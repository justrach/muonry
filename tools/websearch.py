"""
Web search tool using Exa (exa_py).

Provides a callable `websearch` that can be registered as a tool by the
assistant. The search is off by default and requires an API key when enabled.

Usage parameters:
- query (str): the search query (required)
- enabled (bool): must be True to execute the search (default False)
- api_key (str|None): optional key; falls back to EXA_API_KEY env var
- text (bool): include text contents (default True)
- type (str): Exa search type (default "auto")

Debugging
- Set env var `MUONRY_WEBSEARCH_DEBUG=1` to include a `debug` section in the output (no secrets).

Output shape (JSON string on success):
{
  "query": str,
  "meta": {
    "request_id": str|None,
    "search_type": str|None,
    "autoprompt": str|None,
    "provider": "exa"
  },
  "results": [
    {
      "title": str,
      "url": str,
      "published_date": str|None,
      "author": str|None,
      "image": str|None,
      "snippet": str,       # cleaned, short preview
      "text": str|None      # possibly truncated full text
    },
    ...
  ],
  "count": int
}
"""

from __future__ import annotations

import json
import os
from typing import Optional, Any, Dict
import dotenv

dotenv.load_dotenv()


def _to_plain(obj: Any) -> Any:
    """Best-effort conversion of SDK objects to plain Python types."""
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, list):
        return [_to_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_plain(v) for k, v in obj.items()}
    # Try common conversion hooks
    for attr in ("model_dump", "dict", "to_dict"):
        fn = getattr(obj, attr, None)
        if callable(fn):
            try:
                return _to_plain(fn())
            except Exception:
                pass
    # Fallback via JSON round-trip
    try:
        return json.loads(json.dumps(obj, default=str))
    except Exception:
        try:
            return obj.__dict__
        except Exception:
            return str(obj)


def _clean_snippet(text: Optional[str], limit: int = 400) -> Optional[str]:
    """Create a compact, readable snippet from raw text/markdown."""
    if not text:
        return None
    try:
        import re
        # Strip markdown images: ![alt](url)
        text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        # Remove repeated social footer noise (best-effort heuristic)
        text = re.sub(r"(?i)(privacy policy|terms|cookies|subscribe|newsletter).*", "", text)
    except Exception:
        # If cleaning fails, return raw truncated text
        text = text.strip()
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def _structure_exa_payload(query: str, payload: Any) -> dict:
    """Normalize Exa search payload into a compact, consistent structure."""
    data = payload.get("data") if isinstance(payload, dict) else None
    core = data if isinstance(data, dict) else (payload if isinstance(payload, dict) else {})

    request_id = core.get("requestId") or core.get("request_id")
    search_type = core.get("resolvedSearchType") or core.get("type")
    autoprompt = core.get("autopromptString") or core.get("autoprompt")

    raw_results = core.get("results") or core.get("documents") or []
    out_results = []
    for item in (raw_results or []):
        if not isinstance(item, dict):
            try:
                item = _to_plain(item)
            except Exception:
                item = {"_raw": str(item)}

        title = item.get("title") or item.get("id") or "Untitled"
        url = item.get("url") or item.get("link") or item.get("id") or ""
        published = item.get("publishedDate") or item.get("published_at") or item.get("date")
        author = item.get("author") or item.get("by")
        image = item.get("image") or item.get("thumbnail")
        text = item.get("text") or item.get("snippet") or item.get("content")

        out_results.append(
            {
                "title": title,
                "url": url,
                "published_date": published,
                "author": author,
                "image": image,
                "snippet": _clean_snippet(text),
                # keep a reasonably sized text; callers can page for more
                "text": (text[:2000] + "…") if isinstance(text, str) and len(text) > 2000 else text,
            }
        )

    return {
        "query": query,
        "meta": {
            "request_id": request_id,
            "search_type": search_type,
            "autoprompt": autoprompt,
            "provider": "exa",
        },
        "results": out_results,
        "count": len(out_results),
    }


