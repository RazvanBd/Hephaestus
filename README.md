# Hephaestus

Hephaestus is the supervisor orchestration layer that manages Hermes execution loops for coding and operational tasks.

## Boundary: Hephaestus vs Hermes

- **Hephaestus** owns task intake, run lifecycle, persistence, approvals, operator controls, and git approval flow.
- **Hermes** executes persona-driven prompt turns and emits structured actions (`<file>`, `<doc_update>`, `<execute>`, `<transition_to>`).

## Core capabilities implemented

- Task and run domain model with lifecycle status transitions.
- Persistent run/task/event/artifact storage under `.session/hephaestus/`.
- Orchestration API for intake, run creation, controls, inspection, result retrieval.
- Workflow coordinator with persona prompt assembly and stop conditions.
- Managed command execution backend with timeout/output capture.
- Per-run isolated workspace under `.session/hephaestus/runs/<run_id>/workspace`.
- Approval + git integration (`APPROVE` control commits local changes).

## API quick reference

- `POST /api/hephaestus/tasks`
- `GET /api/hephaestus/tasks`
- `POST /api/hephaestus/runs`
- `GET /api/hephaestus/runs`
- `GET /api/hephaestus/runs/{run_id}`
- `POST /api/hephaestus/runs/{run_id}/control`
- `GET /api/hephaestus/runs/{run_id}/events`
- `GET /api/hephaestus/runs/{run_id}/artifacts`
- `GET /api/hephaestus/runs/{run_id}/result`

Controls: `START`, `PAUSE`, `RESUME`, `CANCEL`, `APPROVE`.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

On Windows, run `start_project.bat`.

## Tests

```bash
python -m unittest discover tests -v
```
