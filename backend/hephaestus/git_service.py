from __future__ import annotations

import subprocess
from pathlib import Path

from backend.hephaestus.errors import ExecutionFailureError

MAX_COMMIT_MESSAGE_LENGTH = 200


class GitService:
    def __init__(self, project_root: str = ".") -> None:
        self.project_root = Path(project_root).resolve()

    def commit_run(self, *, run_id: str, task_title: str) -> str:
        message = f"[Hephaestus-Auto][{run_id}] {task_title}"[:MAX_COMMIT_MESSAGE_LENGTH]
        self._run(["git", "add", "."])

        status = self._run(["git", "status", "--porcelain"])
        if not status.stdout.strip():
            return ""

        self._run(["git", "commit", "-m", message])
        commit_hash = self._run(["git", "rev-parse", "HEAD"]).stdout.strip()
        return commit_hash

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            command,
            cwd=self.project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise ExecutionFailureError(
                f"Command failed ({' '.join(command)}): {result.stderr.strip() or result.stdout.strip()}"
            )
        return result
