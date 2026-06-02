from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.core.agent_graph import build_agent_graph
from backend.core.event_bus import AsyncEventBus
from backend.core.state_machine import HermesState
from backend.hephaestus.coordinator import HephaestusCoordinator
from backend.hephaestus.errors import ConflictError, InvalidTransitionError, NotFoundError
from backend.hephaestus.git_service import GitService
from backend.hephaestus.models import RunControlCommand, RunRecord, RunStatus, TaskRecord
from backend.hephaestus.store import HephaestusStore
from backend.services.llm_gateway import LLMProvider, LocalOllamaProvider


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""


class RunCreateRequest(BaseModel):
    task_id: str = Field(min_length=1)
    max_steps: int = Field(default=8, ge=1, le=50)


class RunControlRequest(BaseModel):
    command: RunControlCommand


class AppContext:
    def __init__(
        self,
        project_root: str = ".",
        *,
        llm_provider: LLMProvider | None = None,
        git_service: GitService | None = None,
    ) -> None:
        self.event_bus = AsyncEventBus()
        self.store = HephaestusStore(project_root=project_root)
        self.coordinator = HephaestusCoordinator(
            project_root=project_root,
            llm_provider=llm_provider or LocalOllamaProvider(),
            store=self.store,
            git_service=git_service or GitService(project_root=project_root),
            event_sink=self.event_bus.publish,
        )


def serialize_task(task: TaskRecord) -> dict[str, Any]:
    return task.to_dict()


def serialize_run(run: RunRecord) -> dict[str, Any]:
    return run.to_dict()


def create_app(
    project_root: str = ".",
    *,
    llm_provider: LLMProvider | None = None,
    git_service: GitService | None = None,
) -> FastAPI:
    context = AppContext(
        project_root=project_root,
        llm_provider=llm_provider,
        git_service=git_service,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await context.store.initialize()
        await context.coordinator.initialize()
        yield

    app = FastAPI(title="Hephaestus Orchestrator", lifespan=lifespan)

    @app.get("/api/dashboard/agent-network")
    async def agent_network() -> dict[str, object]:
        runs = await context.coordinator.list_runs()
        active = next(
            (
                run
                for run in runs
                if run.status in {RunStatus.RUNNING, RunStatus.PAUSED, RunStatus.WAITING_APPROVAL}
            ),
            None,
        )
        state = HermesState.WAITING_FOR_CLIENT if active is None else active.current_state
        return build_agent_graph(state)

    @app.websocket("/ws/dashboard")
    async def dashboard_socket(websocket: WebSocket) -> None:
        await context.event_bus.connect(websocket)
        await context.event_bus.publish(
            "StateTransition",
            {"old_state": None, "new_state": HermesState.WAITING_FOR_CLIENT.value},
        )
        try:
            while True:
                await websocket.receive_json()
        except WebSocketDisconnect:
            await context.event_bus.disconnect(websocket)

    @app.post("/api/hephaestus/tasks")
    async def create_task(request: TaskCreateRequest) -> dict[str, Any]:
        task = await context.coordinator.create_task(request.title, request.description)
        return {"task": serialize_task(task)}

    @app.get("/api/hephaestus/tasks")
    async def list_tasks() -> dict[str, Any]:
        tasks = await context.coordinator.list_tasks()
        return {"tasks": [serialize_task(task) for task in tasks]}

    @app.post("/api/hephaestus/runs")
    async def create_run(request: RunCreateRequest) -> dict[str, Any]:
        try:
            run = await context.coordinator.create_run(request.task_id, max_steps=request.max_steps)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"run": serialize_run(run)}

    @app.get("/api/hephaestus/runs")
    async def list_runs() -> dict[str, Any]:
        runs = await context.coordinator.list_runs()
        return {"runs": [serialize_run(run) for run in runs]}

    @app.get("/api/hephaestus/runs/{run_id}")
    async def get_run(run_id: str) -> dict[str, Any]:
        try:
            run = await context.coordinator.get_run(run_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"run": serialize_run(run)}

    @app.post("/api/hephaestus/runs/{run_id}/control")
    async def control_run(run_id: str, request: RunControlRequest) -> dict[str, Any]:
        try:
            run = await context.coordinator.apply_control(run_id, request.command)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except InvalidTransitionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"run": serialize_run(run)}

    @app.get("/api/hephaestus/runs/{run_id}/events")
    async def run_events(run_id: str) -> dict[str, Any]:
        try:
            await context.coordinator.get_run(run_id)
            events = await context.coordinator.run_events(run_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"events": events}

    @app.get("/api/hephaestus/runs/{run_id}/artifacts")
    async def run_artifacts(run_id: str) -> dict[str, Any]:
        try:
            await context.coordinator.get_run(run_id)
            artifacts = await context.coordinator.run_artifacts(run_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"artifacts": artifacts}

    @app.get("/api/hephaestus/runs/{run_id}/result")
    async def run_result(run_id: str) -> dict[str, Any]:
        try:
            run = await context.coordinator.get_run(run_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "result": run.result,
            "error": run.error,
            "status": run.status.value,
            "commit_hash": run.commit_hash,
            "approved": run.approved,
        }

    app.mount("/", StaticFiles(directory="frontend/dashboard", html=True), name="dashboard")

    return app


app = create_app(project_root=".")
