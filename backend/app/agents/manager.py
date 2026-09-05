from backend.app.agents.base import AgentInput, AgentResult, BaseAgent
from backend.app.agents.simple_chat_agent import SimpleChatAgent


class AgentNotFoundError(Exception):
    pass


class AgentExecutionError(Exception):
    pass


class AgentManager:
    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {
            "simple_chat_agent": SimpleChatAgent(),
        }

    def get_agent(self, name: str) -> BaseAgent:
        agent = self._agents.get(name)
        if agent is None:
            raise AgentNotFoundError(f"Unknown agent: {name}")
        return agent

    async def run(self, agent_name: str, agent_input: AgentInput) -> AgentResult:
        agent = self.get_agent(agent_name)
        try:
            return await agent.run(agent_input)
        except Exception as exc:
            raise AgentExecutionError(f"Agent '{agent_name}' failed: {exc}") from exc
