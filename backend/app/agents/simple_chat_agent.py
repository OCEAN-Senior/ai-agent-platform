from backend.app.agents.base import AgentInput, AgentResult, BaseAgent
from backend.app.services.chat_service import get_chat_response


class SimpleChatAgent(BaseAgent):
    name = "simple_chat_agent"

    async def run(self, agent_input: AgentInput) -> AgentResult:
        output = await get_chat_response(agent_input.task)
        return AgentResult(output=output)
