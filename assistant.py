#!/usr/bin/env python3
"""
Muonry - Interactive Coding Assistant with Bhumi
Uses OpenRouter and coding tools: apply_patch, shell, update_plan
"""

import asyncio
import contextlib
import os
import sys
import platform
import shlex
import subprocess
from pathlib import Path
import json
import dotenv   
import getpass
import re

# Load environment variables
dotenv.load_dotenv()

# --- Simple ANSI color helpers (no external deps required) ---
def _supports_color() -> bool:
    try:
        # Respect NO_COLOR and only color TTY outputs
        return sys.stdout.isatty() and os.getenv("NO_COLOR") is None
    except Exception:
        return False


class _Ansi:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"


_COLOR_ENABLED = _supports_color()


def _style(text: str, *, color: str | None = None, bold: bool = False, dim: bool = False) -> str:
    if not _COLOR_ENABLED:
        return text
    parts = []
    if bold:
        parts.append(_Ansi.BOLD)
    if dim:
        parts.append(_Ansi.DIM)
    if color:
        parts.append(color)
    return f"{''.join(parts)}{text}{_Ansi.RESET}"


def _info(msg: str) -> str:
    return _style(msg, color=_Ansi.CYAN)


def _success(msg: str) -> str:
    return _style(msg, color=_Ansi.GREEN)


def _warn(msg: str) -> str:
    return _style(msg, color=_Ansi.YELLOW)


def _error(msg: str) -> str:
    return _style(msg, color=_Ansi.RED, bold=True)

# Get OS info at startup
OS_INFO = f"{platform.system()} {platform.release()}"

# Add parent/src to path for bhumi import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bhumi.base_client import BaseLLMClient, LLMConfig

# --- Settings helpers (persist API keys in ~/.muonry/.env) ---
def _home_env_file() -> Path:
    p = Path.home() / ".muonry" / ".env"
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _mask_value(val: str) -> str:
    if not val:
        return ""
    v = str(val)
    if len(v) <= 8:
        return "*" * (len(v) - 2) + v[-2:]
    return v[:2] + "*" * (len(v) - 6) + v[-4:]


def _persist_key(name: str, value: str | None) -> None:
    """Set or remove a key in ~/.muonry/.env and update os.environ."""
    env_path = _home_env_file()
    existing = ""
    try:
        if env_path.exists():
            existing = env_path.read_text(encoding="utf-8")
    except Exception:
        existing = ""

    lines = existing.splitlines()
    pattern = re.compile(rf"^\s*{re.escape(name)}\s*=.*$")
    # Remove any existing lines for this key
    lines = [ln for ln in lines if not pattern.match(ln)]

    if value:
        lines.append(f"{name}={value}")
        os.environ[name] = value
    else:
        # Unset
        os.environ.pop(name, None)

    new_text = ("\n".join(lines)).strip() + ("\n" if lines else "")
    try:
        env_path.write_text(new_text, encoding="utf-8")
        try:
            env_path.chmod(0o600)
        except Exception:
            pass
    except Exception:
        pass


def _show_settings() -> None:
    print(_style("\n⚙️  Settings", color=_Ansi.BLUE, bold=True))
    env_path = _home_env_file()
    print(_style(f"Config file: {env_path}", color=_Ansi.BLUE, dim=True))

    groq = os.getenv("GROQ_API_KEY", "")
    cer = os.getenv("CEREBRAS_API_KEY", "")
    exa = os.getenv("EXA_API_KEY", "")

    print("\nCurrent keys (masked):")
    print(f" - GROQ_API_KEY: {'<not set>' if not groq else _mask_value(groq)}")
    print(f" - CEREBRAS_API_KEY: {'<not set>' if not cer else _mask_value(cer)}")
    print(f" - EXA_API_KEY: {'<not set>' if not exa else _mask_value(exa)}")

    print("\nProviders:")
    print(" - Groq: https://groq.com (sign in → console)")
    print(" - Cerebras: https://www.cerebras.ai")
    print(" - Exa (websearch): https://exa.ai")


