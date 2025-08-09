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
import time
from typing import Optional
try:
    import select  # POSIX readiness checks
except Exception:  # pragma: no cover
    select = None  # type: ignore
try:
    import msvcrt  # Windows console keyboard checks
except Exception:  # pragma: no cover
    msvcrt = None  # type: ignore

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
        # Track Ctrl-C presses for double-press-to-exit behavior
        self._last_interrupt_at: float = 0.0
        
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
        # Register both canonical name and a compatibility alias without underscore.
        for tool_name in ("apply_patch", "applypatch"):
            self.client.register_tool(
                name=tool_name,
                func=apply_patch_tool,
                description=(
                    "PREFERRED for modifying existing files. Accepts Muonry patch envelope; "
                    "also auto-wraps common unified diffs (---/+++ @@)."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "patch": {
                            "type": "string",
                            "description": "Patch content (Muonry patch or standard unified diff)"
                        },
                        "cwd": {
                            "type": "string",
                            "description": "Working directory for applying the patch (optional)"
                        }
                    },
                    "required": ["patch"],
                    "additionalProperties": False
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
            "content": f"""
You are Muonry, a terminal-first AI coding assistant. You help the user get software work done quickly, safely, and pragmatically.

SAFETY
- Never assist with malicious or harmful intent.
- Prefer minimal, non-destructive actions; explain risks briefly when relevant.

INTERACTION CONTRACT
- If the user asks a question (how to perform a task), provide concise instructions only and then ask if they want you to perform them.
- If the user gives a task/command:
  - Simple tasks: execute directly without unnecessary questions.
  - Complex tasks: ask brief, high-value clarifying questions only when necessary to proceed; otherwise plan and act.
- Be concise. Prefer bullet points and short code blocks. Reference files and symbols using backticks.

TOOLS (Muonry runtime)
- talk: respond with markdown in terminal. Use for explanations and non-file outputs.
- planner: break down complex tasks into steps; then execute sequentially.
- apply_patch: PREFERRED for modifying existing files safely.
- write_file: ONLY for creating new files when the user explicitly asks to save/create/export.
- read_file, grep, search_replace: reading and simple text edits.
- run_shell: non-interactive commands; avoid pagers; prefer options that prevent pagination.
- smart_run_shell: run, analyze failures, suggest or apply safe fixes.
- interactive_shell: use only for CLI wizards (short, scripted interactions), not for long interactive sessions.
- quick_check, get_system_info, update_plan: diagnostics and planning helpers.
- websearch (optional): Exa search. Off by default; requires `EXA_API_KEY` and install of optional extra `muonry[websearch]`. Must set `enabled=true`.

SHELL & VCS POLICY
- Do not change directories implicitly; prefer specifying working directory explicitly.
- Avoid interactive/fullscreen commands unless explicitly asked; prefer flags that produce non-paginated output (e.g., set pager to cat or use --no-pager if available).
- For git, avoid pagers and keep outputs concise.

SECRETS & SETTINGS
- Never display secrets. If a command needs a secret, use an environment variable placeholder (e.g., {{FOO_API_KEY}}) and instruct the user to set it.
- Keys are managed via /settings and persisted to `~/.muonry/.env` with 0600 perms.

WHEN TO SAVE VS. TALK
- Conversational requests → use talk. Do NOT create files.
- Only create or modify files when asked or when required to complete the explicit task outcome.

PLANNING WORKFLOW (for complex tasks)
1) Call planner with the high-level task.
2) Execute steps sequentially using apply_patch/write_file/run_shell/etc.
3) Keep actions minimal and verifiable; show progress succinctly.

OUTPUT STYLE
- Markdown-friendly. Use short bullets. Reference paths like `path/to/file.py`.
- Keep context trimmed. Be explicit about assumptions.

WEB SEARCH
- Only use `websearch` if explicitly enabled and configured. No browsing beyond Exa API.

RUNTIME
- Primary model: groq/moonshotai/kimi-k2-instruct; fallback: cerebras/qwen-3-coder-480b (auto on rate-limit).
- Context trimming keeps the latest turns under budget.

FRONTEND BRANDING (when editing web UI)
- Choose style by context, not always developer-only.
- Modes and font options (use open licenses when possible):
  - Marketing Landing: Space Grotesk / Sora / Outfit / Geist Sans for headlines and UI; strong CTAs; allow tasteful text gradients.
  - Developer/Docs: IBM Plex Mono / JetBrains Mono / Fira Code; monospace accents; high contrast; minimal gradients.
  - App/Dashboard: Inter / Geist Sans / IBM Plex Sans; compact UI, subtle cards, clear focus rings.
  - Blog/Longform: Source Serif Pro / IBM Plex Serif for body; Inter/Geist Sans for UI; comfortable reading width.
- Palette: white base with cyan–magenta brand accents; ensure accessible contrast; support dark mode.
- Gradients: sparingly; text (#06b6d4 → #d946ef), panels (rgba(6,182,212,0.2) → rgba(217,70,239,0.12)); avoid heavy motion.
- Accessibility: keyboard focus-visible rings, prefers-reduced-motion, legible sizes.
- No vendor lockups by default; do not add “Powered by …” unless the user asks.

Environment OS: {OS_INFO}
Current Datetime: {now_str}
"""
        }]
        while True:
            try:
                user_input = self._smart_read_input()
                if user_input is None:
                    # EOF (e.g., Ctrl-D) — exit quietly
                    break
                # Keep a trimmed copy for command checks, but preserve original
                trimmed = user_input.strip()
                if not trimmed:
                    continue

                # Commands
                if trimmed.lower() in ['quit', 'exit', 'bye']:
                    break
                if trimmed.lower() in {'/settings', 'settings'}:
                    _settings_menu()
                    continue

                # Fast local Markdown preview: md <file>
                try:
                    # Only parse tokens for single-line commands
                    tokens = shlex.split(trimmed)
                except Exception:
                    tokens = trimmed.split()
                if tokens and tokens[0].lower() in {"md", "viewmd"}:
                    if len(tokens) < 2:
                        print(_warn("Usage: md <path-to-markdown>"))
                        continue
                    path_arg = trimmed[len(tokens[0]):].strip()
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
                now = time.time()
                if self._last_interrupt_at and (now - self._last_interrupt_at) < 2.0:
                    # Exit quietly on second Ctrl-C
                    break
                # First Ctrl-C: brief hint; second within 2s exits
                self._last_interrupt_at = now
                print(_warn("\nInterrupted. Press Ctrl-C again to exit."))

    # --- Improved input handling (supports Ctrl+V multi-line paste and /paste mode) ---
    def _smart_read_input(self) -> Optional[str]:
        """Read user input robustly.

        - Captures multi-line pastes (Ctrl+V) by draining stdin for a short window.
        - Supports explicit paste mode: type `/paste` to enter, then finish with a line `EOF` or ```.
        - Strips terminal bracketed-paste markers if present.
        - Returns None on EOF (Ctrl-D) to signal exit.
        """
        prompt = _style("\n💬 You: ", color=_Ansi.CYAN, bold=True)
        try:
            first_line = input(prompt)
        except EOFError:
            return None
        except KeyboardInterrupt:
            raise

        # Explicit paste mode
        if first_line.strip().lower() in {"/paste", ":paste", "paste"}:
            print(_style("Paste multi-line text. End with `EOF` or ``` on its own line.", color=_Ansi.BLUE, dim=True))
            lines: list[str] = []
            while True:
                try:
                    ln = input()
                except EOFError:
                    # Treat EOF as finish
                    break
                except KeyboardInterrupt:
                    print(_warn("Paste cancelled."))
                    return ""
                if ln.strip() in {"EOF", "```"}:
                    break
                lines.append(ln)
            content = "\n".join(lines)
            return self._clean_paste_text(content)

        # Greedy-drain stdin for fast multi-line paste (POSIX) or best-effort on Windows
        extra = self._drain_stdin_lines(max_idle_ms=120)
        if extra:
            full = "\n".join([first_line] + extra)
            return self._clean_paste_text(full)
        return self._clean_paste_text(first_line)

    def _drain_stdin_lines(self, max_idle_ms: int = 120) -> list[str]:
        """Collect additional lines already queued in stdin.

        Reads lines while input is immediately available, stopping after a short idle period.
        """
        lines: list[str] = []
        deadline = time.time() + (max_idle_ms / 1000.0)

        # POSIX: use select() on stdin
        if select is not None and hasattr(select, "select") and os.name == "posix":
            while True:
                now = time.time()
                if now >= deadline:
                    break
                timeout = max(0.0, deadline - now)
                r, _, _ = select.select([sys.stdin], [], [], timeout)
                if not r:
                    break
                try:
                    ln = sys.stdin.readline()
                except Exception:
                    break
                if ln == "":
                    break
                # Remove trailing newline to align with input()
                if ln.endswith("\n"):
                    ln = ln[:-1]
                lines.append(ln)
                # extend deadline slightly while data flows
                deadline = time.time() + (max_idle_ms / 1000.0)
            return lines

        # Windows best-effort: read while keys are available (line-buffered approximation)
        if msvcrt is not None and os.name == "nt":  # pragma: no cover (platform-specific)
            buf = ""
            while time.time() < deadline and msvcrt.kbhit():
                ch = msvcrt.getwche()
                if ch:
                    buf += ch
                else:
                    time.sleep(0.01)
                    continue
                # extend while data flows
                deadline = time.time() + (max_idle_ms / 1000.0)
            # Split any captured buffer into lines
            if buf:
                # Normalize newlines to \n then split
                buf = buf.replace("\r\n", "\n").replace("\r", "\n")
                parts = buf.split("\n")
                # msvcrt read includes the newline characters; align with input() behavior
                if parts and parts[-1] == "":
                    parts.pop()
                return parts
        return lines

    def _clean_paste_text(self, text: str) -> str:
        """Normalize pasted text: strip bracketed paste markers, normalize newlines."""
        if not text:
            return text
        # Remove XTerm bracketed paste markers if present
        text = text.replace("\x1b[200~", "").replace("\x1b[201~", "")
        # Normalize CRLF/CR to LF
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Avoid accidental trailing newlines explosion; keep original internal newlines
        return text
    


async def main():
    assistant = MuonryAssistant()
    if await assistant.setup():
        await assistant.interactive_loop()
    else:
        print(_error("Failed to initialize assistant"))
        
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Quiet exit on Ctrl-C at top-level
        pass
