from __future__ import annotations

"""
Thin shim to expose the top-level `assistant.py` module under the package path
`muonry.assistant` for test imports and external consumers.

This keeps CLI behavior intact (which imports `assistant` directly) while
allowing `from muonry.assistant import MuonryAssistant`.
"""

try:
    # Re-export the class used by tests
    from assistant import MuonryAssistant  # type: ignore
except Exception as e:  # pragma: no cover - only hit in broken environments
    raise ImportError(
        "muonry.assistant shim could not import top-level 'assistant' module"
    ) from e
