import asyncio
import json
import os
from pathlib import Path
import getpass
import sys
from typing import Optional

import dotenv


async def _validate_keys_async(
    groq_key: Optional[str] = None,
    cerebras_key: Optional[str] = None,
    exa_key: Optional[str] = None,
) -> None:
    """Validate provided keys by issuing tiny test requests.
    - Groq/Cerebras via Bhumi BaseLLMClient ("say 'hello there'")
    - Exa via tools.websearch.websearch("hello there")
    Prints concise PASS/FAIL per provider. Never raises.
    """
    async def _llm_ping(name: str, model: str, key: str, base_url: Optional[str] = None) -> bool:
        try:
            from bhumi.base_client import BaseLLMClient, LLMConfig  # type: ignore
            cfg = {"api_key": key, "model": model, "debug": False}
            if base_url:
                cfg["base_url"] = base_url
            client = BaseLLMClient(LLMConfig(**cfg))
            msgs = [
                {"role": "system", "content": f"You are a helpful {name} test bot."},
                {"role": "user", "content": "Say 'hello there' and nothing else."},
            ]
            resp = await asyncio.wait_for(client.completion(msgs), timeout=15)
            return bool(resp and isinstance(resp, dict) and isinstance(resp.get("text"), str) and resp.get("text").strip())
        except Exception:
            return False

    async def _exa_ping(key: str) -> bool:
        try:
            # Import locally to avoid importing exa_py when not needed
            from tools import websearch as websearch_tool  # type: ignore
            s = await asyncio.to_thread(websearch_tool.websearch, "hello there", True, key, False, "auto")
            data = json.loads(s)
            return isinstance(data, dict) and "error" not in data and data.get("meta", {}).get("provider") == "exa"
        except Exception:
            return False

    truthy = {"1", "true", "yes", "on"}

    # Run checks that have keys
    if groq_key:
        ok = await _llm_ping("Groq", "groq/moonshotai/kimi-k2-instruct", groq_key)
        print(f"Groq API key: {'PASS' if ok else 'FAIL'}")
    if cerebras_key:
        ok = await _llm_ping("Cerebras", "cerebras/qwen-3-235b-a22b-thinking-2507", cerebras_key, base_url="https://api.cerebras.ai/v1")
        print(f"Cerebras API key: {'PASS' if ok else 'FAIL'}")
    if exa_key:
        ok = await _exa_ping(exa_key)
        print(f"Exa API key: {'PASS' if ok else 'FAIL'}")


