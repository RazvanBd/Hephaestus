# PRD - Hephaestus Orchestrator

## Product Goal
Build Hephaestus as the supervisor system that orchestrates Hermes execution to deliver coding and non-coding tasks through controlled multi-step runs.

## Primary Users
- Operator managing task queue and active runs.
- Engineering/QA teams auditing run timelines and approvals.

## Core Requirements
1. Task intake and run creation API.
2. Run lifecycle controls (`START`, `PAUSE`, `RESUME`, `CANCEL`, `APPROVE`).
3. Persistent run/task/event/artifact tracking.
4. Persona-aware workflow coordination with stop conditions.
5. Managed command execution with timeout and captured output.
6. Approval-to-git commit bridge with audit linkage.

## Non-Functional Requirements
- Safe run isolation in per-run workspaces.
- Idempotent run controls with explicit transition validation.
- Clear failure payloads for operator diagnosis.
- Auditable timeline in append-only run event log.
