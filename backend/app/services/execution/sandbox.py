import asyncio
import uuid
from dataclasses import dataclass

SANDBOX_IMAGE = "python:3.12-slim"
DEFAULT_TIMEOUT_SECONDS = 10


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool


async def run_python_code(code: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> SandboxResult:
    container_name = f"sandbox-{uuid.uuid4().hex[:12]}"
    cmd = [
        "docker", "run", "--rm",
        "--name", container_name,
        "--network", "none",
        "--memory", "128m",
        "--cpus", "0.5",
        "--pids-limit", "64",
        SANDBOX_IMAGE,
        "python3", "-c", code,
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return SandboxResult(
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
            exit_code=process.returncode,
            timed_out=False,
        )
    except asyncio.TimeoutError:
        kill_process = await asyncio.create_subprocess_exec("docker", "kill", container_name)
        await kill_process.wait()
        process.kill()
        return SandboxResult(stdout="", stderr="Execution timed out.", exit_code=None, timed_out=True)
