import asyncio
import json
import os
import sys
import time
import types
from typing import Any, Dict

import pytest

# Use pytest-asyncio via per-test decorator on async tests (no module-level mark)


class DummyRegistry:
    def __init__(self) -> None:
        self._map: Dict[str, Any] = {}

    def register(self, name: str, func: Any) -> None:
        self._map[name] = func

    def get_tool(self, name: str):
        return self._map.get(name)


class DummyClient:
    def __init__(self) -> None:
        self.tool_registry = DummyRegistry()


@pytest.mark.asyncio
async def test_strict_client_rejects_unregistered_tool():
    from muonry.clients import StrictLLMClient  # type: ignore
    from bhumi.base_client import LLMConfig  # type: ignore

    client = StrictLLMClient(LLMConfig(api_key="dummy", model="dummy", debug=False), strict_tools=True)

    messages = []
    tool_calls = [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "nonexistent", "arguments": json.dumps({"x": 1})},
        }
    ]

    out = await client._handle_tool_calls(messages, tool_calls, debug=False)
    # Expect: assistant echo + tool error message
    assert any(m.get("role") == "assistant" and m.get("tool_calls") for m in out)
    tool_msgs = [m for m in out if m.get("role") == "tool"]
    assert len(tool_msgs) == 1
    err = json.loads(tool_msgs[0]["content"]) if isinstance(tool_msgs[0]["content"], str) else tool_msgs[0]["content"]
    assert err.get("error") == "unregistered_tool"
    assert err.get("name") == "nonexistent"


@pytest.mark.asyncio
async def test_strict_client_executes_registered_tool():
    from muonry.clients import StrictLLMClient  # type: ignore
    from bhumi.base_client import LLMConfig  # type: ignore

    client = StrictLLMClient(LLMConfig(api_key="dummy", model="dummy", debug=False), strict_tools=True)

    async def echo_tool(text: str) -> str:
        return f"echo:{text}"

    client.register_tool(name="echo", func=echo_tool, description="echo", parameters={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]})

    messages = []
    tool_calls = [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "echo", "arguments": json.dumps({"text": "hi"})},
        }
    ]

    out = await client._handle_tool_calls(messages, tool_calls, debug=False)
    tool_msgs = [m for m in out if m.get("role") == "tool"]
    assert len(tool_msgs) == 1
    assert tool_msgs[0]["content"] == "echo:hi"


@pytest.mark.asyncio
async def test_parallel_strict_rejects_unregistered_tools():
    from muonry.assistant import MuonryAssistant  # type: ignore
    from tools.orchestratorv2 import ToolCallState  # type: ignore

    a = MuonryAssistant()
    a._strict_tools_mode = True  # enforce strict
    a.client = DummyClient()  # minimal client with tool_registry

    # Register one valid tool
    async def add(a_: int, b: int) -> int:
        await asyncio.sleep(0)
        return a_ + b

    a.client.tool_registry.register("add", add)

    calls = [
        {"id": "1", "type": "function", "function": {"name": "add", "arguments": {"a_": 1, "b": 2}}},
        {"id": "2", "type": "function", "function": {"name": "nope", "arguments": {}}},
    ]

    agg = await a._run_parallel_tool_calls(calls)
    assert agg is not None
    results = agg["results"]
    # Find by id
    r1 = next(r for r in results if r["tool_call_id"] == "1")
    r2 = next(r for r in results if r["tool_call_id"] == "2")

    assert r1["ok"] is True
    assert r2["ok"] is False
    assert r2.get("error") == "rejected"
    # State is enum ToolCallState in results
    assert r2["state"] == ToolCallState.REJECTED


@pytest.mark.asyncio
async def test_parallel_without_strict_allows_unregistered_but_errors_tool_not_found():
    from muonry.assistant import MuonryAssistant  # type: ignore
    from tools.orchestratorv2 import ToolCallState  # type: ignore

    a = MuonryAssistant()
    a._strict_tools_mode = False
    a.client = DummyClient()

    async def mul(x: int, y: int) -> int:
        await asyncio.sleep(0)
        return x * y

    a.client.tool_registry.register("mul", mul)

    calls = [
        {"id": "1", "type": "function", "function": {"name": "mul", "arguments": {"x": 2, "y": 3}}},
        {"id": "2", "type": "function", "function": {"name": "nonexistent", "arguments": {}}},
    ]

    agg = await a._run_parallel_tool_calls(calls)
    results = agg["results"]
    r_ok = next(r for r in results if r["tool_call_id"] == "1")
    r_bad = next(r for r in results if r["tool_call_id"] == "2")

    assert r_ok["ok"] is True
    assert r_bad["ok"] is False
    assert r_bad.get("error") == "tool_not_found"
    assert r_bad["state"] == ToolCallState.ERROR


@pytest.mark.asyncio
async def test_parallel_concurrency_behavior_is_bounded():
    from muonry.assistant import MuonryAssistant  # type: ignore

    a = MuonryAssistant()
    a._strict_tools_mode = False
    a._parallel_concurrency = 2  # bound concurrency
    a.client = DummyClient()

    async def sleeper(ms: int) -> str:
        await asyncio.sleep(ms / 1000)
        return f"slept {ms}"

    a.client.tool_registry.register("sleep", sleeper)

    calls = [
        {"id": str(i), "type": "function", "function": {"name": "sleep", "arguments": {"ms": 300}}}
        for i in range(4)
    ]

    t0 = time.perf_counter()
    agg = await a._run_parallel_tool_calls(calls)
    dt = time.perf_counter() - t0

    # With concurrency 2, 4x300ms should complete in roughly ~0.6-0.8s (two waves).
    assert dt < 1.5, f"Expected concurrent execution; took {dt:.2f}s"
    assert dt > 0.45, f"Execution unexpectedly too fast; took {dt:.2f}s"
    assert agg["summary"]["total"] == 4


def test_cli_prints_strict_notice(monkeypatch, capsys):
    # Ensure env set
    monkeypatch.setenv("MUONRY_STRICT_TOOLS", "1")

    # Inject a dummy assistant module with a no-op main to avoid running the real assistant
    dummy = types.ModuleType("assistant")

    async def _noop():
        return None

    dummy.main = _noop  # type: ignore[attr-defined]
    sys.modules["assistant"] = dummy

    from muonry import cli as mu_cli  # import after monkeypatch

    # Call main and capture output
    mu_cli.main()
    out = capsys.readouterr().out
    assert "Strict tools mode requested via MUONRY_STRICT_TOOLS" in out