def _ensure_home_env() -> None:
    """Load ~/.muonry/.env and prompt to persist missing keys.

    Required: GROQ_API_KEY
    Optional: CEREBRAS_API_KEY
    """
    home_dir = Path.home() / ".muonry"
    home_env = home_dir / ".env"

    # Ensure directory exists
    try:
        home_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    # Load existing values from ~/.muonry/.env (do not override already-set env)
    try:
        dotenv.load_dotenv(home_env, override=False)
    except Exception:
        pass

    # If still missing, prompt interactively (only if TTY)
    needs_groq = not os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY", "").endswith("REDACTED")
    needs_cerebras = not os.getenv("CEREBRAS_API_KEY") or os.getenv("CEREBRAS_API_KEY", "").endswith("REDACTED")
    needs_exa = not os.getenv("EXA_API_KEY") or os.getenv("EXA_API_KEY", "").endswith("REDACTED")

    entered_groq = None  # type: Optional[str]
    entered_cerebras = None  # type: Optional[str]
    entered_exa = None  # type: Optional[str]

    if needs_groq and sys.stdin.isatty():
        print("GROQ_API_KEY is not set. Enter it to persist under ~/.muonry/.env:")
        print("Get a Groq API key at https://groq.com (sign in → console).")
        try:
            groq = getpass.getpass("GROQ_API_KEY: ").strip()
        except Exception:
            groq = ""
        if groq:
            os.environ["GROQ_API_KEY"] = groq
            try:
                created = not home_env.exists()
                with home_env.open("a", encoding="utf-8") as f:
                    f.write(f"\nGROQ_API_KEY={groq}\n")
                if created:
                    try:
                        home_env.chmod(0o600)
                    except Exception:
                        pass
            except Exception:
                pass
            entered_groq = groq

    # Offer optional CEREBRAS_API_KEY prompt once
    if needs_cerebras and sys.stdin.isatty():
        try:
            print("You can request/learn about access at https://www.cerebras.ai")
            ans = input("Do you want to set CEREBRAS_API_KEY now? [y/N]: ").strip().lower()
        except Exception:
            ans = ""
        if ans in ("y", "yes"):
            try:
                cerebras = getpass.getpass("CEREBRAS_API_KEY: ").strip()
            except Exception:
                cerebras = ""
            if cerebras:
                os.environ["CEREBRAS_API_KEY"] = cerebras
                try:
                    created = not home_env.exists()
                    with home_env.open("a", encoding="utf-8") as f:
                        f.write(f"CEREBRAS_API_KEY={cerebras}\n")
                    if created:
                        try:
                            home_env.chmod(0o600)
                        except Exception:
                            pass
                except Exception:
                    pass
                entered_cerebras = cerebras

    # Offer optional EXA_API_KEY prompt once (websearch), with saved opt-out
    exa_prompt_pref = str(os.getenv("MUONRY_EXA_PROMPT", "")).strip().lower()
    exa_skip_prompt = exa_prompt_pref in {"never", "0", "false", "no", "off"}
    if needs_exa and sys.stdin.isatty() and not exa_skip_prompt:
        try:
            print("You can get an Exa key at https://exa.ai")
            ans = input("Do you want to set EXA_API_KEY now? [y/N]: ").strip().lower()
        except Exception:
            ans = ""
        if ans in ("y", "yes"):
            try:
                exa = getpass.getpass("EXA_API_KEY: ").strip()
            except Exception:
                exa = ""
            if exa:
                os.environ["EXA_API_KEY"] = exa
                try:
                    created = not home_env.exists()
                    with home_env.open("a", encoding="utf-8") as f:
                        f.write(f"EXA_API_KEY={exa}\n")
                    if created:
                        try:
                            home_env.chmod(0o600)
                        except Exception:
                            pass
                except Exception:
                    pass
                entered_exa = exa
        else:
            # Persist opt-out so we don't ask again unless user edits ~/.muonry/.env
            try:
                with home_env.open("a", encoding="utf-8") as f:
                    f.write("MUONRY_EXA_PROMPT=never\n")
                os.environ["MUONRY_EXA_PROMPT"] = "never"
            except Exception:
                pass

    # Validate keys if newly entered, or if MUONRY_VALIDATE_KEYS=1
    try:
        truthy = {"1", "true", "yes", "on"}
        force_validate = str(os.getenv("MUONRY_VALIDATE_KEYS", "")).strip().lower() in truthy
        if force_validate or any([entered_groq, entered_cerebras, entered_exa]):
            print("Validating API keys (tiny test requests)...")
            asyncio.run(
                _validate_keys_async(
                    groq_key=entered_groq or os.getenv("GROQ_API_KEY"),
                    cerebras_key=entered_cerebras or os.getenv("CEREBRAS_API_KEY"),
                    exa_key=entered_exa or os.getenv("EXA_API_KEY"),
                )
            )
    except Exception:
        # Never block startup on validation issues
        pass


def main() -> None:
    """Console entry point for Muonry assistant."""
    _ensure_home_env()
    # Import after env is ensured
    from assistant import main as assistant_main  # type: ignore
    try:
        asyncio.run(assistant_main())
    except KeyboardInterrupt:
        # Quiet exit on Ctrl-C
        pass
    except Exception as e:  # Swallow benign cancellation during shutdown
        try:
            import asyncio as _asyncio
            if isinstance(e, _asyncio.CancelledError):
                return
        except Exception:
            pass
        raise
