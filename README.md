# Muonry – Parallel‑Capable AI Coding Assistant

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/justrach/muonry)

Muonry is a **reliable AI coding assistant** built on Bhumi with optional planning and now **parallel tool calling**. It favors a clean, straightforward approach that actually works. It is also an **open‑sourced Claude Code–style** coding assistant.

## ✨ Key Features

- **⚡ Parallel Tool Calling** – Run multiple tools concurrently in one turn (enabled by default)
- **🎯 Sequential Execution** – Reliable step-by-step execution when needed
- **🧠 Optional Planning** – Cerebras-powered task breakdown for complex projects
- **🔧 Rich Tool Set** – File operations, shell commands, code patching
- **📋 Smart Planning** – AI-powered task decomposition with sequential execution
- **🧵 Bounded Concurrency** – Semaphore-based limits with per-call progress updates
- **📊 Compact Codebase** – 1,238 lines of focused, maintainable code
- **🛡️ Rate‑Limit Fallback** – Automatically retries with a fallback model on rate limits
- **🪓 Context Trimming** – Sliding‑window message trimming to avoid context overflow (~131k)
- **✅ Satya Validation** – Robust schema validation for planner outputs (dict/model safe)
- **🔎 Websearch Improvements** – Structured results and fallback parsing for Title/URL blocks

## 🚀 Quick Start

1. **Set API Keys:**
   ```bash
   export GROQ_API_KEY=your_groq_key
   export CEREBRAS_API_KEY=your_cerebras_key  # Optional for multi-model
   export EXA_API_KEY=your_exa_key            # Optional for websearch tool
   export MUONRY_MAX_CONTEXT_CHARS=120000     # Optional: context cap (chars)
   ```

2. **Run the Assistant:**
   ```bash
   python assistant.py
   ```

## 💬 Usage

### Interactive Chat
Simply run `python assistant.py` and start chatting! The assistant automatically handles:

**Simple Tasks** → Direct execution:
```
💬 You: Read config.json
🤖 Assistant: [reads file directly]
```

**Complex Tasks** → Planning + execution (parallel + sequential as appropriate):
```
💬 You: Create 6 Fire Nation stories in a folder
🧠 Planning task with 6 steps...
📋 Plan created: 1. Create folder, 2-6. Generate stories
💻 [Executes each step with the right mix of parallel + sequential]
```

### Available Tools
- **File Operations**: `read_file`, `write_file`, `apply_patch`
- **System Commands**: `run_shell`, `get_system_info`, `grep`, `search_replace`
- **Planning**: `planner` (automatic for complex tasks)
- **Development**: `update_plan`
- **Web Search**: `websearch` (requires `EXA_API_KEY` or api_key param)
- **Interactive Shell**: `interactive_shell` (PTY; scripted answers, env)
- **Quick Checks**: `quick_check` (syntax/health checks)

### Parallel tool calling

- Muonry can execute a batch of tools in parallel either when models return `tool_calls` or explicitly via the `parallel` tool.
- Env flags:
  - `MUONRY_PARALLEL_TOOLS` (default: 1)
  - `MUONRY_PARALLEL_CONCURRENCY` (default: 5)
  - `MUONRY_PARALLEL_TIMEOUT_MS` (default: 60000)

Example using the `parallel` tool:

```json
{
  "name": "parallel",
  "arguments": {
    "calls": [
      {"name": "read_file", "arguments": {"file_path": "README.md"}},
      {"name": "read_file", "arguments": {"file_path": "pyproject.toml"}},
      {"name": "get_system_info", "arguments": {}}
    ],
    "concurrency": 3,
    "timeout_ms": 60000
  }
}
```

## 🎯 Execution Model: Parallel + Sequential

1. **Simple Detection**: AI recognizes simple vs complex tasks automatically
2. **Optional Planning**: For complex tasks, uses Cerebras to break them into steps
3. **Parallel where independent**: Independent tool calls are batched and run in parallel
4. **Sequential where dependent**: Steps that depend on prior results are executed in order
5. **Reliable Results**: Bounded concurrency, progress events, and fallbacks

**Example Output:**
```
💬 You: Create 6 Fire Nation stories in a folder
🧠 Planning task with 6 steps...
📋 Plan created successfully
💻 Shell: mkdir -p "fire nation" (exit 0)
📝 Writing story 1: The First Flame...
📝 Writing story 2: The Phoenix Crown...
✅ All 6 stories created successfully!
```

## 📊 Architecture

### Core Components
- **`assistant.py`** – Main assistant. Handles chat loop, model fallback, context trimming, and parallel integration (auto + `parallel` tool).
- **`tools/toolset.py`** – Consolidated tool implementations (planner, shell, patching, file ops, quick checks, interactive shell, etc.).
- **`tools/orchestratorv2.py`** – Provider‑agnostic parallel executor (`ParallelToolExecutor`) with progress callbacks.
- **`tools/websearch.py`** – Exa-powered web search with structured JSON output and fallback Title/URL parsing.
- **`tools/apply_patch.py`**, **`tools/shell.py`**, **`tools/update_plan.py`**, etc. – Supporting modules used by `toolset.py`.

### Models & Fallback
- **Primary execution model**: `groq/moonshotai/kimi-k2-instruct` (requires `GROQ_API_KEY`).
- **Fallback model on rate-limit**: `cerebras/qwen-3-coder-480b` (auto retry once).
- **Planner model**: `cerebras/qwen-3-235b-a22b-thinking-2507` (requires `CEREBRAS_API_KEY`).

### Error Handling & Limits
- **Rate-limit handling**: Auto-detects rate limit errors; switches to fallback model and retries once.
- **Context length**: Sliding-window trimming keeps the latest messages within `MUONRY_MAX_CONTEXT_CHARS` (default 120k, below ~131k cap).
- **Planner validation**: Satya schema validation with safe conversion of model/dict step objects.

### Web Search
- `websearch` returns compact JSON: title, url, published_date, author, snippet, and limited text.
- If the provider returns a text block, the tool extracts Title/URL pairs to preserve clickable sources.

---

Muonry is a compact, reliable assistant with first-class parallel tool calling and pragmatic guardrails.
