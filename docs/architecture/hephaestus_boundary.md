# Hephaestus / Hermes Architecture Boundary

## Hephaestus (Supervisor)
- Accepts tasks and creates runs.
- Maintains task/run lifecycle state and persistence.
- Enforces run controls and transition validity.
- Coordinates Hermes execution loops.
- Stores run timelines, artifacts, and outcomes.
- Owns approval workflow and git commit linkage.

## Hermes (Execution Engine)
- Runs persona-driven workflow state transitions.
- Converts LLM response to structured XML actions.
- Applies file/doc updates in isolated workspace.
- Executes commands via managed executor.
- Emits action-level events consumed by Hephaestus.

## Interface Contract
Hephaestus calls Hermes through orchestrator turns and receives:
- state transitions
- file mutations
- command execution outputs
- retry/failure signals

Hephaestus never delegates lifecycle ownership to Hermes.
