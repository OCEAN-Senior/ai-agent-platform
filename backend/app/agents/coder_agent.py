import re

from backend.app.agents.base import AgentInput, AgentResult, BaseAgent
from backend.app.core.config import settings
from backend.app.services.chat_service import get_chat_response
from backend.app.services.execution.sandbox import run_python_code

CODER_PROMPT = (
    "You are an expert software engineer. Write clean, correct code for "
    "the following request. Include a short explanation only if it adds "
    "real value. Task: {task}"
)

_CODE_BLOCK_RE = re.compile(r"```(?:python)?\n(.*?)```", re.DOTALL)


def _extract_python_code_block(text: str) -> str | None:
    match = _CODE_BLOCK_RE.search(text)
    return match.group(1).strip() if match else None


class CoderAgent(BaseAgent):
    name = "coder_agent"

    async def run(self, agent_input: AgentInput) -> AgentResult:
        prompt = CODER_PROMPT.format(task=agent_input.task)
        output = await get_chat_response(prompt, model=settings.OLLAMA_CODER_MODEL)
        metadata: dict = {"model": settings.OLLAMA_CODER_MODEL}

        code_block = _extract_python_code_block(output)
        if code_block:
            try:
                result = await run_python_code(code_block)
                metadata["execution"] = {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.exit_code,
                    "timed_out": result.timed_out,
                }
            except Exception as exc:
                metadata["execution_error"] = str(exc)

        return AgentResult(output=output, metadata=metadata)