def _settings_menu() -> None:
    while True:
        _show_settings()
        print("\nChoose an action:")
        print("  1) Set GROQ_API_KEY")
        print("  2) Set CEREBRAS_API_KEY")
        print("  3) Set EXA_API_KEY")
        print("  4) Clear a key")
        print("  0) Back")
        choice = input(_style("Select: ", color=_Ansi.CYAN)).strip()
        if choice == "0":
            return
        elif choice == "1":
            try:
                val = getpass.getpass("GROQ_API_KEY: ").strip()
            except Exception:
                val = ""
            if val:
                _persist_key("GROQ_API_KEY", val)
                print(_success("Saved GROQ_API_KEY."))
        elif choice == "2":
            try:
                val = getpass.getpass("CEREBRAS_API_KEY: ").strip()
            except Exception:
                val = ""
            if val:
                _persist_key("CEREBRAS_API_KEY", val)
                print(_success("Saved CEREBRAS_API_KEY."))
        elif choice == "3":
            try:
                val = getpass.getpass("EXA_API_KEY: ").strip()
            except Exception:
                val = ""
            if val:
                _persist_key("EXA_API_KEY", val)
                print(_success("Saved EXA_API_KEY."))
        elif choice == "4":
            name = input("Key to clear [GROQ_API_KEY|CEREBRAS_API_KEY|EXA_API_KEY]: ").strip()
            if name in {"GROQ_API_KEY", "CEREBRAS_API_KEY", "EXA_API_KEY"}:
                _persist_key(name, None)
                print(_warn(f"Cleared {name}."))
            else:
                print(_warn("Unknown key."))
        else:
            print(_warn("Invalid selection."))
from tools.apply_patch import apply_patch as do_apply_patch
from tools.shell import run_shell, ShellRequest
from tools.update_plan import load_plan, update_plan as do_update_plan, PlanItem, Status
from tools.build_analyzer import analyze_build_output, pick_package_manager
from tools.websearch import websearch as websearch_tool
# Orchestrator removed - using simple sequential approach with optional planning
import tools.toolset as toolset

# --- Minimal Markdown → ANSI renderer (no external deps) ---
import re

# Precompiled regex patterns for speed
_RE_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_RE_FENCE = re.compile(r"^```(.*)$")
_RE_BLOCKQUOTE = re.compile(r"^\s*>\s?(.*)$")
_RE_ULIST = re.compile(r"^(\s*)[-*]\s+(.+)$")
_RE_OLIST = re.compile(r"^(\s*)(\d+)[.)]\s+(.+)$")
_RE_HR = re.compile(r"^\s*---+\s*$")
_RE_CODE_SPAN = re.compile(r"`([^`]+)`")
_RE_BOLD = re.compile(r"\*\*(.+?)\*\*")
_RE_ITALIC_AST = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_RE_ITALIC_US = re.compile(r"_(.+?)_")
_RE_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_RE_AUTOLINK = re.compile(r"(?P<url>https?://[\w\-._~:/?#\[\]@!$&'()*+,;=%]+)")
_RE_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_RE_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")


def _md_heading(line: str) -> str:
    m = _RE_HEADING.match(line)
    if not m:
        return line
    level = len(m.group(1))
    text = m.group(2).strip()
    if not _COLOR_ENABLED:
        return text.upper() if level <= 2 else text
    color = _Ansi.CYAN if level == 1 else (_Ansi.BLUE if level == 2 else _Ansi.MAGENTA)
    return f"{_Ansi.BOLD}{color}{text}{_Ansi.RESET}"


def _md_inline(text: str) -> str:
    # Protect inline code spans first
    code_spans = []
    def _stash_code(m):
        code_spans.append(m.group(1))
        return f"\u0000{len(code_spans)-1}\u0000"

    text = _RE_CODE_SPAN.sub(_stash_code, text)

    # Bold **text**
    def _bold(m):
        inner = m.group(1)
        return _style(inner, bold=True) if _COLOR_ENABLED else inner.upper()
    text = _RE_BOLD.sub(_bold, text)

    # Italic *text* or _text_
    def _italic(m):
        inner = m.group(1)
        return _style(inner, dim=True) if _COLOR_ENABLED else inner
    text = _RE_ITALIC_AST.sub(_italic, text)
    text = _RE_ITALIC_US.sub(_italic, text)

    # Links [text](url)
    def _link(m):
        label, url = m.group(1), m.group(2)
        if _COLOR_ENABLED:
            return f"{_style(label, bold=True)} ({_style(url, color=_Ansi.BLUE)})"
        return f"{label} ({url})"
    text = _RE_LINK.sub(_link, text)

    # Images ![alt](url) → alt (url)
    def _image(m):
        alt, url = m.group(1) or "image", m.group(2)
        label = alt or "image"
        if _COLOR_ENABLED:
            return f"{_style(label, bold=True)} [{_style('img', color=_Ansi.MAGENTA)}] ({_style(url, color=_Ansi.BLUE)})"
        return f"{label} [img] ({url})"
    text = _RE_IMAGE.sub(_image, text)

    # Autolinks
    def _autolink(m):
        url = m.group("url")
        if _COLOR_ENABLED:
            return _style(url, color=_Ansi.BLUE)
        return url
    text = _RE_AUTOLINK.sub(_autolink, text)

    # Restore code spans
    def _restore_code(m):
        idx = int(m.group(1))
        code = code_spans[idx]
        if _COLOR_ENABLED:
            return f"{_Ansi.YELLOW}`{code}`{_Ansi.RESET}"
        return f"`{code}`"
    text = re.sub(r"\u0000(\d+)\u0000", _restore_code, text)
    return text


