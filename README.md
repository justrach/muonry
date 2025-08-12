# Muonry – Simple Sequential AI Coding Assistant

Muonry is a **reliable, sequential AI coding assistant** built on Bhumi with optional planning capabilities. The complex multi-agent orchestrator has been **removed** in favor of a clean, straightforward approach that actually works.

## ✨ Key Features

- **🎯 Sequential Execution** – Reliable step-by-step task completion
- **🧠 Optional Planning** – Cerebras-powered task breakdown for complex projects
- **🔧 Rich Tool Set** – File operations, shell commands, code patching
- **📋 Smart Planning** – AI-powered task decomposition with sequential execution
- **⚡ No Concurrency Issues** – Simple, reliable execution without coordination failures
- **📊 Compact Codebase** – 1,238 lines of focused, maintainable code
- **🛡️ Rate‑Limit Fallback** – Automatically retries with a fallback model on rate limits
- **🪓 Context Trimming** – Sliding‑window message trimming to avoid context overflow (~131k)
- **✅ Satya Validation** – Robust schema validation for planner outputs (dict/model safe)
- **🔎 Websearch Improvements** – Structured results and fallback parsing for Title/URL blocks

## 🚀 Quick Start

1. **Install (editable):**
   ```bash
   # create venv (example)
   python -m venv .venv/muonry && source .venv/muonry/bin/activate

   # install core (bhumi + satya included)
   pip install -e .
   # or with uv
   # uv pip install -e .

   # optional extras
   # pip install -e ".[websearch]"   # Exa web search
   # pip install -e ".[mcp]"         # MCP client
   ```

2. **Set API Keys:**
   ```bash
   export GROQ_API_KEY=your_groq_key
   export CEREBRAS_API_KEY=your_cerebras_key  # Optional for planner/fallback
   export EXA_API_KEY=your_exa_key            # Optional for websearch tool
   export MUONRY_MAX_CONTEXT_CHARS=120000     # Optional: context cap (chars)
   ```

3. **Run the Assistant:**
   ```bash
   muonry           # recommended CLI
   # or
   python assistant.py
   ```

## 💬 Usage

### Interactive Chat
Run `muonry` (recommended) or `python assistant.py` and start chatting! The assistant automatically handles:

**Simple Tasks** → Direct execution:
```
💬 You: Read config.json
🤖 Assistant: [reads file directly]
```

**Complex Tasks** → Planning + Sequential execution:
```
💬 You: Create 6 Fire Nation stories in a folder
🧠 Planning task with 6 steps...
📋 Plan created: 1. Create folder, 2-6. Generate stories
💻 [Executes each step sequentially]
```

### Available Tools
- **File Operations**: `read_file`, `write_file`, `apply_patch`
- **System Commands**: `run_shell`, `get_system_info`, `grep`, `search_replace`
- **Planning**: `planner` (automatic for complex tasks)
- **Development**: `update_plan`
- **Web Search**: `websearch` (requires `EXA_API_KEY` or api_key param)
- **Interactive Shell**: `interactive_shell` (PTY; scripted answers, env)
- **Quick Checks**: `quick_check` (syntax/health checks)

## 🎯 How the Sequential Approach Works

1. **Simple Detection**: AI recognizes simple vs complex tasks automatically
2. **Optional Planning**: For complex tasks, uses Cerebras to break them into steps
3. **Sequential Execution**: Executes each step in order using appropriate tools
4. **Reliable Results**: No coordination issues, race conditions, or worker failures

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

### Core Components (sequential, no orchestrator)
- **`assistant.py`** – Main sequential assistant. Handles chat loop, model fallback, and context trimming.
- **`tools/toolset.py`** – Consolidated tool implementations (planner, shell, patching, file ops, quick checks, interactive shell, etc.).
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

### Smithery MCP (HTTP)
- **Install MCP extra**:
  ```bash
  pip install -e ".[mcp]"   # or: pip install "mcp[cli]"
  ```
- **Set a server URL** (examples on Smithery):
  ```bash
  export SMITHERY_SERVER_URL="https://server.smithery.ai/exa/mcp"
  # optional
  export SMITHERY_CLIENT_NAME="Muonry CLI"
  export SMITHERY_REDIRECT_URI="http://localhost:3000/callback"
  export SMITHERY_SCOPE="user"
  ```
- **First run triggers OAuth**: you'll see an auth URL and be asked to paste the callback URL after authorizing in the browser.
- **Token storage**: saved under `~/.muonry/smithery_tokens.json` and `~/.muonry/smithery_client.json` for reuse.
- **Quick check** (interactive terminal required):
  ```bash
  python3 scripts/run_smoke_tests.py   # runs smithery_list_tools when SMITHERY_SERVER_URL is set
  ```
  Programmatic access is available via `tools/toolset.py`:
  - `smithery_list_tools_tool(server_url)`
  - `smithery_call_tool_tool(server_url, tool, arguments=None)`

---

Muonry is a compact, reliable, sequential assistant. No multi-agent orchestration, no worker state—just focused tools and robust guardrails.
