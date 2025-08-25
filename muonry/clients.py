from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from bhumi.base_client import BaseLLMClient  # type: ignore
from bhumi.tools import ToolCall  # type: ignore


class StrictLLMClient(BaseLLMClient):
    """
    Enforces strict tool usage during single (sequential) tool execution.

    Behavior:
    - Appends the assistant message with the original tool_calls (always).
    - If a tool call references an unregistered tool name and strict mode is enabled:
      append a tool message with an error payload and skip execution for that call.
    - Registered tools execute via the underlying ToolRegistry as usual.
    """

    def __init__(self, *args, strict_tools: bool = True, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.strict_tools: bool = bool(strict_tools)

    async def _handle_tool_calls(
        self,
        messages: List[Dict[str, Any]],
        tool_calls: List[Dict[str, Any]],
        debug: bool = False,
    ) -> List[Dict[str, Any]]:
        if debug:
            print("\n[strict] Handling tool calls...")

        # Always append the assistant's message with the tool_calls first (preserve format)
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls,
        })

        # Then handle each tool call
        for tc in tool_calls or []:
            fn = (tc or {}).get("function") or {}
            name = str(fn.get("name") or "")
            tool_call_id = str(tc.get("id") or str(uuid.uuid4()))

            # Check registration
            is_registered = False
            try:
                if hasattr(self, "tool_registry"):
                    is_registered = bool(self.tool_registry.get_tool(name))  # type: ignore[attr-defined]
            except Exception:
                is_registered = False

            if self.strict_tools and not is_registered:
                # Reject and append an error tool message, do not execute
                if debug:
                    print(f"[strict] Rejecting unregistered tool: {name}")
                err_content = json.dumps({
                    "error": "unregistered_tool",
                    "name": name,
                })
                messages.append({
                    "role": "tool",
                    "content": err_content,
                    "tool_call_id": tool_call_id,
                    "name": name,
                })
                continue

            # Execute registered tools via registry
            call = ToolCall(
                id=tool_call_id,
                type=tc.get("type", "function"),
                function=fn,
            )
            try:
                if debug:
                    print(f"[strict] Executing tool: {name}")
                result = await self.tool_registry.execute_tool(call)  # type: ignore[attr-defined]
                tool_message = {
                    "role": "tool",
                    "content": str(result),
                    "tool_call_id": call.id,
                }
                messages.append(tool_message)
            except Exception as e:
                if debug:
                    print(f"[strict] Error executing tool {name}: {e}")
                messages.append({
                    "role": "tool",
                    "content": f"Error: {str(e)}",
                    "tool_call_id": call.id,
                })

        return messages
