"""
OrchestratorV2: Parallel tool calling engine (from scratch)

Goal: Execute multiple model-emitted tool calls concurrently in one turn, 
mirroring the approach described by Continue (PR #6524) at a systems level.

Design highlights:
- Accept a batch of tool calls (each with a stable tool_call_id)
- Request per-call permission via a callback before executing
- Execute approved calls in parallel with a concurrency limit
- Stream independent updates per call (state changes) via an optional callback
- Preserve call IDs and return provider-agnostic aggregated results

This module focuses on execution; UI, chat history (toolCallStates[]), and 
provider-specific adapters should live at higher layers.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

# Types
JSON = Union[dict, list, str, int, float, bool, None]


class ToolCallState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class ToolCallSpec:
    """Provider-agnostic tool call specification."""
    tool_call_id: str
    name: str
    arguments: Dict[str, Any]
    timeout_ms: Optional[int] = None


@dataclass
class ToolCallResult:
    tool_call_id: str
    name: str
    ok: bool
    state: ToolCallState
    result: Optional[JSON] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    ended_at: Optional[float] = None

    @property
    def duration_ms(self) -> Optional[int]:
        if self.started_at and self.ended_at:
            return int((self.ended_at - self.started_at) * 1000)
        return None


PermissionCallback = Callable[[ToolCallSpec], Awaitable[bool]]
ProgressCallback = Callable[[Dict[str, Any]], Awaitable[None]]
ToolResolver = Callable[[str], Optional[Callable[..., Awaitable[Any] | Any]]]


class ParallelToolExecutor:
    """Execute independent tool calls concurrently with per-call permissions.

    Responsibilities:
    - Request approval per tool call via `permission_cb`
    - Run approved calls up to `concurrency` in parallel
    - Stream per-call state transitions via `progress_cb`
    - Preserve `tool_call_id` and return aggregated results

    This module focuses purely on execution. Parsing provider-specific message
    formats into `ToolCallSpec[]` and rendering UI belongs to higher layers.
    """

    def __init__(
        self,
        tool_resolver: ToolResolver,
        *,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._resolve_tool = tool_resolver
        self._log = logger or logging.getLogger("orchestratorv2")
        if not self._log.handlers:
            h = logging.StreamHandler()
            f = logging.Formatter("[%(asctime)s] [%(levelname)s] orchestratorv2: %(message)s", "%H:%M:%S")
            h.setFormatter(f)
            self._log.addHandler(h)
        self._log.setLevel(logging.INFO)

    async def _emit(self, cb: Optional[ProgressCallback], payload: Dict[str, Any]) -> None:
        if cb:
            try:
                await cb(payload)
            except Exception as e:
                # Never allow UI callback issues to break execution
                self._log.debug(f"progress_cb error ignored: {e}")

    async def _maybe_await(self, fn: Callable[..., Any], *args, **kwargs) -> Any:
        out = fn(*args, **kwargs)
        if asyncio.iscoroutine(out):
            return await out
        return out

    async def execute(
        self,
        calls: List[ToolCallSpec],
        *,
        permission_cb: Optional[PermissionCallback] = None,
        progress_cb: Optional[ProgressCallback] = None,
        concurrency: int = 5,
        default_timeout_ms: int = 60000,
    ) -> Dict[str, Any]:
        semaphore = asyncio.Semaphore(max(1, concurrency))

        async def _run_one(spec: ToolCallSpec) -> ToolCallResult:
            # Permission gate
            approved = True
            if permission_cb:
                try:
                    approved = await permission_cb(spec)
                except Exception as e:
                    approved = False
                    self._log.debug(f"permission_cb error for {spec.tool_call_id}: {e}")

            if not approved:
                await self._emit(progress_cb, {
                    "type": "tool_state",
                    "tool_call_id": spec.tool_call_id,
                    "name": spec.name,
                    "state": ToolCallState.REJECTED.value,
                })
                return ToolCallResult(
                    tool_call_id=spec.tool_call_id,
                    name=spec.name,
                    ok=False,
                    state=ToolCallState.REJECTED,
                    error="rejected",
                )

            tool = self._resolve_tool(spec.name)
            if tool is None:
                await self._emit(progress_cb, {
                    "type": "tool_state",
                    "tool_call_id": spec.tool_call_id,
                    "name": spec.name,
                    "state": ToolCallState.ERROR.value,
                    "error": "tool_not_found",
                })
                return ToolCallResult(
                    tool_call_id=spec.tool_call_id,
                    name=spec.name,
                    ok=False,
                    state=ToolCallState.ERROR,
                    error="tool_not_found",
                )

            timeout = (spec.timeout_ms or default_timeout_ms) / 1000.0

            await semaphore.acquire()
            try:
                await self._emit(progress_cb, {
                    "type": "tool_state",
                    "tool_call_id": spec.tool_call_id,
                    "name": spec.name,
                    "state": ToolCallState.RUNNING.value,
                })
                started = time.time()

                async def _with_timeout():
                    return await self._maybe_await(tool, **spec.arguments)

                result: Any
                try:
                    result = await asyncio.wait_for(_with_timeout(), timeout=timeout)
                    ended = time.time()
                    await self._emit(progress_cb, {
                        "type": "tool_state",
                        "tool_call_id": spec.tool_call_id,
                        "name": spec.name,
                        "state": ToolCallState.DONE.value,
                        "ended_at": ended,
                    })
                    return ToolCallResult(
                        tool_call_id=spec.tool_call_id,
                        name=spec.name,
                        ok=True,
                        state=ToolCallState.DONE,
                        result=result,
                        started_at=started,
                        ended_at=ended,
                    )
                except asyncio.TimeoutError:
                    ended = time.time()
                    await self._emit(progress_cb, {
                        "type": "tool_state",
                        "tool_call_id": spec.tool_call_id,
                        "name": spec.name,
                        "state": ToolCallState.ERROR.value,
                        "error": "timeout",
                        "ended_at": ended,
                    })
                    return ToolCallResult(
                        tool_call_id=spec.tool_call_id,
                        name=spec.name,
                        ok=False,
                        state=ToolCallState.ERROR,
                        error="timeout",
                        started_at=started,
                        ended_at=ended,
                    )
                except Exception as e:
                    ended = time.time()
                    await self._emit(progress_cb, {
                        "type": "tool_state",
                        "tool_call_id": spec.tool_call_id,
                        "name": spec.name,
                        "state": ToolCallState.ERROR.value,
                        "error": str(e),
                        "ended_at": ended,
                    })
                    return ToolCallResult(
                        tool_call_id=spec.tool_call_id,
                        name=spec.name,
                        ok=False,
                        state=ToolCallState.ERROR,
                        error=str(e),
                        started_at=started,
                        ended_at=ended,
                    )
            finally:
                semaphore.release()

        # Emit initial states
        for c in calls:
            await self._emit(progress_cb, {
                "type": "tool_state",
                "tool_call_id": c.tool_call_id,
                "name": c.name,
                "state": ToolCallState.PENDING.value,
            })

        # Launch all tasks
        tasks = [asyncio.create_task(_run_one(c)) for c in calls]
        results: List[ToolCallResult] = await asyncio.gather(*tasks)

        # Aggregate
        agg = {
            "results": [
                {
                    **asdict(r),
                    "duration_ms": r.duration_ms,
                    # Ensure JSON-safe result
                    "result": _json_safe(r.result),
                }
                for r in results
            ],
            "summary": {
                "total": len(results),
                "ok": sum(1 for r in results if r.ok),
                "errors": sum(1 for r in results if not r.ok),
            },
        }
        await self._emit(progress_cb, {"type": "batch_done", **agg["summary"]})
        return agg


def _json_safe(val: Any) -> JSON:
    try:
        json.dumps(val)
        return val  # type: ignore[return-value]
    except Exception:
        try:
            return json.loads(json.dumps(val, default=str))  # Fallback serialize
        except Exception:
            return str(val)


# Example usage for manual testing
if __name__ == "__main__":
    async def main():
        async def tool_sleep(ms: int) -> str:
            await asyncio.sleep(ms / 1000)
            return f"slept {ms}ms"

        def tool_echo(text: str) -> Dict[str, Any]:
            return {"echo": text}

        registry: Dict[str, Callable[..., Any]] = {
            "sleep": tool_sleep,
            "echo": tool_echo,
        }

        def resolver(name: str):
            return registry.get(name)

        async def permit(spec: ToolCallSpec) -> bool:
            # Approve everything for demo
            return True

        async def progress(update: Dict[str, Any]):
            print("PROGRESS:", update)

        exec = ParallelToolExecutor(resolver)
        calls = [
            ToolCallSpec(tool_call_id="a1", name="sleep", arguments={"ms": 200}),
            ToolCallSpec(tool_call_id="b2", name="echo", arguments={"text": "hi"}),
            ToolCallSpec(tool_call_id="c3", name="sleep", arguments={"ms": 100}),
        ]
        agg = await exec.execute(
            calls,
            permission_cb=permit,
            progress_cb=progress,
            concurrency=2,
            default_timeout_ms=5000,
        )
        print("AGGREGATED:", json.dumps(agg, indent=2))

    asyncio.run(main())
from dataclasses import dataclass, asdict, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

# Import async tools from our local registry
from tools import toolset as ts

logger = logging.getLogger("orchestratorv2")
if not logger.handlers:
    _h = logging.StreamHandler()
    _f = logging.Formatter("[%(asctime)s] [%(levelname)s] orchestratorv2: %(message)s", "%H:%M:%S")
    _h.setFormatter(_f)
    logger.addHandler(_h)
logger.setLevel(logging.INFO)


# ----- Data structures -----

@dataclass
class ToolCallRequest:
    """Model-emitted request.

    Fields mirror typical provider responses while staying provider-agnostic.
    - tool_call_id: stable identifier from the model's response (preserved end-to-end)
    - name: registered tool name
    - arguments: parsed JSON args for the tool
    - approved: optional initial approval (UI may set this pre-exec). If None, we'll ask.
    - timeout_ms: optional per-call timeout
    """
    tool_call_id: str
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    approved: Optional[bool] = None
    timeout_ms: Optional[int] = None


@dataclass
class ToolRunState:
    tool_call_id: str
    name: str
    arguments: Dict[str, Any]
    status: str = "pending"  # pending|awaiting_approval|rejected|running|done|failed|timeout
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "tool_call_id": self.tool_call_id,
            "tool_name": self.name,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# Callback signatures
PermissionCallback = Callable[[ToolRunState], Awaitable[bool]]
UpdateCallback = Callable[[ToolRunState, str], Awaitable[None]]  # event: state_change|start|finish|error


class OrchestratorV2:
    def __init__(
        self,
        max_concurrency: int = 8,
        registry: Optional[Dict[str, Callable[..., Awaitable[str]]]] = None,
    ) -> None:
        self.max_concurrency = max(1, int(max_concurrency))
        self.registry = registry or self._default_registry()

    def _default_registry(self) -> Dict[str, Callable[..., Awaitable[str]]]:
        # Map display names to async tool funcs in tools/toolset.py
        return {
            "read_file": ts.read_file_tool,
            "write_file": ts.write_file_tool,
            "grep": ts.grep_tool,
            "run_shell": ts.run_shell_tool,
            "smart_run_shell": ts.smart_run_shell_tool,
            "interactive_shell": ts.interactive_shell_tool,
            "get_system_info": ts.get_system_info_tool,
            "quick_check": ts.quick_check_tool,
            "update_plan": ts.update_plan_tool,
            "planner": ts.planner_tool,
            "deepwiki": ts.deepwiki_tool,
            "search_replace": ts.search_replace_tool,
        }

    async def _maybe_call(self, cb: Optional[UpdateCallback], state: ToolRunState, event: str) -> None:
        if cb is None:
            return
        try:
            await cb(state, event)
        except Exception:
            # Do not crash orchestrator on callback errors
            logger.debug("update callback raised; ignoring", exc_info=True)

    async def _await_permission(self, req: ToolCallRequest, state: ToolRunState, permission_cb: Optional[PermissionCallback]) -> bool:
        if req.approved is True:
            return True
        if req.approved is False:
            return False
        if permission_cb is None:
            return True  # default auto-approve
        state.status = "awaiting_approval"
        await self._maybe_call(None, state, "state_change")
        try:
            return await permission_cb(state)
        except Exception:
            logger.debug("permission callback raised; defaulting to reject", exc_info=True)
            return False

    async def _run_single(self, req: ToolCallRequest, update_cb: Optional[UpdateCallback]) -> ToolRunState:
        state = ToolRunState(tool_call_id=req.tool_call_id, name=req.name, arguments=dict(req.arguments or {}))
        approved = await self._await_permission(req, state, None)
        if not approved:
            state.status = "rejected"
            await self._maybe_call(update_cb, state, "state_change")
            return state

        func = self.registry.get(req.name)
        if not func:
            state.status = "failed"
            state.error = f"Unknown tool: {req.name}"
            await self._maybe_call(update_cb, state, "state_change")
            return state

        # Execute
        state.status = "running"
        state.started_at = time.time()
        await self._maybe_call(update_cb, state, "start")

        try:
            if req.timeout_ms and req.timeout_ms > 0:
                res = await asyncio.wait_for(func(**(req.arguments or {})), timeout=req.timeout_ms / 1000)
            else:
                res = await func(**(req.arguments or {}))
            state.result = res
            state.status = "done"
        except asyncio.TimeoutError:
            state.status = "timeout"
            state.error = f"Timeout after {req.timeout_ms} ms" if req.timeout_ms else "Timeout"
        except Exception as e:
            state.status = "failed"
            state.error = str(e)
        finally:
            state.completed_at = time.time()
            await self._maybe_call(update_cb, state, "finish")
        return state

    async def run_batch(
        self,
        requests: List[ToolCallRequest] | List[Dict[str, Any]],
        permission_cb: Optional[PermissionCallback] = None,
        update_cb: Optional[UpdateCallback] = None,
        max_concurrency: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run all tool calls in parallel and aggregate results.

        - requests: list of ToolCallRequest or plain dicts with keys
          {tool_call_id, name, arguments?, approved?, timeout_ms?}
        - permission_cb: optional async function called per call for approval
        - update_cb: optional async function called on state changes
        - max_concurrency: override default per-batch
        """
        # Normalize inputs
        norm: List[ToolCallRequest] = []
        for i, r in enumerate(requests):
            if isinstance(r, ToolCallRequest):
                norm.append(r)
            else:
                rid = r.get("tool_call_id") or r.get("id") or f"call_{i+1}"
                norm.append(
                    ToolCallRequest(
                        tool_call_id=str(rid),
                        name=str(r.get("name") or r.get("tool") or ""),
                        arguments=dict(r.get("arguments") or {}),
                        approved=r.get("approved"),
                        timeout_ms=r.get("timeout_ms"),
                    )
                )

        # Use a semaphore to bound parallelism
        sem = asyncio.Semaphore(max_concurrency or self.max_concurrency)
        states: List[ToolRunState] = []
        start = time.time()

        async def _guarded(req: ToolCallRequest) -> ToolRunState:
            async with sem:
                # permission via provided permission_cb if any
                # Use a wrapper state to interact with permission_cb
                state = ToolRunState(tool_call_id=req.tool_call_id, name=req.name, arguments=dict(req.arguments or {}))
                # Ask for permission
                approved = await self._await_permission(req, state, permission_cb)
                if not approved:
                    state.status = "rejected"
                    await self._maybe_call(update_cb, state, "state_change")
                    return state
                # Now actually run the call with updates
                return await self._run_single(ToolCallRequest(
                    tool_call_id=req.tool_call_id,
                    name=req.name,
                    arguments=req.arguments,
                    approved=True,
                    timeout_ms=req.timeout_ms,
                ), update_cb)

        tasks = [asyncio.create_task(_guarded(r)) for r in norm]
        for t in asyncio.as_completed(tasks):
            st = await t
            states.append(st)

        duration_ms = int((time.time() - start) * 1000)
        # Aggregate provider-agnostic results (suitable for a single-turn tool_result response)
        results = [s.to_public_dict() for s in states]
        overall = {
            "status": "ok" if all(s.status in ("done", "rejected") for s in states) else "partial" if any(s.status == "done" for s in states) else "error",
            "duration_ms": duration_ms,
            "tool_results": results,
        }
        return overall


# ----- Optional CLI for quick manual testing -----
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Run a batch of tool calls in parallel")
    parser.add_argument("--batch", help="Path to JSON file with 'tool_calls' array")
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args()

    async def _amain() -> None:
        if not args.batch:
            print("Missing --batch", file=sys.stderr)
            sys.exit(2)
        try:
            data = json.loads(open(args.batch, "r", encoding="utf-8").read())
        except Exception as e:
            print(f"Failed reading batch: {e}", file=sys.stderr)
            sys.exit(2)
        calls = data.get("tool_calls") or []
        orch = OrchestratorV2(max_concurrency=args.concurrency)
        res = await orch.run_batch(calls)
        print(json.dumps(res, indent=2))

    asyncio.run(_amain())
