import asyncio
import os
from pathlib import Path
import getpass
import sys

import dotenv


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


def main() -> None:
    """Console entry point for Muonry assistant."""
    _ensure_home_env()
    # Import after env is ensured
    from assistant import main as assistant_main  # type: ignore
    asyncio.run(assistant_main())
