# Muonry AI Coding Assistant - Project Summary

## Overview
Muonry is a **simplified, sequential AI coding assistant** with optional planning capabilities. It replaces complex multi-agent orchestration with a reliable, straightforward approach that actually works.

## Project Structure

### Root Files
- **`assistant.py`** - Main sequential assistant (648 lines)
- **`agent.md`** - Comprehensive documentation and capabilities overview
- **`README.md`** - Project overview and basic setup instructions
- **`pyproject.toml`** - Packaging configuration
- **`.env`** - Environment variables for API keys

### Core Python Modules
#### `muonry/` Package
- **`__init__.py`** - Package initialization
- **`cli.py`** - Command-line interface

#### `tools/` Directory (441 lines total)
- **`toolset.py`** - Consolidated tool implementations (planner, shell, patching, file ops)
- **`apply_patch.py`** - Advanced file patching tool
- **`shell.py`** - Shell command execution and management
- **`build_analyzer.py`** - Build failure analysis and auto-fix suggestions
- **`update_plan.py`** - Plan management utilities
- **`websearch.py`** - Exa-powered web search tool (optional)
- **`orchestrator.py`** - Deprecated (excluded from active codebase)

### Frontend (Next.js)
- **`frontend/`** - Next.js web application
- **`frontend/package.json`** - Frontend dependencies
- **`frontend/next.config.ts`** - Next.js configuration
- **`frontend/tsconfig.json`** - TypeScript configuration

### Build & Distribution
- **`dist/`** - Built packages (wheel and source distribution)
- **`muonry.egg-info/`** - Package metadata
- **`MANIFEST.in`** - Package manifest

## Key Features

### AI Models
- **Primary**: `groq/moonshotai/kimi-k2-instruct` (requires `GROQ_API_KEY`)
- **Fallback**: `cerebras/qwen-3-coder-480b` (auto retry on rate-limit)
- **Planner**: `cerebras/qwen-3-235b-a22b-thinking-2507` (requires `CEREBRAS_API_KEY`)

### Core Capabilities
- **File Operations**: Create, read, update, patch files
- **Shell Commands**: Execute system commands with auto-fix
- **Project Validation**: Syntax checking for Python/Rust/JS projects
- **Web Search**: Exa-powered search (optional, requires `EXA_API_KEY`)
- **Planning**: AI-powered task breakdown for complex projects
- **Interactive Chat**: Terminal-based conversational interface

### Tool Set
- `read_file`, `write_file`, `apply_patch` - File operations
- `run_shell`, `smart_run_shell` - Command execution
- `get_system_info`, `quick_check` - System information
- `websearch` - Web search (off by default)
- `interactive_shell` - PTY for CLI wizards
- `planner` - Task planning and decomposition

## Usage

### Quick Start
```bash
export GROQ_API_KEY=your_key
python assistant.py
```

### CLI Commands
```bash
muonry                    # Interactive chat mode
python -m muonry.cli      # Alternative
```

### Settings Management
```env
GROQ_API_KEY=your_groq_key
CEREBRAS_API_KEY=your_cerebras_key    # Optional
EXA_API_KEY=your_exa_key            # Optional (websearch)
MUONRY_MAX_CONTEXT_CHARS=120000       # Optional
```

## Statistics
- **Total Python Code**: 1,238 lines
- **Core Assistant**: 648 lines
- **Active Tools**: 441 lines
- **Dependencies**: 149 lines

## Installation
```bash
pip install muonry                    # Base install
pip install "muonry[websearch]"       # With websearch support
```

## Package Configuration
- **Python**: >= 3.10
- **Entry Point**: `muonry = muonry.cli:main`
- **Distribution**: Universal wheel (`py3-none-any`)
- **URLs**: https://github.com/justrach/muonry

## Next Steps
- Local HTTP API with FastAPI
- Web UI with React/Vite
- Docker support
- Enhanced web interface