def render_markdown_to_ansi(md: str) -> str:
    lines = md.splitlines()
    out_lines: list[str] = []
    in_code = False
    code_lang = None
    code_block: list[str] = []

    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        line = raw.rstrip("\n")

        # Handle fenced code blocks
        fence = _RE_FENCE.match(line)
        if fence:
            if not in_code:
                in_code = True
                code_lang = (fence.group(1) or "").strip() or None
                code_block = []
            else:
                # closing fence -> flush code block
                content = "\n".join(code_block)
                if _COLOR_ENABLED:
                    header = f"{_Ansi.DIM}{_Ansi.BLUE}┌─ code{(':'+code_lang) if code_lang else ''} ─────────────────────────┐{_Ansi.RESET}"
                    footer = f"{_Ansi.DIM}{_Ansi.BLUE}└──────────────────────────────────────────────┘{_Ansi.RESET}"
                    body = "\n".join(f"{_Ansi.DIM}{_Ansi.BLUE}│{_Ansi.RESET} {l}" for l in content.splitlines() or [""])
                    out_lines.extend([header, body, footer])
                else:
                    out_lines.extend(["[code]", content, "[/code]"])
                in_code = False
                code_lang = None
                code_block = []
            i += 1
            continue

        if in_code:
            code_block.append(raw)
            i += 1
            continue

        # Tables: header|header, separator, then rows
        if "|" in line and i + 1 < n and _RE_TABLE_SEP.match(lines[i + 1].strip()):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            j = i + 2
            rows = []
            while j < n and "|" in lines[j]:
                row = [c.strip() for c in lines[j].strip().strip("|").split("|")]
                rows.append(row)
                j += 1
            # Simple render (no width calc for speed)
            header_line = " | ".join(header)
            out_lines.append(_style(header_line, bold=True) if _COLOR_ENABLED else header_line)
            out_lines.append("—" * max(10, len(header_line)))
            for r in rows:
                out_lines.append(" | ".join(r))
            i = j
            continue

        # Headings
        if line.startswith("#"):
            out_lines.append(_md_heading(line))
            i += 1
            continue

        # Blockquote
        bq = _RE_BLOCKQUOTE.match(line)
        if bq:
            inner = bq.group(1)
            if _COLOR_ENABLED:
                out_lines.append(f"{_Ansi.DIM}{_Ansi.GREEN}│{_Ansi.RESET} {_md_inline(inner)}")
            else:
                out_lines.append(f"> {inner}")
            i += 1
            continue

        # Lists (unordered) with checkboxes
        m = _RE_ULIST.match(line)
        if m:
            indent, item = m.groups()
            item = item.replace("[ ]", "☐").replace("[x]", "☑").replace("[X]", "☑")
            bullet = "•"
            if _COLOR_ENABLED:
                bullet = f"{_Ansi.MAGENTA}•{_Ansi.RESET}"
            out_lines.append(f"{indent}{bullet} {_md_inline(item)}")
            i += 1
            continue

        # Ordered lists (preserve numbers)
        m = _RE_OLIST.match(line)
        if m:
            indent, num, item = m.groups()
            out_lines.append(f"{indent}{num}. {_md_inline(item)}")
            i += 1
            continue

        # Horizontal rule
        if _RE_HR.match(line):
            rule = "—" * 30
            out_lines.append(_style(rule, color=_Ansi.DIM) if _COLOR_ENABLED else rule)
            i += 1
            continue

        # Blank line
        if line.strip() == "":
            out_lines.append("")
            i += 1
            continue

        # Paragraph with inline formatting
        out_lines.append(_md_inline(line))
        i += 1

    # If file ended while in code fence, flush it plainly
    if in_code and code_block:
        content = "\n".join(code_block)
        out_lines.append(content)

    return "\n".join(out_lines)

