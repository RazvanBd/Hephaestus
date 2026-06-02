# Technical Specifications

## Architecture Boundary
- Hephaestus supervisor domain: intake, persistence, controls, approvals, and orchestration API.
- Hermes execution domain: stateful persona progression, XML action parsing, and action dispatch.

## Domain Model
- `TaskRecord`: id, title, description, status, run_ids, timestamps.
- `RunRecord`: id, task_id, status, current_state, attempts, result/error, approval metadata.

## Persistence
- Root: `.session/hephaestus/`
- Files: `tasks.json`, `runs.json`
- Per-run: `runs/<run_id>/events.jsonl`, `runs/<run_id>/artifacts/*`, `runs/<run_id>/workspace/*`

## API Contract
- Intake: `POST/GET /api/hephaestus/tasks`
- Runs: `POST/GET /api/hephaestus/runs`, `GET /api/hephaestus/runs/{run_id}`
- Control: `POST /api/hephaestus/runs/{run_id}/control`
- Observability: events/artifacts/result endpoints per run

## Reliability Rules
- Max active run limit to protect runtime resources.
- Validated control transitions via explicit transition table.
- Max-step stop condition to avoid infinite loops.
- Structured error payloads on run failures.
