import logging

from backend.app.agents.base import AgentInput, AgentResult, BaseAgent
from backend.app.services.llm.factory import get_llm_provider
from backend.app.services.mcp.mcp_client import mcp_tool_client
from backend.app.services.tools.registry import TOOL_REGISTRY

logger = logging.getLogger("ai_agent_platform.tool_agent")

MAX_TOOL_ITERATIONS = 3


class ToolAgent(BaseAgent):
    name = "tool_agent"

    async def run(self, agent_input: AgentInput) -> AgentResult:
        provider = get_llm_provider()
        local_schemas = [tool.to_ollama_schema() for tool in TOOL_REGISTRY.values()]
        try:
            mcp_schemas = await mcp_tool_client.list_tools()
        except Exception:
            logger.warning("MCP server unavailable, continuing with local tools only", exc_info=True)
            mcp_schemas = []
        mcp_tool_names = {schema["function"]["name"] for schema in mcp_schemas}
        tool_schemas = local_schemas + mcp_schemas

        messages: list[dict] = [{"role": "user", "content": agent_input.task}]
        tools_used: list[str] = []

        for _ in range(MAX_TOOL_ITERATIONS):
            message = await provider.chat_with_tools(messages, tool_schemas)
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                return AgentResult(
                    output=message.get("content", ""),
                    metadata={"tools_used": tools_used},
                )

            messages.append(message)
            for call in tool_calls:
                fn_name = call["function"]["name"]
                fn_args = call["function"].get("arguments") or {}
                logger.info("tool_call=%s args=%s", fn_name, fn_args)
                if fn_name in mcp_tool_names:
                    result = await mcp_tool_client.call_tool(fn_name, fn_args)
                else:
                    tool = TOOL_REGISTRY.get(fn_name)
                    result = tool.func(**fn_args) if tool else f"Error: unknown tool '{fn_name}'"
                tools_used.append(fn_name)
                messages.append({"role": "tool", "content": str(result), "name": fn_name})

        logger.warning("tool_agent reached max iterations (%d)", MAX_TOOL_ITERATIONS)
        final_message = await provider.chat_with_tools(messages, [])
        return AgentResult(
            output=final_message.get("content", ""),
            metadata={"tools_used": tools_used, "note": "max_iterations_reached"},
        )
