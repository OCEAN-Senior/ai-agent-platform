from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class AgentInput(BaseModel):
    task: str
    context: dict[str, Any] = Field(default_factory=dict)
    memory: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    output: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    name: str = "base_agent"

    @abstractmethod
    async def run(self, agent_input: AgentInput) -> AgentResult:
        """Execute the agent's task and return a result."""
