# Internal Service: Workspace & Git Controller

## File System Manager
- Handles all reads/writes from XML tags.
- Enforces path traversal protection.
- Supports path-switching docs lookup (`src/X` -> `docs/X.md` or module rules).

## Git Automation
- On QA approval transition back to PM:
  1. `git add .`
  2. derive task from `03_Management/current_task.md`
  3. `git commit -m "[Hermes-Auto] {Task_Name}"`
  4. capture hash for audit link.

## Session Auditor
- Persist Event Bus events as append-only `.session/*/events.jsonl`.
