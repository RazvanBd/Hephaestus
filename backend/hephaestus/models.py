from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from backend.core.state_machine import HermesState


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"


class RunStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RunControlCommand(str, Enum):
    START = "START"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    CANCEL = "CANCEL"
    APPROVE = "APPROVE"


@dataclass
class TaskRecord:
    id: str
    title: str
    description: str
    status: TaskStatus
    created_at: str
    updated_at: str
    run_ids: list[str] = field(default_factory=list)

    @classmethod
    def create(cls, title: str, description: str) -> "TaskRecord":
        now = utc_now()
        return cls(
            id=f"task-{uuid4().hex[:12]}",
            title=title,
            description=description,
            status=TaskStatus.QUEUED,
            created_at=now,
            updated_at=now,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "run_ids": list(self.run_ids),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TaskRecord":
        return cls(
            id=str(payload["id"]),
            title=str(payload["title"]),
            description=str(payload.get("description", "")),
            status=TaskStatus(str(payload["status"])),
            created_at=str(payload["created_at"]),
            updated_at=str(payload["updated_at"]),
            run_ids=[str(run_id) for run_id in payload.get("run_ids", [])],
        )


@dataclass
class RunRecord:
    id: str
    task_id: str
    status: RunStatus
    created_at: str
    updated_at: str
    current_state: HermesState
    workspace_root: str
    attempts: int = 0
    max_steps: int = 8
    approved: bool = False
    commit_hash: str | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    @classmethod
    def create(cls, task_id: str, workspace_root: str, max_steps: int = 8) -> "RunRecord":
        now = utc_now()
        return cls(
            id=f"run-{uuid4().hex[:12]}",
            task_id=task_id,
            status=RunStatus.CREATED,
            created_at=now,
            updated_at=now,
            current_state=HermesState.WAITING_FOR_CLIENT,
            workspace_root=workspace_root,
            max_steps=max_steps,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "current_state": self.current_state.value,
            "workspace_root": self.workspace_root,
            "attempts": self.attempts,
            "max_steps": self.max_steps,
            "approved": self.approved,
            "commit_hash": self.commit_hash,
            "result": self.result,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RunRecord":
        return cls(
            id=str(payload["id"]),
            task_id=str(payload["task_id"]),
            status=RunStatus(str(payload["status"])),
            created_at=str(payload["created_at"]),
            updated_at=str(payload["updated_at"]),
            current_state=HermesState(str(payload["current_state"])),
            workspace_root=str(payload["workspace_root"]),
            attempts=int(payload.get("attempts", 0)),
            max_steps=int(payload.get("max_steps", 8)),
            approved=bool(payload.get("approved", False)),
            commit_hash=payload.get("commit_hash"),
            result=payload.get("result"),
            error=payload.get("error"),
        )


def can_apply_control(status: RunStatus, command: RunControlCommand) -> bool:
    allowed: dict[RunStatus, set[RunControlCommand]] = {
        RunStatus.CREATED: {RunControlCommand.START, RunControlCommand.CANCEL},
        RunStatus.RUNNING: {RunControlCommand.PAUSE, RunControlCommand.CANCEL},
        RunStatus.PAUSED: {RunControlCommand.RESUME, RunControlCommand.CANCEL},
        RunStatus.WAITING_APPROVAL: {RunControlCommand.APPROVE, RunControlCommand.CANCEL},
        RunStatus.COMPLETED: set(),
        RunStatus.FAILED: set(),
        RunStatus.CANCELLED: set(),
    }
    return command in allowed.get(status, set())
