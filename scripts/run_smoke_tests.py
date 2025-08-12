#!/usr/bin/env python3
import asyncio
import json
import os
import sys
from pathlib import Path
import argparse

try:
    import dotenv  # type: ignore
except Exception:
    dotenv = None

# Allow running from repo root or any cwd
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import tool functions directly (no LLM required)
from tools import toolset  # type: ignore

# Optional: import websearch tool for Exa checks (sync function)
from tools import websearch as websearch_tool  # type: ignore


def load_env():
    """Load .env files from project and ~/.muonry without failing if absent."""
    # Project .env
    if dotenv:
        try:
            dotenv.load_dotenv(REPO_ROOT / ".env", override=False)
        except Exception:
            pass
    # Home ~/.muonry/.env
    home_env = Path.home() / ".muonry/.env"
    if dotenv:
        try:
            dotenv.load_dotenv(home_env, override=False)
        except Exception:
            pass


async def run_case(name: str, coro_fn, *args, validator=None, **kwargs):
    print(f"\n=== {name} ===")
    try:
        out = await coro_fn(*args, **kwargs)
        ok = True
        if validator:
            try:
                ok = bool(validator(out))
            except Exception:
                ok = False
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}")
        # Show compact preview of output
        preview = str(out)
        if len(preview) > 800:
            preview = preview[:800] + "...\n[truncated]"
        print(preview)
        return ok
    except Exception as e:
        print(f"[ERROR] {name}: {e}")
        return False


# Validators

def is_nonempty_string(s: str) -> bool:
    return isinstance(s, str) and len(s.strip()) > 0


def json_has_status(s: str) -> bool:
    try:
        data = json.loads(s)
        return isinstance(data, dict) and "status" in data and "summary" in data
    except Exception:
        return False


def contains(s: str, needle: str) -> bool:
    return needle in s


# --- Vendor checks (optional) ---
async def llm_hello_check(name: str, model: str, api_key: str, base_url: str | None = None) -> dict:
    """Issue a tiny completion via Bhumi to validate an API key.
    Returns the raw response dict.
    """
    # Import locally to keep top-level deps light
    from bhumi.base_client import BaseLLMClient, LLMConfig  # type: ignore

    cfg_kwargs = {"api_key": api_key, "model": model, "debug": False}
    if base_url:
        cfg_kwargs["base_url"] = base_url
    client = BaseLLMClient(LLMConfig(**cfg_kwargs))
    messages = [
        {"role": "system", "content": f"You are a helpful {name} test bot."},
        {"role": "user", "content": "Say 'hello there' and nothing else."},
    ]
    # Cap with a short timeout so CI doesn't hang
    return await asyncio.wait_for(client.completion(messages), timeout=15)


def llm_resp_ok(resp: dict) -> bool:
    try:
        txt = resp.get("text", "")
        return isinstance(txt, str) and len(txt.strip()) > 0
    except Exception:
        return False


async def exa_hello_check(api_key: str) -> str:
    """Call Exa via our websearch tool with a tiny query to validate the key."""
    # websearch_tool.websearch is synchronous; run it in a thread
    return await asyncio.to_thread(
        websearch_tool.websearch,
        "hello there",
        True,  # enabled
        api_key,  # api_key
        False,  # text
        "auto",  # type
    )


def exa_resp_ok(s: str) -> bool:
    try:
        data = json.loads(s)
        return isinstance(data, dict) and "error" not in data and data.get("meta", {}).get("provider") == "exa"
    except Exception:
        return False


async def main():
    load_env()

    parser = argparse.ArgumentParser(description="Muonry smoke tests")
    parser.add_argument("--groq-key", dest="groq_key", default=None, help="Override GROQ_API_KEY for validation")
    parser.add_argument("--cerebras-key", dest="cerebras_key", default=None, help="Override CEREBRAS_API_KEY for validation")
    parser.add_argument("--exa-key", dest="exa_key", default=None, help="Override EXA_API_KEY for validation")
    args = parser.parse_args()

    repo = str(REPO_ROOT)
    navbar = REPO_ROOT / "frontend/src/components/Navbar.tsx"
    py_target = repo  # project root for python scan

    # Build base cases; use smaller limits/timeouts to be safe in CI
    cases = [
        ("system_info", toolset.get_system_info_tool, (), {}, is_nonempty_string),
        ("grep_quick_check_tool", toolset.grep_tool, ("quick_check_tool", str(REPO_ROOT / "tools/toolset.py")), {"recursive": False}, lambda s: contains(s, "quick_check_tool")),
        ("read_pyproject", toolset.read_file_tool, (str(REPO_ROOT / "pyproject.toml"),), {}, lambda s: "[project]" in s),
        ("quick_check_python", toolset.quick_check_tool, ("python", py_target), {"max_files": 50, "timeout_ms": 30000}, json_has_status),
        ("quick_check_js_navbar", toolset.quick_check_tool, ("js", str(navbar if navbar.exists() else REPO_ROOT)), {"max_files": 50, "timeout_ms": 30000}, json_has_status),
    ]

    # Optional vendor checks based on provided or env keys
    groq_key = args.groq_key or os.getenv("GROQ_API_KEY")
    cerebras_key = args.cerebras_key or os.getenv("CEREBRAS_API_KEY")
    exa_key = args.exa_key or os.getenv("EXA_API_KEY")

    if groq_key:
        cases.append(
            (
                "validate_groq_key",
                llm_hello_check,
                ("Groq", "groq/moonshotai/kimi-k2-instruct", groq_key),
                {},
                llm_resp_ok,
            )
        )
    if cerebras_key:
        cases.append(
            (
                "validate_cerebras_key",
                llm_hello_check,
                ("Cerebras", "cerebras/qwen-3-235b-a22b-thinking-2507", cerebras_key),
                {"base_url": "https://api.cerebras.ai/v1"},
                llm_resp_ok,
            )
        )
    if exa_key:
        cases.append(
            (
                "validate_exa_key",
                exa_hello_check,
                (exa_key,),
                {},
                exa_resp_ok,
            )
        )

    # Optional: Smithery MCP over HTTP (requires interactive OAuth on first use)
    smithery_url = os.getenv("SMITHERY_SERVER_URL")
    if smithery_url and sys.stdin.isatty():
        def smithery_validator(s: str) -> bool:
            # Consider PASS if we either got tools JSON or SDK isn't installed (optional extra)
            if not isinstance(s, str):
                return False
            lowered = s.lower()
            return ('"tools"' in s) or ("mcp sdk not installed" in lowered)

        cases.append(
            (
                "smithery_list_tools",
                toolset.smithery_list_tools_tool,
                (smithery_url,),
                {},
                smithery_validator,
            )
        )

    results = []
    for name, fn, args, kwargs, validator in cases:
        ok = await run_case(name, fn, *args, validator=validator, **kwargs)
        results.append(ok)

    passed = sum(1 for x in results if x)
    total = len(results)
    print("\n=== Summary ===")
    print(f"Passed: {passed}/{total}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(main())
