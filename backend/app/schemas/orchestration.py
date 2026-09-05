from pydantic import BaseModel


class OrchestrateRequest(BaseModel):
    task: str


class SubtaskResult(BaseModel):
    subtask: str
    agent: str
    output: str


class OrchestrateResponse(BaseModel):
    plan: list[str]
    subtask_results: list[SubtaskResult]
    final_answer: str
