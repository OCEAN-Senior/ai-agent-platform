from typing import Any

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    agent: str = "simple_chat_agent"
    task: str
    context: dict[str, Any] = Field(default_factory=dict)
