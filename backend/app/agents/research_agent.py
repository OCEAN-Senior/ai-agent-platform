from backend.app.agents.base import AgentInput, AgentResult, BaseAgent
from backend.app.services.chat_service import get_chat_response

RESEARCH_PROMPT = (
    "You are a research assistant. Answer the following question with the "
    "most accurate, well-structured information you have. If you are not "
    "certain about a fact, say so explicitly instead of guessing. Respond "
    "in the same language as the question.\n\nQuestion: {task}"
)


class ResearchAgent(BaseAgent):
    name = "research_agent"

    async def run(self, agent_input: AgentInput) -> AgentResult:
        prompt = RESEARCH_PROMPT.format(task=agent_input.task)
        output = await get_chat_response(prompt)
        return AgentResult(
            output=output,
            metadata={"source": "llm_knowledge_only"},
        )
