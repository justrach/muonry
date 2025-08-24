# ADR 0001: Parallel Tool Calling and Tool Call Definition

- Status: Accepted
- Date: 2025-08-25
- Owners: Muonry maintainers
- Related files:
  - `assistant.py` (parallel integration, `parallel` tool, env defaults)
  - `tools/orchestratorv2.py` (`ParallelToolExecutor`, `ToolCallSpec`, `ToolCallState` enum, `ToolRunState` dataclass)

## Context

We wanted models to execute multiple independent tools in one assistant turn to improve latency and UX. Some model providers emit a batch of `tool_calls` (OpenAI-style), but others do not. We also need bounded concurrency, progress callbacks, and robust aggregation.

## Decision

- Implement a provider-agnostic parallel executor in `tools/orchestratorv2.py`.
- Integrate into `assistant.py` with two paths:
  1) If the model returns OpenAI-style `tool_calls`, execute them in parallel automatically.
  2) Expose a `parallel` tool so models can explicitly request a batch when their provider doesn’t natively emit multi-call responses.
- Enable parallel mode by default via `MUONRY_PARALLEL_TOOLS=1` (default).

## What is a Tool Call?

A tool call is a single invocation of a registered function with JSON arguments and a stable call ID. Minimal normalized form:

```json
{
  "id": "call_1",
  "type": "function",
  "function": {
    "name": "read_file",
    "arguments": { "file_path": "README.md" }
  }
}
```

Internal representation (`ToolCallSpec`):

```python
ToolCallSpec(
  tool_call_id="call_1",
  name="read_file",
  arguments={"file_path": "README.md"},
  timeout_ms=None,
)
```

## Execution Flow

- Input: list of `ToolCallSpec`
- For each call:
  - Optional permission gate
  - Resolve tool from registry (Bhumi tools via `ToolRegistry` in `assistant.py`)
  - Run with semaphore-bounded concurrency
  - Stream state changes: pending → running → done/error
- Aggregate results with per-call duration and ok/error flags

Progress callback payload example:
```json
{
  "type": "tool_state",
  "tool_call_id": "call_1",
  "name": "read_file",
  "state": "running"
}
```

Aggregated result shape (executor):
```json
{
  "results": [
    {
      "tool_call_id": "call_1",
      "name": "read_file",
      "ok": true,
      "state": "done",
      "result": "...",
      "error": null,
      "started_at": 1756051828.10,
      "ended_at": 1756051828.40,
      "duration_ms": 300
    }
  ],
  "summary": {"total": 3, "ok": 3, "errors": 0}
}
```

## Assistant Integration (`assistant.py`)

- Env flags:
  - `MUONRY_PARALLEL_TOOLS` (default enabled)
  - `MUONRY_PARALLEL_CONCURRENCY` (default 5)
  - `MUONRY_PARALLEL_TIMEOUT_MS` (default 60000)
- Two entry points:
  - Auto-parallel: when `response["tool_calls"]` exists
  - Explicit: `parallel` tool with schema:

```json
{
  "name": "parallel",
  "arguments": {
    "calls": [ {"name": "read_file", "arguments": {"file_path": "README.md"}} ],
    "concurrency": 5,
    "timeout_ms": 60000
  }
}
```

## Alternatives Considered

- Single-threaded sequential execution: simpler but slower.
- External queueing system: overkill for local developer assistant use.

## Consequences

- Faster responses for I/O-bound operations (file reads, grep, web requests).
- Clearer telemetry via progress events.
- Slight complexity in handling providers without native multi-call responses (solved by `parallel` tool).

## Usage Examples

- Parallel read + system info:
```json
{
  "name": "parallel",
  "arguments": {
    "calls": [
      {"name": "read_file", "arguments": {"file_path": "README.md"}},
      {"name": "read_file", "arguments": {"file_path": "pyproject.toml"}},
      {"name": "get_system_info", "arguments": {}}
    ]
  }
}
```

- From model with native `tool_calls`: just emit an array; Muonry will run them concurrently.

## Notes

- Fix in `tools/orchestratorv2.py`: renamed dataclass `ToolCallState` → `ToolRunState` to avoid clashing with Enum `ToolCallState`.
- Web search requires `EXA_API_KEY` unless provided as argument to `websearch`.
