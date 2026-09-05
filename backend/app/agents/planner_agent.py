from backend.app.agents.base import AgentInput, AgentResult, BaseAgent
from backend.app.services.chat_service import get_chat_response

PLANNER_PROMPT = (
    "You are a planning assistant. Break the following task into a short, "
    "numbered list of concrete subtasks needed to complete it. Respond in "
    "the same language as the task. Only output the numbered list, "
    "nothing else.\n\nTask: {task}"
)


class PlannerAgent(BaseAgent):
    name = "planner_agent"

    async def run(self, agent_input: AgentInput) -> AgentResult:
        prompt = PLANNER_PROMPT.format(task=agent_input.task)
        output = await get_chat_response(prompt)
        subtasks = [line.strip() for line in output.splitlines() if line.strip()]
        return AgentResult(output=output, metadata={"subtasks": subtasks})
