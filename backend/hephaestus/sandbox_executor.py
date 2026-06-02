from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CommandResult:
    command: str
    return_code: int
    stdout: str
    stderr: str
    timed_out: bool

    @property
    def success(self) -> bool:
        return self.return_code == 0 and not self.timed_out


class SandboxExecutor:
    def __init__(self, *, timeout_seconds: int = 60) -> None:
        self.timeout_seconds = timeout_seconds

    async def execute(self, command: str, *, working_dir: str) -> CommandResult:
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=working_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout_seconds
            )
            return CommandResult(
                command=command,
                return_code=process.returncode or 0,
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                timed_out=False,
            )
        except TimeoutError:
            process.kill()
            stdout_bytes, stderr_bytes = await process.communicate()
            return CommandResult(
                command=command,
                return_code=process.returncode or -1,
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                timed_out=True,
            )

    async def execute_and_archive(
        self,
        command: str,
        *,
        working_dir: str,
        artifact_dir: str,
        artifact_prefix: str,
    ) -> CommandResult:
        result = await self.execute(command, working_dir=working_dir)
        target_dir = Path(artifact_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / f"{artifact_prefix}_stdout.log").write_text(result.stdout, encoding="utf-8")
        (target_dir / f"{artifact_prefix}_stderr.log").write_text(result.stderr, encoding="utf-8")
        return result
