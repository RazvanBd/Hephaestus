from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from backend.hephaestus.errors import NotFoundError
from backend.hephaestus.models import RunRecord, RunStatus, TaskRecord, TaskStatus, utc_now


class HephaestusStore:
    def __init__(self, project_root: str = ".") -> None:
        self.project_root = Path(project_root).resolve()
        self.base_dir = self.project_root / ".session" / "hephaestus"
        self.runs_dir = self.base_dir / "runs"
        self.tasks_file = self.base_dir / "tasks.json"
        self.runs_file = self.base_dir / "runs.json"
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        if not self.tasks_file.exists():
            self.tasks_file.write_text("[]", encoding="utf-8")
        if not self.runs_file.exists():
            self.runs_file.write_text("[]", encoding="utf-8")

    def run_root(self, run_id: str) -> Path:
        return self.runs_dir / run_id

    def run_workspace(self, run_id: str) -> Path:
        return self.run_root(run_id) / "workspace"

    def run_events_file(self, run_id: str) -> Path:
        return self.run_root(run_id) / "events.jsonl"

    def run_artifacts_dir(self, run_id: str) -> Path:
        return self.run_root(run_id) / "artifacts"

    async def create_task(self, title: str, description: str) -> TaskRecord:
        task = TaskRecord.create(title=title, description=description)
        async with self._lock:
            tasks = await self._read_tasks()
            tasks.append(task)
            await self._write_tasks(tasks)
        return task

    async def list_tasks(self) -> list[TaskRecord]:
        async with self._lock:
            return await self._read_tasks()

    async def get_task(self, task_id: str) -> TaskRecord:
        async with self._lock:
            tasks = await self._read_tasks()
        for task in tasks:
            if task.id == task_id:
                return task
        raise NotFoundError(f"Unknown task: {task_id}")

    async def save_task(self, task: TaskRecord) -> TaskRecord:
        task.updated_at = utc_now()
        async with self._lock:
            tasks = await self._read_tasks()
            updated = False
            for index, item in enumerate(tasks):
                if item.id == task.id:
                    tasks[index] = task
                    updated = True
                    break
            if not updated:
                tasks.append(task)
            await self._write_tasks(tasks)
        return task

    async def create_run(self, task_id: str, max_steps: int = 8) -> RunRecord:
        run = RunRecord.create(
            task_id=task_id,
            workspace_root=str(self.run_workspace("pending")),
            max_steps=max_steps,
        )
        run.workspace_root = str(self.run_workspace(run.id))

        run_dir = self.run_root(run.id)
        workspace = self.run_workspace(run.id)
        artifacts = self.run_artifacts_dir(run.id)
        run_dir.mkdir(parents=True, exist_ok=True)
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "src").mkdir(parents=True, exist_ok=True)
        (workspace / "docs").mkdir(parents=True, exist_ok=True)
        artifacts.mkdir(parents=True, exist_ok=True)

        async with self._lock:
            runs = await self._read_runs()
            runs.append(run)
            await self._write_runs(runs)
        return run

    async def list_runs(self) -> list[RunRecord]:
        async with self._lock:
            return await self._read_runs()

    async def get_run(self, run_id: str) -> RunRecord:
        async with self._lock:
            runs = await self._read_runs()
        for run in runs:
            if run.id == run_id:
                return run
        raise NotFoundError(f"Unknown run: {run_id}")

    async def save_run(self, run: RunRecord) -> RunRecord:
        run.updated_at = utc_now()
        async with self._lock:
            runs = await self._read_runs()
            updated = False
            for index, item in enumerate(runs):
                if item.id == run.id:
                    runs[index] = run
                    updated = True
                    break
            if not updated:
                runs.append(run)
            await self._write_runs(runs)
        return run

    async def append_event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> None:
        run_event_file = self.run_events_file(run_id)
        run_event_file.parent.mkdir(parents=True, exist_ok=True)
        with run_event_file.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {"timestamp": utc_now(), "event_type": event_type, "payload": payload},
                    ensure_ascii=False,
                )
                + "\n"
            )

    async def read_events(self, run_id: str) -> list[dict[str, Any]]:
        run_event_file = self.run_events_file(run_id)
        if not run_event_file.exists():
            return []
        lines = run_event_file.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    async def add_artifact(self, run_id: str, name: str, content: str) -> str:
        artifact_file = self.run_artifacts_dir(run_id) / name
        artifact_file.parent.mkdir(parents=True, exist_ok=True)
        artifact_file.write_text(content, encoding="utf-8")
        return str(artifact_file)

    async def list_artifacts(self, run_id: str) -> list[str]:
        artifacts_dir = self.run_artifacts_dir(run_id)
        if not artifacts_dir.exists():
            return []
        return sorted(str(path) for path in artifacts_dir.rglob("*") if path.is_file())

    async def set_run_status(self, run_id: str, status: RunStatus) -> RunRecord:
        run = await self.get_run(run_id)
        run.status = status
        return await self.save_run(run)

    async def set_task_status(self, task_id: str, status: TaskStatus) -> TaskRecord:
        task = await self.get_task(task_id)
        task.status = status
        return await self.save_task(task)

    async def _read_tasks(self) -> list[TaskRecord]:
        data = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        return [TaskRecord.from_dict(item) for item in data]

    async def _write_tasks(self, tasks: list[TaskRecord]) -> None:
        payload = [task.to_dict() for task in tasks]
        self.tasks_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    async def _read_runs(self) -> list[RunRecord]:
        data = json.loads(self.runs_file.read_text(encoding="utf-8"))
        return [RunRecord.from_dict(item) for item in data]

    async def _write_runs(self, runs: list[RunRecord]) -> None:
        payload = [run.to_dict() for run in runs]
        self.runs_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
