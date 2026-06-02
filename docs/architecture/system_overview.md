# Hermes Orchestrator - System Overview

Hermes is an autonomous, event-driven orchestrator where project memory lives on disk.

## Core ideas
- Stateless agents receive only task + mapped docs.
- SSOT on disk: code in `src/`, rules in `docs/`.
- QA executes real terminal checks in sandbox.
- Approved micro-tasks trigger atomic git commits.

## Stack
- Backend: Python + FastAPI + WebSockets.
- Frontend: Angular dashboard.
- Session audit: JSON/JSONL under `.session/`.
