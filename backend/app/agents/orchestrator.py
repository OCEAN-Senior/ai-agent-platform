from backend.app.agents.base import AgentInput
from backend.app.agents.manager import AgentManager
from backend.app.schemas.orchestration import OrchestrateResponse, SubtaskResult
from backend.app.services.chat_service import get_chat_response

CODER_KEYWORDS = (
    "code", "function", "script", "class", "api",
    "dastur", "kod", "funksiya", "sinf", "veb-sayt", "sayt",
)

MAX_SUBTASKS = 5

SYNTHESIS_PROMPT = (
    "You are combining results from multiple subtasks into one final answer "
    "for the original task. Respond in the same language as the task.\n\n"
    "Original task: {task}\n\n"
    "Subtask results:\n{subtask_results}\n\n"
    "Write a single, coherent final answer."
)


class MultiAgentOrchestrator:
    def __init__(self, agent_manager: AgentManager) -> None:
        self._agent_manager = agent_manager

    def _choose_agent(self, subtask: str) -> str:
        lowered = subtask.lower()
        if any(keyword in lowered for keyword in CODER_KEYWORDS):
            return "coder_agent"
        return "research_agent"

    async def run(self, task: str) -> OrchestrateResponse:
        plan_result = await self._agent_manager.run("planner_agent", AgentInput(task=task))
        subtasks = plan_result.metadata.get("subtasks") or [plan_result.output]
        subtasks = subtasks[:MAX_SUBTASKS]

        subtask_results: list[SubtaskResult] = []
        for subtask in subtasks:
            agent_name = self._choose_agent(subtask)
            result = await self._agent_manager.run(agent_name, AgentInput(task=subtask))
            subtask_results.append(
                SubtaskResult(subtask=subtask, agent=agent_name, output=result.output)
            )

        combined = "\n".join(
            f"- ({r.agent}) {r.subtask}: {r.output}" for r in subtask_results
        )
        final_answer = await get_chat_response(
            SYNTHESIS_PROMPT.format(task=task, subtask_results=combined)
        )

        return OrchestrateResponse(
            plan=subtasks,
            subtask_results=subtask_results,
            final_answer=final_answer,
        )