# Conversational talk tool: moved to tools.toolset
async def talk_tool(content: str) -> str:
    return await toolset.talk_tool(content)

# Simple Planner Tool using Cerebras (moved to tools.toolset)
async def planner_tool(task: str, context: str = "") -> str:
    return await toolset.planner_tool(task, context)

# Coding Tools for LLM
async def apply_patch_tool(patch: str, cwd: str = ".") -> str:
    return await toolset.apply_patch_tool(patch, cwd)

async def run_shell_tool(command: str, workdir: str = None, timeout_ms: int = 30000) -> str:
    return await toolset.run_shell_tool(command, workdir, timeout_ms)

async def update_plan_tool(steps: list = None, explanation: str = None) -> str:
    return await toolset.update_plan_tool(steps, explanation)

async def smart_run_shell_tool(command: str, workdir: str = None, timeout_ms: int = 300000, auto_fix: bool = False) -> str:
    return await toolset.smart_run_shell_tool(command, workdir, timeout_ms, auto_fix)

async def read_file_tool(file_path: str, start_line: int = None, end_line: int = None) -> str:
    return await toolset.read_file_tool(file_path, start_line, end_line)

async def grep_tool(pattern: str, file_path: str = ".", recursive: bool = True, case_sensitive: bool = False) -> str:
    return await toolset.grep_tool(pattern, file_path, recursive, case_sensitive)

async def search_replace_tool(file_path: str, search_text: str, replace_text: str, all_occurrences: bool = True) -> str:
    return await toolset.search_replace_tool(file_path, search_text, replace_text, all_occurrences)

async def get_system_info_tool() -> str:
    return await toolset.get_system_info_tool()

async def quick_check_tool(kind: str, target: str = ".", max_files: int = 200, timeout_ms: int = 120000) -> str:
    return await toolset.quick_check_tool(kind, target, max_files, timeout_ms)

async def interactive_shell_tool(
    command: str,
    workdir: str | None = None,
    timeout_ms: int = 600000,
    answers: list[dict] | None = None,
    input_script: str | None = None,
    env: dict | None = None,
    transcript_limit: int = 20000,
) -> str:
    return await toolset.interactive_shell_tool(command, workdir, timeout_ms, answers, input_script, env, transcript_limit)

async def write_file_tool(file_path: str, content: str, overwrite: bool = True) -> str:
    return await toolset.write_file_tool(file_path, content, overwrite)

