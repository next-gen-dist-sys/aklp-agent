from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class CommandExecutionResult:
    """실행된 쉘 명령어의 결과를 표현하는 DTO"""

    command: str
    return_code: int
    stdout: str
    stderr: str


class CommandExecutor:
    """kubectl 과 같은 쉘 명령어를 실제로 실행"""

    async def execute(
        self,
        command: str,
        timeout: int = 30,
    ) -> CommandExecutionResult:
        """주어진 쉘 명령어를 비동기로 실행

        Args:
            command: 실행할 쉘 명령어 문자열 (예: 'kubectl get pods -A')
            timeout: 명령어 실행 타임아웃 (초)

        Returns:
            CommandExecutionResult: 실행 결과 DTO
        """
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except TimeoutError:
            process.kill()
            raise

        stdout = stdout_bytes.decode().strip()
        stderr = stderr_bytes.decode().strip()

        return_code = process.returncode if process.returncode is not None else -1

        return CommandExecutionResult(
            command=command,
            return_code=return_code,
            stdout=stdout,
            stderr=stderr,
        )
