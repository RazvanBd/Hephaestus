from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Awaitable, Callable

from backend.core.orchestrator import Orchestrator
from backend.core.state_machine import HermesState
from backend.hephaestus.errors import ConflictError, InvalidTransitionError, NotFoundError
from backend.hephaestus.git_service import GitService
from backend.hephaestus.models import (
    RunControlCommand,
    RunRecord,
    RunStatus,
    TaskRecord,
    TaskStatus,
    can_apply_control,
)
from backend.hephaestus.personas import build_persona_prompt
from backend.hephaestus.sandbox_executor import SandboxExecutor
from backend.hephaestus.store import HephaestusStore
from backend.services.llm_gateway import LLMProvider
from backend.services.session_logger import SessionLogger
from backend.services.workspace_manager import WorkspaceManager


class HephaestusCoordinator:
    def __init__(
        self,
        *,
        project_root: str,
        llm_provider: LLMProvider,
        store: HephaestusStore,
        git_service: GitService,
        max_active_runs: int = 3,
        event_sink: Callable[[str, dict], Awaitable[None]] | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.llm_provider = llm_provider
        self.store = store
        self.git_service = git_service
        self.max_active_runs = max_active_runs
        self.event_sink = event_sink
        self._run_tasks: dict[str, asyncio.Task[None]] = {}
        self._active_lock = asyncio.Lock()

    async def initialize(self) -> None:
        await self.store.initialize()

    async def create_task(self, title: str, description: str) -> TaskRecord:
        return await self.store.create_task(title=title, description=description)

    async def list_tasks(self) -> list[TaskRecord]:
        return await self.store.list_tasks()

    async def create_run(self, task_id: str, *, max_steps: int = 8) -> RunRecord:
        task = await self.store.get_task(task_id)
        run = await self.store.create_run(task_id=task.id, max_steps=max_steps)
        task.run_ids.append(run.id)
        await self.store.save_task(task)
        await self.store.append_event(run.id, "RunCreated", {"task_id": task.id})
        return run

    async def list_runs(self) -> list[RunRecord]:
        return await self.store.list_runs()

    async def get_run(self, run_id: str) -> RunRecord:
        return await self.store.get_run(run_id)

    async def run_events(self, run_id: str) -> list[dict]:
        return await self.store.read_events(run_id)

    async def run_artifacts(self, run_id: str) -> list[str]:
        return await self.store.list_artifacts(run_id)

    async def apply_control(self, run_id: str, command: RunControlCommand) -> RunRecord:
        run = await self.store.get_run(run_id)
        if not can_apply_control(run.status, command):
            raise InvalidTransitionError(f"Cannot apply {command.value} to {run.status.value}")

        if command == RunControlCommand.START:
            await self._start_run(run)
        elif command == RunControlCommand.PAUSE:
            run.status = RunStatus.PAUSED
            await self.store.save_run(run)
            task = await self.store.set_task_status(run.task_id, TaskStatus.PAUSED)
            await self.store.append_event(run.id, "RunPaused", {"task_status": task.status.value})
        elif command == RunControlCommand.RESUME:
            run.status = RunStatus.RUNNING
            await self.store.save_run(run)
            await self.store.set_task_status(run.task_id, TaskStatus.RUNNING)
            await self.store.append_event(run.id, "RunResumed", {})
            await self._start_run(run)
        elif command == RunControlCommand.CANCEL:
            run.status = RunStatus.CANCELLED
            await self.store.save_run(run)
            await self.store.set_task_status(run.task_id, TaskStatus.CANCELLED)
            running = self._run_tasks.get(run.id)
            if running and not running.done():
                running.cancel()
            await self.store.append_event(run.id, "RunCancelled", {})
        elif command == RunControlCommand.APPROVE:
            await self._approve_run(run)

        return await self.store.get_run(run_id)

    async def _start_run(self, run: RunRecord) -> None:
        async with self._active_lock:
            in_progress = [
                task
                for task in self._run_tasks.values()
                if not task.done()
            ]
            if len(in_progress) >= self.max_active_runs:
                raise ConflictError("Active run limit reached")

            existing = self._run_tasks.get(run.id)
            if existing and not existing.done():
                return

            run.status = RunStatus.RUNNING
            await self.store.save_run(run)
            await self.store.set_task_status(run.task_id, TaskStatus.RUNNING)
            self._run_tasks[run.id] = asyncio.create_task(self._run_loop(run.id))

    async def _approve_run(self, run: RunRecord) -> None:
        task = await self.store.get_task(run.task_id)
        commit_hash = self.git_service.commit_run(run_id=run.id, task_title=task.title)
        run.approved = True
        run.commit_hash = commit_hash or None
        run.status = RunStatus.COMPLETED
        run.result = {
            "approved": True,
            "commit_hash": run.commit_hash,
            "message": "Run approved and committed",
        }
        await self.store.save_run(run)
        await self.store.set_task_status(run.task_id, TaskStatus.COMPLETED)
        await self.store.append_event(
            run.id,
            "RunApproved",
            {"commit_hash": run.commit_hash},
        )

    async def _run_loop(self, run_id: str) -> None:
        run = await self.store.get_run(run_id)
        task_record = await self.store.get_task(run.task_id)
        workspace_root = Path(run.workspace_root)

        self._seed_workspace(workspace_root)

        workspace_manager = WorkspaceManager(project_root=str(workspace_root))
        session_logger = SessionLogger(project_root=str(workspace_root))
        executor = SandboxExecutor(timeout_seconds=60)
        command_index = 0

        async def action_hook(event_type: str, payload: dict) -> None:
            nonlocal command_index
            await self.store.append_event(run_id, event_type, payload)
            if self.event_sink is not None:
                await self.event_sink(event_type, {"run_id": run_id, **payload})
            if event_type == "CommandExecuted":
                command_index += 1
                stdout = str(payload.get("stdout", ""))
                stderr = str(payload.get("stderr", ""))
                await self.store.add_artifact(run_id, f"command_{command_index}_stdout.log", stdout)
                await self.store.add_artifact(run_id, f"command_{command_index}_stderr.log", stderr)

        orchestrator = Orchestrator(
            llm_provider=self.llm_provider,
            workspace_manager=workspace_manager,
            session_logger=session_logger,
            command_executor=executor,
            execution_working_dir=str(workspace_root),
            action_hook=action_hook,
        )

        await workspace_manager.initialize_workspace()
        await session_logger.initialize_session()

        try:
            for _ in range(run.max_steps):
                run = await self.store.get_run(run_id)
                if run.status in {RunStatus.CANCELLED, RunStatus.PAUSED}:
                    return

                events = await self.store.read_events(run_id)
                prompt = build_persona_prompt(
                    project_root=str(self.project_root),
                    task_title=task_record.title,
                    task_description=task_record.description,
                    state=orchestrator.state_machine.current_state,
                    recent_events=events,
                )
                actions = await orchestrator.process_agent_turn(prompt)
                run.attempts += 1
                run.current_state = orchestrator.state_machine.current_state
                await self.store.save_run(run)

                if orchestrator.state_machine.current_state == HermesState.PAUSED:
                    run.status = RunStatus.PAUSED
                    await self.store.save_run(run)
                    await self.store.set_task_status(task_record.id, TaskStatus.PAUSED)
                    await self.store.append_event(run.id, "RunPausedByWorkflow", {})
                    return

                if orchestrator.state_machine.current_state == HermesState.QA_TESTING:
                    run.status = RunStatus.WAITING_APPROVAL
                    run.result = {
                        "message": "QA reached; waiting for operator approval",
                        "state": orchestrator.state_machine.current_state.value,
                        "attempts": run.attempts,
                    }
                    await self.store.save_run(run)
                    await self.store.set_task_status(task_record.id, TaskStatus.WAITING_APPROVAL)
                    await self.store.append_event(run.id, "AwaitingApproval", run.result)
                    return

            run.status = RunStatus.FAILED
            run.error = {
                "code": "MAX_STEPS_REACHED",
                "message": f"Run stopped after {run.max_steps} steps without approval state",
            }
            await self.store.save_run(run)
            await self.store.set_task_status(task_record.id, TaskStatus.FAILED)
            await self.store.append_event(run.id, "RunFailed", run.error)
        except asyncio.CancelledError:
            raise
        except Exception as error:  # pragma: no cover - defensive orchestration boundary
            run = await self.store.get_run(run_id)
            run.status = RunStatus.FAILED
            run.error = {
                "code": "RUN_EXECUTION_ERROR",
                "message": str(error),
                "error_type": type(error).__name__,
            }
            await self.store.save_run(run)
            await self.store.set_task_status(task_record.id, TaskStatus.FAILED)
            await self.store.append_event(run.id, "RunFailed", run.error)

    def _seed_workspace(self, workspace_root: Path) -> None:
        src_dir = self.project_root / "src"
        docs_dir = self.project_root / "docs"
        target_src = workspace_root / "src"
        target_docs = workspace_root / "docs"
        target_src.mkdir(parents=True, exist_ok=True)
        target_docs.mkdir(parents=True, exist_ok=True)

        if src_dir.exists() and target_src.exists() and not any(target_src.iterdir()):
            for item in src_dir.iterdir():
                destination = target_src / item.name
                if item.is_dir():
                    shutil.copytree(item, destination, dirs_exist_ok=True)
                else:
                    destination.write_text(item.read_text(encoding="utf-8"), encoding="utf-8")
        if docs_dir.exists() and target_docs.exists() and not any(target_docs.iterdir()):
            for item in docs_dir.iterdir():
                destination = target_docs / item.name
                if item.is_dir():
                    shutil.copytree(item, destination, dirs_exist_ok=True)
                else:
                    destination.write_text(item.read_text(encoding="utf-8"), encoding="utf-8")