def _parse_text_block_results(text: str, query: str) -> dict:
    """Parse stringified Exa output that includes 'Title:' and 'URL:' lines.
    Returns a structured payload consistent with _structure_exa_payload.
    """
    import re
    titles = re.findall(r"^Title:\s*(.+)$", text, flags=re.MULTILINE)
    urls = re.findall(r"^URL:\s*(https?://\S+)$", text, flags=re.MULTILINE)
    results = []
    for i, url in enumerate(urls):
        title = titles[i] if i < len(titles) else "Untitled"
        results.append({
            "title": title,
            "url": url,
            "published_date": None,
            "author": None,
            "image": None,
            "snippet": None,
            "text": None,
        })
    return {
        "query": query,
        "meta": {
            "request_id": None,
            "search_type": None,
            "autoprompt": None,
            "provider": "exa",
        },
        "results": results,
        "count": len(results),
    }


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def _wrap_json(payload: Dict[str, Any], debug_info: Optional[Dict[str, Any]] = None) -> str:
    if debug_info:
        payload = {**payload, "debug": debug_info}
    return json.dumps(payload, ensure_ascii=False)

def websearch(
    query: str,
    enabled: bool = True,
    api_key: Optional[str] = None,
    text: bool = True,
    type: str = "auto",
) -> str:
    """Search the web using Exa's Python SDK (exa_py).

    Off by default. To run the search, set enabled=True and provide an API key
    via the `api_key` parameter or the `EXA_API_KEY` environment variable.
    Returns a JSON string on success, or a human-readable error string.
    """

    dbg = _env_bool("MUONRY_WEBSEARCH_DEBUG", False)
    debug_info: Dict[str, Any] = {
        "enabled": enabled,
        "query_len": len(query or ""),
        "uses_env_key": api_key is None,
        "env_key_present": bool(os.getenv("EXA_API_KEY")),
        "params": {"text": text, "type": type},
        "import": "pending",
        "request": "pending",
    }

    if not enabled:
        return _wrap_json({
            "error": (
                "websearch disabled. Set enabled=true to run. "
                "Ensure EXA_API_KEY is set or pass api_key."
            )
        }, debug_info if dbg else None)

    key = api_key or os.getenv("EXA_API_KEY")
    if not key:
        debug_info["import"] = "skipped"
        return _wrap_json({
            "error": "Missing EXA API key. Set EXA_API_KEY env var or pass api_key."
        }, debug_info if dbg else None)

    try:
        from exa_py import Exa  # type: ignore
    except Exception as ie:
        debug_info["import"] = "failed"
        return _wrap_json({
            "error": (
                "exa_py not installed. Install the optional extra with "
                "`pip install 'muonry[websearch]'` or install exa_py directly "
                "with `pip install exa_py`."
            ),
            "detail": str(ie)
        }, debug_info if dbg else None)

    try:
        exa = Exa(api_key=key)
        debug_info["import"] = "ok"
        result = exa.search_and_contents(query, text=text, type=type)
        debug_info["request"] = "ok"
    except Exception as se:
        debug_info["request"] = "failed"
        return _wrap_json({
            "error": "Error calling Exa",
            "detail": str(se)
        }, debug_info if dbg else None)

    # Normalize to structured JSON
    try:
        plain = _to_plain(result)
        if isinstance(plain, dict):
            structured = _structure_exa_payload(query, plain)
        elif isinstance(plain, str):
            # Fallback: parse stringified output for Title/URL blocks
            structured = _parse_text_block_results(plain, query)
        else:
            structured = _structure_exa_payload(query, {"data": plain})
        # Add minimal debug shape info if requested
        if dbg:
            debug_info["response_keys"] = list((plain or {}).keys()) if isinstance(plain, dict) else type(plain).__name__
            debug_info["result_count"] = structured.get("count")
        return _wrap_json(structured, debug_info if dbg else None)
    except Exception as e:
        # Fallback to a best-effort dump
        if dbg:
            debug_info["normalize_error"] = str(e)
        try:
            return _wrap_json(_to_plain(result), debug_info if dbg else None)
        except Exception:
            return _wrap_json({"raw": str(result)}, debug_info if dbg else None)
