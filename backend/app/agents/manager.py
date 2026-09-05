import logging

from backend.app.agents.base import AgentInput, AgentResult, BaseAgent
from backend.app.agents.coder_agent import CoderAgent
from backend.app.agents.planner_agent import PlannerAgent
from backend.app.agents.research_agent import ResearchAgent
from backend.app.agents.simple_chat_agent import SimpleChatAgent
from backend.app.agents.tool_agent import ToolAgent

logger = logging.getLogger("ai_agent_platform.agent_manager")


class AgentNotFoundError(Exception):
    pass


class AgentExecutionError(Exception):
    pass


class AgentManager:
    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {
            "simple_chat_agent": SimpleChatAgent(),
            "planner_agent": PlannerAgent(),
            "research_agent": ResearchAgent(),
            "coder_agent": CoderAgent(),
            "tool_agent": ToolAgent(),
        }

    def get_agent(self, name: str) -> BaseAgent:
        agent = self._agents.get(name)
        if agent is None:
            raise AgentNotFoundError(f"Unknown agent: {name}")
        return agent

    async def run(self, agent_name: str, agent_input: AgentInput) -> AgentResult:
        agent = self.get_agent(agent_name)
        logger.info("agent=%s starting task_len=%d", agent_name, len(agent_input.task))
        try:
            result = await agent.run(agent_input)
        except Exception as exc:
            logger.exception("agent=%s failed", agent_name)
            raise AgentExecutionError(f"Agent '{agent_name}' failed: {exc}") from exc
        logger.info("agent=%s completed output_len=%d", agent_name, len(result.output))
        return result
