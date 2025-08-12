# Optional Smithery MCP HTTP client with OAuth auth
#
# Provides convenience functions to connect to Smithery-hosted MCP servers
# using the MCP Python SDK's Streamable HTTP transport. OAuth tokens are
# persisted to ~/.muonry to enable non-interactive reuse after first login.
from __future__ import annotations

import json
import os
import sys
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _not_installed_message() -> str:
    return (
        "MCP SDK not installed. Install optional extra `muonry[mcp]` or run: "
        "pip install \"mcp[cli]\"\n"
        "Docs: https://github.com/modelcontextprotocol/python-sdk\n"
        "Smithery: https://smithery.ai/docs/use/connect"
    )


def _smithery_home() -> Path:
    return Path.home() / ".muonry"


def _tokens_path() -> Path:
    return _smithery_home() / "smithery_tokens.json"


def _client_info_path() -> Path:
    return _smithery_home() / "smithery_client.json"


def _ensure_home_dir() -> None:
    try:
        _smithery_home().mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _strip_mcp_suffix(url: str) -> str:
    return url[:-4] if url.endswith("/mcp") else url


async def smithery_list_tools_http(server_url: str) -> str:
    """List tools from a Smithery MCP server over Streamable HTTP.

    server_url: Full MCP URL, e.g. https://server.smithery.ai/exa/mcp
    Returns JSON string: {"tools": [{name, description, inputSchema} ...]}
    """
    try:
        from pydantic import AnyUrl  # type: ignore
        from mcp import ClientSession  # type: ignore
        from mcp.client.streamable_http import streamablehttp_client  # type: ignore
        from mcp.client.auth import OAuthClientProvider, TokenStorage  # type: ignore
        from mcp.shared.auth import (
            OAuthClientInformationFull,
            OAuthClientMetadata,
            OAuthToken,
        )  # type: ignore
    except Exception:
        return _not_installed_message()

    # Local token storage persisted under ~/.muonry/
    class FileTokenStorage(TokenStorage):  # type: ignore[misc]
        def __init__(self, scope_key: str):
            _ensure_home_dir()
            self.scope_key = scope_key  # per-server key

        async def get_tokens(self) -> OAuthToken | None:  # type: ignore[name-defined]
            try:
                p = _tokens_path()
                if not p.exists():
                    return None
                data = json.loads(p.read_text(encoding="utf-8"))
                entry = (data or {}).get(self.scope_key)
                if not entry:
                    return None
                return OAuthToken(**entry)  # type: ignore[name-defined]
            except Exception:
                return None

        async def set_tokens(self, tokens: OAuthToken) -> None:  # type: ignore[name-defined]
            try:
                p = _tokens_path()
                db = {}
                if p.exists():
                    try:
                        db = json.loads(p.read_text(encoding="utf-8"))
                    except Exception:
                        db = {}
                db[self.scope_key] = tokens.model_dump()
                p.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
                try:
                    p.chmod(0o600)
                except Exception:
                    pass
            except Exception:
                pass

        async def get_client_info(self) -> OAuthClientInformationFull | None:  # type: ignore[name-defined]
            try:
                p = _client_info_path()
                if not p.exists():
                    return None
                data = json.loads(p.read_text(encoding="utf-8"))
                return OAuthClientInformationFull(**data)  # type: ignore[name-defined]
            except Exception:
                return None

        async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:  # type: ignore[name-defined]
            try:
                p = _client_info_path()
                p.write_text(json.dumps(client_info.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
                try:
                    p.chmod(0o600)
                except Exception:
                    pass
            except Exception:
                pass

    # Interactive handlers for OAuth (CLI)
    async def handle_redirect(auth_url: str) -> None:
        print(f"Visit to authorize Smithery: {auth_url}")
        try:
            if os.getenv("MUONRY_OPEN_BROWSER", "1") not in {"0", "false", "no"}:
                webbrowser.open(auth_url)
        except Exception:
            pass

    async def handle_callback() -> Tuple[str, Optional[str]]:
        try:
            callback_url = input("Paste the callback URL after authorization: ").strip()
        except Exception:
            callback_url = ""
        from urllib.parse import parse_qs, urlparse
        params = parse_qs(urlparse(callback_url).query)
        code = params.get("code", [""])[0]
        state = params.get("state", [None])[0]
        return code, state

    base_url = _strip_mcp_suffix(server_url)

    client_name = os.getenv("SMITHERY_CLIENT_NAME", "Muonry CLI")
    redirect_uri = os.getenv("SMITHERY_REDIRECT_URI", "http://localhost:3000/callback")
    scope = os.getenv("SMITHERY_SCOPE", "user")

    storage = FileTokenStorage(scope_key=base_url)
    oauth_auth = OAuthClientProvider(  # type: ignore[call-arg]
        server_url=base_url,
        client_metadata=OAuthClientMetadata(  # type: ignore[call-arg]
            client_name=client_name,
            redirect_uris=[AnyUrl(redirect_uri)],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            scope=scope,
        ),
        storage=storage,
        redirect_handler=handle_redirect,
        callback_handler=handle_callback,
    )

    tools_payload: List[dict] = []
    async with streamablehttp_client(server_url, auth=oauth_auth) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            for t in tools.tools:
                tools_payload.append(
                    {
                        "name": getattr(t, "name", ""),
                        "description": getattr(t, "description", ""),
                        "inputSchema": getattr(t, "inputSchema", None),
                    }
                )
    return json.dumps({"tools": tools_payload}, ensure_ascii=False)


async def smithery_call_tool_http(
    server_url: str,
    tool: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> str:
    """Call a tool on a Smithery MCP server over Streamable HTTP.

    Returns JSON string with keys: text, structured, raw (optional)
    """
    try:
        from pydantic import AnyUrl  # type: ignore
        from mcp import ClientSession, types  # type: ignore
        from mcp.client.streamable_http import streamablehttp_client  # type: ignore
        from mcp.client.auth import OAuthClientProvider, TokenStorage  # type: ignore
        from mcp.shared.auth import (
            OAuthClientInformationFull,
            OAuthClientMetadata,
            OAuthToken,
        )  # type: ignore
    except Exception:
        return _not_installed_message()

    # Reuse same helpers
    class FileTokenStorage(TokenStorage):  # type: ignore[misc]
        def __init__(self, scope_key: str):
            _ensure_home_dir()
            self.scope_key = scope_key

        async def get_tokens(self):
            try:
                p = _tokens_path()
                if not p.exists():
                    return None
                data = json.loads(p.read_text(encoding="utf-8"))
                entry = (data or {}).get(self.scope_key)
                if not entry:
                    return None
                from mcp.shared.auth import OAuthToken  # type: ignore
                return OAuthToken(**entry)
            except Exception:
                return None

        async def set_tokens(self, tokens):
            try:
                p = _tokens_path()
                db = {}
                if p.exists():
                    try:
                        db = json.loads(p.read_text(encoding="utf-8"))
                    except Exception:
                        db = {}
                db[self.scope_key] = tokens.model_dump()
                p.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
                try:
                    p.chmod(0o600)
                except Exception:
                    pass
            except Exception:
                pass

        async def get_client_info(self):
            try:
                p = _client_info_path()
                if not p.exists():
                    return None
                from mcp.shared.auth import OAuthClientInformationFull  # type: ignore
                data = json.loads(p.read_text(encoding="utf-8"))
                return OAuthClientInformationFull(**data)
            except Exception:
                return None

        async def set_client_info(self, client_info):
            try:
                p = _client_info_path()
                p.write_text(json.dumps(client_info.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
                try:
                    p.chmod(0o600)
                except Exception:
                    pass
            except Exception:
                pass

    async def handle_redirect(auth_url: str) -> None:
        print(f"Visit to authorize Smithery: {auth_url}")
        try:
            if os.getenv("MUONRY_OPEN_BROWSER", "1") not in {"0", "false", "no"}:
                webbrowser.open(auth_url)
        except Exception:
            pass

    async def handle_callback() -> Tuple[str, Optional[str]]:
        try:
            callback_url = input("Paste the callback URL after authorization: ").strip()
        except Exception:
            callback_url = ""
        from urllib.parse import parse_qs, urlparse
        params = parse_qs(urlparse(callback_url).query)
        code = params.get("code", [""])[0]
        state = params.get("state", [None])[0]
        return code, state

    base_url = _strip_mcp_suffix(server_url)

    client_name = os.getenv("SMITHERY_CLIENT_NAME", "Muonry CLI")
    redirect_uri = os.getenv("SMITHERY_REDIRECT_URI", "http://localhost:3000/callback")
    scope = os.getenv("SMITHERY_SCOPE", "user")

    storage = FileTokenStorage(scope_key=base_url)
    from mcp.shared.auth import OAuthClientMetadata  # type: ignore
    from pydantic import AnyUrl  # type: ignore
    oauth_auth = OAuthClientProvider(  # type: ignore[call-arg]
        server_url=base_url,
        client_metadata=OAuthClientMetadata(  # type: ignore[call-arg]
            client_name=client_name,
            redirect_uris=[AnyUrl(redirect_uri)],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            scope=scope,
        ),
        storage=storage,
        redirect_handler=handle_redirect,
        callback_handler=handle_callback,
    )

    arguments = arguments or {}
    async with streamablehttp_client(server_url, auth=oauth_auth) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments=arguments)

            texts: List[str] = []
            try:
                for block in getattr(result, "content", []) or []:
                    from mcp import types  # type: ignore
                    if isinstance(block, types.TextContent):  # type: ignore[attr-defined]
                        texts.append(block.text)
            except Exception:
                pass

            payload = {
                "text": "\n".join(texts) if texts else None,
                "structured": getattr(result, "structuredContent", None),
            }
            try:
                if not payload["text"] and hasattr(result, "model_dump"):
                    payload["raw"] = result.model_dump()  # type: ignore[attr-defined]
            except Exception:
                pass
    return json.dumps(payload, ensure_ascii=False, default=str)
