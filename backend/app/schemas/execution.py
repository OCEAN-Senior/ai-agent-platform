from pydantic import BaseModel


class ExecuteCodeRequest(BaseModel):
    code: str
    timeout: int = 10


class ExecuteCodeResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
