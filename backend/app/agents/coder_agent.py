from backend.app.agents.base import AgentInput, AgentResult, BaseAgent
from backend.app.core.config import settings
from backend.app.services.chat_service import get_chat_response

CODER_PROMPT = (
    "You are an expert software engineer. Write clean, correct code for "
    "the following request. Include a short explanation only if it adds "
    "real value. Task: {task}"
)


class CoderAgent(BaseAgent):
    name = "coder_agent"

    async def run(self, agent_input: AgentInput) -> AgentResult:
        prompt = CODER_PROMPT.format(task=agent_input.task)
        output = await get_chat_response(prompt, model=settings.OLLAMA_CODER_MODEL)
        return AgentResult(output=output, metadata={"model": settings.OLLAMA_CODER_MODEL})
