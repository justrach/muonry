# Muonry AI Coding Assistant - Overview & Capabilities

This project is a **simplified, sequential AI coding assistant** with optional planning capabilities. The complex multi-agent orchestrator has been removed in favor of a reliable, straightforward approach that actually works.

## Root Directory (`/muonry`)

- **`agent.md`** - This file: comprehensive documentation about capabilities and usage
- **`assistant.py`** - **Main sequential assistant** (648 lines) with optional planning
- **`README.md`** - Project overview and basic setup instructions
- **`tools/toolset.py`** - Consolidated tool implementations (planner, shell, patching, file ops, quick checks, interactive shell, websearch)
- **`.env`** - Environment variables for configuration (API keys, etc.)
- **`improvements.md`** - Log of planned improvements and features

## Key Directories

### `tools/` Directory
Contains utility modules and helper functions:
- `toolset.py`: Consolidated tool implementations registered by `assistant.py`
- `build_analyzer.py`: Build failure analysis and auto-fix suggestions
- `shell.py`: Shell command execution and management
- `apply_patch.py`: Advanced file patching tool
- `update_plan.py`: Plan management utilities
- `websearch.py`: Exa-powered web search tool (off by default; requires `EXA_API_KEY`)
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
- **Exa web search** with `websearch` (off by default). Requires `EXA_API_KEY` or an explicit `api_key` parameter. Returns structured JSON results and includes a fallback parser that extracts Title/URL pairs when providers return text blocks.

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
- **Interactive chat** mode (run `python assistant.py`)
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
python assistant.py
```

### **Environment Setup**
```bash
export GROQ_API_KEY=your_groq_key
export CEREBRAS_API_KEY=your_cerebras_key  # Optional for planning
export EXA_API_KEY=your_exa_key            # Optional for websearch
export MUONRY_MAX_CONTEXT_CHARS=120000     # Optional context cap (chars)
```

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

---

## Usage Patterns

- **Simple Tasks**: `"Read config.json"` → Direct tool usage
- **Complex Tasks**: `"Create 6 Fire Nation stories"` → Planner + sequential execution
- **Configuration**: Environment settings via `.env` file
- **Reliability**: No worker coordination or orchestration complexity
- **Development Flow**: New features are typically added by creating new agent files in `agents/` or extending existing ones
- **Modularity**: The structure supports adding new capabilities without modifying core files
- **Testing**: Individual agents can be tested independently before integration

## File Relationships
- `assistant.py` imports and registers tools from `tools/` (e.g., `websearch`, `apply_patch`, `shell`).
- Shared utilities and additional tools live under `tools/`.

## ✅ **COMPLETED: Simplified Architecture**

### ✅ **Planning System Implementation**
- [x] ✅ Created planner tool with Cerebras integration
- [x] ✅ Implemented robust JSON parsing (orjson + Satya)
- [x] ✅ Added sequential task execution
- [x] ✅ Removed broken orchestrator complexity
- [x] ✅ Tested with multi-file story generation
- [x] ✅ Documented simplified usage patterns

### 🚀 **Architecture Benefits**
- **Reliability:** No coordination failures or worker idle states
- **Simplicity:** Clean, understandable execution flow
- **Planning:** Optional AI-powered task breakdown
- **Performance:** Sequential execution without race conditions
- **Maintainability:** Single assistant file vs complex orchestrator
- Configuration flows from `.env` to the main application and then to individual agents

## 🆕 Recent Enhancements
- **Rate-limit fallback**: Automatic retry with a fallback model on rate-limit.
- **Context trimming**: Sliding-window strategy prevents context overflow errors.
- **Satya validation**: Robust conversion for planner steps (dict/model-safe).
- **Websearch parsing**: Structured output with fallback Title/URL extraction.
