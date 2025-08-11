# Lightweight MCP client helpers for Muonry
#
# These helpers connect to an MCP server over stdio and expose minimal
# list-tools and call-tool capabilities. We keep imports optional so the
# rest of Muonry works without MCP installed.
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional


def _not_installed_message() -> str:
    return (
        "MCP SDK not installed. Install optional extra `muonry[mcp]` or run: "
        "pip install \"mcp[cli]\"\n"
        "Docs: https://github.com/modelcontextprotocol/python-sdk"
    )


async def mcp_list_tools(
    server_command: str,
    args: Optional[List[str]] = None,
    env: Optional[Dict[str, str]] = None,
) -> str:
    try:
        from mcp import ClientSession, StdioServerParameters  # type: ignore
        from mcp.client.stdio import stdio_client  # type: ignore
    except Exception:
        return _not_installed_message()

    args = args or []
    server_params = StdioServerParameters(command=server_command, args=args, env=env)

    tools_payload: List[dict] = []
    async with stdio_client(server_params) as (read, write):
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


async def mcp_call_tool(
    server_command: str,
    tool: str,
    arguments: Optional[Dict[str, Any]] = None,
    args: Optional[List[str]] = None,
    env: Optional[Dict[str, str]] = None,
) -> str:
    try:
        from mcp import ClientSession, StdioServerParameters, types  # type: ignore
        from mcp.client.stdio import stdio_client  # type: ignore
    except Exception:
        return _not_installed_message()

    args = args or []
    arguments = arguments or {}
    server_params = StdioServerParameters(command=server_command, args=args, env=env)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments=arguments)

            # Try to extract useful text content
            texts: List[str] = []
            try:
                for block in getattr(result, "content", []) or []:
                    if isinstance(block, types.TextContent):  # type: ignore[attr-defined]
                        texts.append(block.text)
            except Exception:
                pass

            payload = {
                "text": "\n".join(texts) if texts else None,
                "structured": getattr(result, "structuredContent", None),
            }
            # Fall back to model dump if available
            try:
                if not payload["text"] and hasattr(result, "model_dump"):
                    payload["raw"] = result.model_dump()  # type: ignore[attr-defined]
            except Exception:
                pass
    return json.dumps(payload, ensure_ascii=False, default=str)
