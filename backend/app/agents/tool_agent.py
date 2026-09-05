from backend.app.agents.base import AgentInput, AgentResult, BaseAgent
from backend.app.services.llm.factory import get_llm_provider
from backend.app.services.tools.registry import TOOL_REGISTRY

MAX_TOOL_ITERATIONS = 3


class ToolAgent(BaseAgent):
    name = "tool_agent"

    async def run(self, agent_input: AgentInput) -> AgentResult:
        provider = get_llm_provider()
        tool_schemas = [tool.to_ollama_schema() for tool in TOOL_REGISTRY.values()]
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
                tool = TOOL_REGISTRY.get(fn_name)
                result = tool.func(**fn_args) if tool else f"Error: unknown tool '{fn_name}'"
                tools_used.append(fn_name)
                messages.append({"role": "tool", "content": str(result), "name": fn_name})

        final_message = await provider.chat_with_tools(messages, [])
        return AgentResult(
            output=final_message.get("content", ""),
            metadata={"tools_used": tools_used, "note": "max_iterations_reached"},
        )
