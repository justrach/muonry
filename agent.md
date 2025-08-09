# Muonry AI Coding Assistant - Overview & Capabilities

This project is a **simplified, sequential AI coding assistant** with optional planning capabilities. The complex multi-agent orchestrator has been removed in favor of a reliable, straightforward approach that actually works.

## Root Directory (`/muonry`)

- **`agent.md`** - This file: comprehensive documentation about capabilities and usage
- **`assistant.py`** - **Main sequential assistant** (with optional planning and /settings)
- **`README.md`** - Project overview and basic setup instructions
- **`tools/toolset.py`** - Consolidated tool implementations (planner, shell, patching, file ops, quick checks, interactive shell, websearch)
- **`~/.muonry/.env`** - User-level secrets (GROQ, CEREBRAS, EXA) managed by CLI; created on first run with `0600` perms

## Key Directories

### `tools/` Directory
Contains utility modules and helper functions:
- `toolset.py`: Consolidated tool implementations registered by `assistant.py`
- `build_analyzer.py`: Build failure analysis and auto-fix suggestions
- `shell.py`: Shell command execution and management
- `apply_patch.py`: Advanced file patching tool
- `update_plan.py`: Plan management utilities
- `websearch.py`: Exa-powered web search tool (optional extra; requires `EXA_API_KEY`)
- `orchestrator.py`: ⚠️ Deprecated (excluded from active codebase)

## 📊 **Project Statistics** (excluding deprecated orchestrator)
- **Total Python Code:** 1,238 lines
- **Core Assistant:** 648 lines
- **Active Tools:** 441 lines
- **Dependencies:** 149 lines

## 🎯 **Architecture: Simple Sequential Assistant**

### **Core Design Philosophy:**
- **Simple tasks:** Use individual tools directly
- **Complex tasks:** Use planner tool first, then execute sequentially
- **No broken concurrency:** All operations run in reliable sequence
- **Optional planning:** Cerebras-powered task breakdown for multi-file projects

### **Key Features (What It Can Do):**
1. **Planner Tool** - Uses Cerebras Qwen model for complex task breakdown
2. **Robust Parsing** - orjson + Satya schema validation
3. **Sequential Execution** - No coordination issues or race conditions
4. **Clean Tool Set** - File ops, shell commands, patching, planning

## 🎯 **What Muonry Can Do** - Complete Capability Overview

### **📁 File Operations**
- **Create new files** with `write_file` (e.g., "Create a new Python script")
- **Read any file** with `read_file` (e.g., "Read the README.md")
- **Apply patches** with `apply_patch` (safe file modifications)
- **Search/replace** with `search_replace` (simple text replacements)
- **Search patterns** with `grep` (find code across files)

### **🐚 System & Shell Operations**
 - **Execute commands** with `run_shell` (e.g., "Run `ls -la`")
 - **Smart command execution** with `smart_run_shell` (auto-fixes build issues)
 - **System information** with `get_system_info` (OS, Python version, etc.)
 - **Quick project checks** with `quick_check` (validate Python/Rust/JS projects)

### **🌐 Web Search (Optional)**
- **Exa web search** with `websearch` (off by default). Install optional extra: `pip install "muonry[websearch]"`. Requires `EXA_API_KEY` (or pass `api_key`). Returns structured JSON results and includes a fallback parser that extracts Title/URL pairs when providers return text blocks.

### **🧠 AI-Powered Planning**
- **Complex task breakdown** with `planner` (e.g., "Create 6 Fire Nation stories")
- **Sequential execution** of multi-step projects
- **Cerebras AI integration** for intelligent planning
- **Automatic step generation** for multi-file projects

## 🧠 Models & Fallback

- **Primary execution model**: `groq/moonshotai/kimi-k2-instruct` (requires `GROQ_API_KEY`).
- **Fallback model on rate-limit**: `cerebras/qwen-3-coder-480b` (auto-retry once when rate-limit is detected).
- **Planner model**: `cerebras/qwen-3-235b-a22b-thinking-2507` (requires `CEREBRAS_API_KEY`).

### Limits & Guardrails
- **Rate-limit handling**: Automatic model switch and retry on rate-limit errors.
- **Context management**: Sliding-window trimming keeps the latest conversation within a safe character budget (default `MUONRY_MAX_CONTEXT_CHARS=120000`, under ~131k cap). The system message is preserved and the latest turns are kept.
- **Planner validation**: Satya schema validation with robust normalization of steps (handles dicts and model instances; no `__dict__` reliance).

### **📋 Project Management**
- **Development planning** with `update_plan` (track progress)
- **Build analysis** with `smart_run_shell` (auto-detects and fixes build issues)
- **Package management** (auto-detects npm/bun/yarn/pnpm)
- **Error analysis** with detailed suggestions

### **💬 Conversational Features**
- **Interactive chat** mode via console script (`muonry`) or module (`python -m muonry.cli`)
- **Markdown rendering** in terminal
- **Conversational responses** using `talk` tool
- **Storytelling and explanations** without file creation

## 🔧 **Tool Examples**

### **Simple Tasks (Direct Execution)**
```
💬 You: Read config.json
🤖 Assistant: [reads file contents directly]

💬 You: Run `ls -la`
🤖 Assistant: [executes command and shows output]
```

