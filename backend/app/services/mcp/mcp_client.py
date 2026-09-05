import asyncio
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SERVER_SCRIPT = str(_REPO_ROOT / "mcp_servers" / "example_server.py")


class MCPToolClient:
    def __init__(self, server_script: str = _SERVER_SCRIPT) -> None:
        self._server_script = server_script
        self._session: ClientSession | None = None
        self._exit_stack = AsyncExitStack()
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        if self._session is not None:
            return
        async with self._lock:
            if self._session is not None:
                return
            params = StdioServerParameters(command="python3", args=[self._server_script])
            read, write = await self._exit_stack.enter_async_context(stdio_client(params))
            self._session = await self._exit_stack.enter_async_context(ClientSession(read, write))
            await self._session.initialize()

    async def list_tools(self) -> list[dict[str, Any]]:
        await self.connect()
        assert self._session is not None
        response = await self._session.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.input_schema,
                },
            }
            for tool in response.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        await self.connect()
        assert self._session is not None
        result = await self._session.call_tool(name, arguments)
        parts = [item.text for item in result.content if hasattr(item, "text")]
        return "\n".join(parts) if parts else str(result.content)

    async def close(self) -> None:
        await self._exit_stack.aclose()
        self._session = None


mcp_tool_client = MCPToolClient()
