# Internal Service: Sandbox & Command Executor

- Executes `<execute>` commands via subprocess asynchronously.
- Enforces command timeout (default 60s) and kills hung processes.
- Captures stdout/stderr and injects output back into next prompt.
- Requires non-interactive commands (`--yes`, `--quiet` where needed).
