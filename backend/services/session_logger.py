from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class SessionLogger:
    def __init__(self, project_root: str = ".") -> None:
        self.project_root = Path(project_root).resolve()
        self.session_root: Path | None = None

    async def initialize_session(self) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.session_root = self.project_root / ".session" / timestamp
        (self.session_root / "prompts").mkdir(parents=True, exist_ok=True)
        return self.session_root

    async def log_event(self, event_type: str, payload: dict) -> Path:
        session_root = self.session_root or await self.initialize_session()
        event_file = session_root / "events.jsonl"
        with event_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"event_type": event_type, "payload": payload}) + "\n")
        return event_file

    async def save_prompt_response(
        self, agent_role: str, task_name: str, prompt: str, response: str
    ) -> tuple[Path, Path]:
        session_root = self.session_root or await self.initialize_session()
        safe_name = f"{agent_role}_{task_name}".replace(" ", "_")
        prompt_path = session_root / "prompts" / f"{safe_name}_prompt.txt"
        response_path = session_root / "prompts" / f"{safe_name}_response.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        response_path.write_text(response, encoding="utf-8")
        return prompt_path, response_path