class MuonryAssistant:
    def __init__(self):
        self.client = None
        # Primary and fallback models
        self.primary_model = "groq/moonshotai/kimi-k2-instruct"
        self.fallback_model = "cerebras/qwen-3-coder-480b"
        # Sliding window budget (characters). 131k is hard limit; keep margin.
        try:
            self.max_context_chars = int(os.getenv("MUONRY_MAX_CONTEXT_CHARS", "120000"))
        except Exception:
            self.max_context_chars = 120000
        
    async def setup(self):
        """Initialize the assistant with OpenRouter"""
        # Re-enable verbose websearch debug by default; unset MUONRY_WEBSEARCH_DEBUG to disable
        os.environ.setdefault("MUONRY_WEBSEARCH_DEBUG", "1")
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print(_error("❌ Error: GROQ_API_KEY environment variable not set"))
            return False
            
        config = LLMConfig(
            api_key=api_key,
            model=self.primary_model,  # Primary model via Groq
            debug=True
        )
        
        self.client = BaseLLMClient(config)
        await self.register_tools()
        return True

    async def _completion_with_fallback(self, messages: list[dict]) -> dict:
        """Call completion; on rate limit, switch to fallback model and retry once."""
        # Prepare a trimmed copy of messages under char budget
        def _trim_messages(msgs: list[dict]) -> list[dict]:
            if not msgs:
                return msgs
            budget = max(10000, self.max_context_chars)
            sys_msg = msgs[0] if msgs and msgs[0].get("role") == "system" else None
            rest = msgs[1:] if sys_msg else msgs[:]
            total = 0
            kept_rev: list[dict] = []
            for m in reversed(rest):
                c = len(str(m.get("content", "")))
                if total + c > budget:
                    break
                kept_rev.append(m)
                total += c
            kept = list(reversed(kept_rev))
            if sys_msg:
                return [sys_msg] + kept
            return kept

        async def _call() -> dict:
            return await self.client.completion(_trim_messages(messages))

        def _is_rate_limit(resp: dict) -> bool:
            # Check explicit error structure or text mentioning rate limit
            try:
                err = resp.get("error")
                if isinstance(err, dict):
                    msg = str(err.get("message", "")).lower()
                    code = str(err.get("code", "")).lower()
                    if "rate limit" in msg or "ratelimit" in msg or code == "ratelimitexceeded":
                        return True
                txt = str(resp.get("text", "")).lower()
                if "rate limit" in txt or "ratelimit" in txt:
                    return True
            except Exception:
                pass
            return False

        # First attempt with current client/model
        resp = await _call()
        if not _is_rate_limit(resp):
            return resp

        # Switch to fallback model and retry once
        print(_warn(f"Rate limit encountered on {self.client.config.model if hasattr(self.client, 'config') else 'primary model'}; switching to {self.fallback_model} and retrying once..."))
        try:
            api_key = os.getenv("GROQ_API_KEY")
            fb_config = LLMConfig(api_key=api_key, model=self.fallback_model, debug=True)
            self.client = BaseLLMClient(fb_config)
        except Exception as e:
            print(_error(f"Failed to switch to fallback model: {e}"))
            return resp
        return await _call()
        
    async def register_tools(self):
        """Register coding tools with Bhumi"""
        print(_info("🔧 Registering coding tools..."))
        
        # Patch tool (PREFERRED for file modifications)
        self.client.register_tool(
            name="apply_patch",
            func=apply_patch_tool,
            description="PREFERRED tool for modifying existing files. Use patch format to add/update/delete content safely.",
            parameters={
                "type": "object",
                "properties": {
                    "patch": {
                        "type": "string",
                        "description": "Patch content in unified diff format between **_ Begin Patch and _** End Patch markers"
                    }
                },
                "required": ["patch"]
            }
        )
        
        # Shell tool
        self.client.register_tool(
            name="run_shell",
            func=run_shell_tool,
            description="Execute a shell command",
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute"
                    },
                    "workdir": {
                        "type": "string",
                        "description": "Working directory for command (optional, default: current directory)"
                    },
                    "timeout_ms": {
                        "type": "integer",
                        "description": "Timeout in milliseconds (optional, default: 30000)"
                    }
                },
                "required": ["command"],
                "additionalProperties": False
            }
        )

        # Smart shell tool
        self.client.register_tool(
            name="smart_run_shell",
            func=smart_run_shell_tool,
            description="Execute a shell command, analyze failures, suggest fixes, and optionally auto-fix safe issues (e.g., install missing deps).",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "workdir": {"type": "string", "description": "Working directory (optional)"},
                    "timeout_ms": {"type": "integer", "description": "Timeout in ms (optional, default: 300000)"},
                    "auto_fix": {"type": "boolean", "description": "If true, apply safe fixes (e.g., install missing deps) and re-run"}
                },
                "required": ["command"],
                "additionalProperties": False
            }
        )

        # Interactive shell tool (PTY-based)
        self.client.register_tool(
            name="interactive_shell",
            func=interactive_shell_tool,
            description=(
                "Run interactive CLI commands via a pseudo-terminal. Match prompts with regex and send answers. "
                "Useful for wizards like create-next-app, npm init, etc."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run (e.g., npx create-next-app@latest .)"},
                    "workdir": {"type": "string", "description": "Working directory (optional)"},
                    "timeout_ms": {"type": "integer", "description": "Overall timeout in ms (default: 600000)"},
                    "answers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "expect": {"type": "string", "description": "Regex to match in transcript"},
                                "send": {"type": "string", "description": "Text to send when matched (newline auto-appended)"}
                            },
                            "required": ["expect", "send"],
                            "additionalProperties": False
                        },
                        "description": "Ordered expect/send rules"
                    },
                    "input_script": {"type": "string", "description": "Initial input to send on start (optional)"},
                    "env": {"type": "object", "description": "Extra environment variables (optional)"},
                    "transcript_limit": {"type": "integer", "description": "Max transcript bytes to retain (default: 20000)"}
                },
                "required": ["command"],
                "additionalProperties": False
            }
        )
        
        # Plan tool
        self.client.register_tool(
            name="update_plan",
            func=update_plan_tool,
            description="Update the development plan with new steps",
            parameters={
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of development steps"
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Explanation of plan changes"
                    }
                }
            }
        )

        # Talk tool (use for conversational replies; prints to terminal)
        self.client.register_tool(
            name="talk",
            func=talk_tool,
            description=(
                "Use this to respond conversationally in the terminal. "
                "Render answers, stories, explanations, brainstorming, and Q&A here. "
                "Do not write files unless the user explicitly asks to save/create."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Markdown content to say to the user"}
                },
                "required": ["content"]
            }
        )

        # File read tool
        self.client.register_tool(
            name="read_file",
            func=read_file_tool,
            description="Read contents of a file, optionally specifying line range",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    }
                },
                "required": ["file_path"]
            }
        )
        
        # Grep tool
        self.client.register_tool(
            name="grep",
            func=grep_tool,
            description="Search for patterns in files using grep",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Pattern to search for"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "File or directory to search in (optional, default: current directory)"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Whether to search recursively (optional, default: true)"
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Whether search should be case sensitive (optional, default: False)"
                    }
                },
                "required": ["pattern"],
                "additionalProperties": False
            }
        )
        
        # Search and replace tool (for simple text replacements)
        self.client.register_tool(
            name="search_replace",
            func=search_replace_tool,
            description="For simple text replacements in existing files. Use apply_patch for complex changes.",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to modify"
                    },
                    "search_text": {
                        "type": "string",
                        "description": "Text to search for"
                    },
                    "replace_text": {
                        "type": "string",
                        "description": "Text to replace with"
                    }
                },
                "required": ["file_path", "search_text", "replace_text"]
            }
        )
        
        # System info tool
        self.client.register_tool(
            name="get_system_info",
            func=get_system_info_tool,
            description="Get system information including OS, Python version, and current directory",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
        
        # Quick project/file checker (python | rust | js)
        self.client.register_tool(
            name="quick_check",
            func=quick_check_tool,
            description="Quickly sanity-check a project or file for Python (ast.parse), Rust (cargo/rustc), or JS/TS (tsc/package.json)",
            parameters={
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["python", "rust", "js"], "description": "Type of project/file to check"},
                    "target": {"type": "string", "description": "Path to file or directory (default: .)"},
                    "max_files": {"type": "integer", "description": "Max files to scan for syntax (default: 200)"},
                    "timeout_ms": {"type": "integer", "description": "Per-command timeout in ms (default: 120000)"}
                },
                "required": ["kind"],
                "additionalProperties": False
            }
        )

        # Web search (Exa) tool - off by default; requires EXA_API_KEY when enabled
        self.client.register_tool(
            name="websearch",
            func=websearch_tool,
            description=(
                "Search the web via Exa. Off by default; set enabled=true and provide EXA_API_KEY env var."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "enabled": {"type": "boolean", "description": "Must be true to execute search (default: false)"}
                },
                "additionalProperties": False
            }
        )
        
        # Write file tool (for creating NEW files only)
        self.client.register_tool(
            name="write_file",
            func=write_file_tool,
            description="Create NEW files only. For modifying existing files, use apply_patch or search_replace instead.",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the NEW file to create"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content for the new file"
                    }
                },
                "required": ["file_path", "content"]
            }
        )
        
        # Simple Planner Tool (using Cerebras for complex task breakdown)
        self.client.register_tool(
            name="planner",
            func=planner_tool,
            description="Break down complex tasks into sequential steps using AI planning. Useful for multi-file tasks or complex projects.",
            parameters={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The complex task to break down into sequential steps"
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context about the task (optional)"
                    }
                },
                "required": ["task"]
            }
        )
        
        print(_success("✅ Tools registered successfully!"))
        print(_style(f"🔍 Debug: Registered {len(self.client.tool_registry.get_definitions())} tools", color=_Ansi.BLUE, dim=True))
    
    async def interactive_loop(self):
        """Main conversational loop"""
        # Initial system message with orchestrator-first approach
        from datetime import datetime
        now_str = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z%z")
        conversation = [{
            "role": "system", 
            "content": f"""You are Muonry, an expert coding assistant that helps with software development tasks efficiently and systematically.

🎯 **Your Approach:**
- **Simple tasks:** Use `talk` to converse; use other tools as needed
- **Complex tasks:** Use the planner tool first, then execute steps sequentially
- **Always be practical and get things done**

💡 **When to Use Planning:**
Use the `planner` tool for complex tasks involving multiple files or steps:
- "Create X files/stories/components"
- "Build a complete application" 
- "Generate multiple related files"
- "Create a project with several parts"

**Planning Workflow:**
1. Call `planner(task="description")` to break down complex tasks
2. Follow the generated plan step-by-step using appropriate tools
3. Execute each step sequentially with write_file, apply_patch, etc.

🔧 **Available Tools:**
- **Conversation:** talk (default for stories, explanations, brainstorming, Q&A)
- **Planning:** planner (break down complex tasks into steps)
- **File ops:** read_file, write_file (NEW files), apply_patch (PREFERRED for modifications)
- **System:** run_shell, interactive_shell, smart_run_shell, quick_check, get_system_info, grep, search_replace  
- **Development:** update_plan
 - **Web:** websearch (Exa web search; off by default — set enabled=true and provide EXA_API_KEY)

🧭 **When to Save vs. Talk:**
- For conversational requests (tell a story, explain, discuss, brainstorm), call `talk(content=...)` and DO NOT create files.
- Only use `write_file` if the user explicitly asks to save, create, write, or export to a file/path.

🚀 **Examples:**
- Chat: "Tell me a story" → Use `talk` to narrate in terminal.
- Simple: "Read config.json" → Use read_file directly
- Complex: "Create 5 story files about Travis Scott" → Use planner first, then write_file for each story

Be efficient, practical, and always deliver working solutions. Use planning when it helps organize complex work.

Current OS: {OS_INFO}
Current Datetime: {now_str}"""
        }]
        while True:
            try:
                user_input = input(_style("\n💬 You: ", color=_Ansi.CYAN, bold=True)).strip()
                if not user_input:
                    continue

                # Commands
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print(_success("👋 Goodbye!"))
                    break
                if user_input.strip().lower() in {'/settings', 'settings'}:
                    _settings_menu()
                    continue

                # Fast local Markdown preview: md <file>
                try:
                    tokens = shlex.split(user_input)
                except Exception:
                    tokens = user_input.split()
                if tokens and tokens[0].lower() in {"md", "viewmd"}:
                    if len(tokens) < 2:
                        print(_warn("Usage: md <path-to-markdown>"))
                        continue
                    path_arg = user_input[len(tokens[0]):].strip()
                    # Handle unquoted paths with spaces by using the remainder string
                    path_str = path_arg.strip()
                    p = Path(path_str)
                    if not p.exists():
                        print(_error(f"File not found: {path_str}"))
                        continue
                    try:
                        content = p.read_text(encoding="utf-8")
                    except Exception as e:
                        print(_error(f"Failed to read {path_str}: {e}"))
                        continue
                    print(_style(f"\n📄 {p}", color=_Ansi.BLUE, bold=True))
                    print(render_markdown_to_ansi(content))
                    continue

                # Add user message to conversation
                conversation.append({"role": "user", "content": user_input})

                # Get response from assistant (with rate-limit fallback)
                response = await self._completion_with_fallback(conversation.copy())

                if response and 'text' in response:
                    assistant_message = response['text']
                    # Pretty-print Markdown response in terminal
                    print(_style("\n Muonry :>>", color=_Ansi.MAGENTA, bold=True))
                    print(render_markdown_to_ansi(assistant_message))
                    conversation.append({"role": "assistant", "content": assistant_message})

                # Keep conversation manageable
                if len(conversation) > 20:
                    conversation = conversation[-20:]

            except KeyboardInterrupt:
                print(_success("\n👋 Goodbye!"))
                break
            except Exception as e:
                print(_error(f"\n❌ Error: {e}"))
                print(_warn("Let's continue..."))
    


async def main():
    assistant = MuonryAssistant()
    if await assistant.setup():
        await assistant.interactive_loop()
    else:
        print(_error("Failed to initialize assistant"))
        
if __name__ == "__main__":
    asyncio.run(main())