### **Complex Tasks (Planning + Sequential Execution)**
```
💬 You: Create 6 Fire Nation stories in a folder
🧠 Planning task with 6 steps...
📋 Plan created: 1. Create folder, 2-6. Generate stories
💻 [Executes each step sequentially]
✅ All 6 stories created successfully!
```

### **Smart Build Fixes**
```
💬 You: Run `npm run build`
🔍 Analyzing build output...
⚠️ Missing modules detected: express, lodash
🛠️ Auto-fix: Installing missing dependencies...
✅ Build completed successfully!
```

### **Project Validation**
```
💬 You: Check if this Python project has syntax errors
🔍 Scanning Python files...
✅ Python syntax OK: 12/12 files
```

### **Web Search (Exa)**
```
💬 You: Find a blog post about AI
🔎 Using websearch (enabled=true)...
📄 Returning JSON results from Exa
```
Parameters:
- query: search query string
- enabled: must be true to execute the search (default false)
- api_key: override API key (otherwise uses `EXA_API_KEY`)
- text: include text contents (default true)
- type: Exa search type (default "auto")

## 📦 Packaging & Publishing

- Universal wheel (`py3-none-any`) with `requires-python >= 3.10` (3.10–3.13 supported)
- Optional dependencies:
  - `websearch`: installs `exa_py`
  - `llm`: installs `bhumi`
- CLI entry point: `muonry = muonry.cli:main`
- URLs: Homepage `https://github.com/justrach/muonry`, Website `https://muonry.com`
- Build: `python -m build` → dist/*.whl, dist/*.tar.gz
- Upload:
  - TestPyPI: `twine upload --repository-url https://test.pypi.org/legacy/ dist/*`
  - PyPI: `twine upload dist/*`

## 🚨 **What Muonry Cannot Do**
- ❌ Concurrent execution (intentionally sequential for reliability)
- ❌ Full web browsing or scraping (only Exa search via API if enabled)
- ❌ Arbitrary external APIs (limited to configured ones like Groq/Cerebras/Exa)
- ❌ GUI interactions (terminal-based)
- ❌ Database operations (file system only)

## 🎨 **Supported File Types**
- **Python** (.py) - syntax validation, linting
- **Rust** (.rs) - cargo check, rustc validation
- **JavaScript/TypeScript** (.js, .ts, .jsx, .tsx) - tsc, package.json validation
- **Markdown** (.md) - rendering and editing
- **JSON** - parsing and validation
- **Configuration files** - reading and modification
- **Any text file** - reading, writing, searching

## 🚀 **Getting Started**

### **Interactive Mode**
```bash
muonry
# or: python -m muonry.cli
```

### **Environment Setup**
Preferred: use the in-app settings menu.
```
# Inside Muonry prompt
/settings  # View/set/clear GROQ_API_KEY, CEREBRAS_API_KEY, EXA_API_KEY
```
Advanced: edit `~/.muonry/.env` directly (created on first run, `0600` perms).
```env
GROQ_API_KEY=...
CEREBRAS_API_KEY=...   # optional
EXA_API_KEY=...        # optional (for websearch)
MUONRY_MAX_CONTEXT_CHARS=120000  # optional
```

### **Provider Links**
- **Groq**: https://groq.com (sign in → console)
- **Cerebras**: https://www.cerebras.ai
- **Exa (websearch)**: https://exa.ai

### **Optional Extras**
- Base install (lean): `pip install muonry`
- Enable websearch: `pip install "muonry[websearch]"`

### **Quick Commands**
- `python assistant.py` → Start interactive chat
- `md README.md` → Preview markdown file
- `quit` or `exit` → Exit interactive mode

## 🎯 **Best Practices**
1. **Use planning for complex tasks** - Always use the planner for multi-file projects
2. **Check syntax before running** - Use `quick_check` to validate code
3. **Use smart shell for builds** - Let it auto-fix common issues
4. **Keep conversations focused** - Each session should have a clear goal
5. **Save important work** - Use `write_file` for permanent changes

## 🆕 Recent Enhancements
- **/settings menu**: View/set/clear keys in `~/.muonry/.env` with provider links.
- **Optional websearch extra**: `muonry[websearch]` for Exa SDK; graceful runtime handling when missing.
- **Rate-limit fallback**: Automatic retry with a fallback model on rate-limit.
- **Context trimming**: Sliding-window strategy prevents context overflow errors.
- **Satya validation**: Robust conversion for planner steps (dict/model-safe).
- **Websearch parsing**: Structured output with fallback Title/URL extraction.

## 🌐 Frontend Roadmap

### Phase 1: Local HTTP API (FastAPI)
- Endpoints:
  - `POST /chat` → send a message, returns assistant reply (streaming SSE optional)
  - `POST /tools/{name}` → invoke a tool (restricted/allowlist)
  - `GET /health` → readiness
- Reuse current assistant core; wrap interactive loop calls in async handlers.
- Auth: local-only by default; optional token for remote access.

### Phase 2: Web UI (React/Vite)
- Minimal chat UI with history, markdown rendering, tool call badges
- Settings page to manage keys (reads/writes `~/.muonry/.env` via API)
- Websearch toggle; debug panel for tool logs

### Phase 3: Packaging & Deploy
- Run as `muonry serve` to start API/UI
- Static build served by FastAPI or separate dev server
- Optional Docker image with non-root user and bind-mounted `~/.muonry/.env`

### Notes
- Keep websearch optional; UI should reflect feature availability
- Preserve sequential execution model; show step-by-step progress
