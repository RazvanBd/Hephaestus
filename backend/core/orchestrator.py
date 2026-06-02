from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol

from backend.core.event_bus import AsyncEventBus
from backend.core.state_machine import HermesState, StateMachine
from backend.services.llm_gateway import LLMProvider
from backend.services.session_logger import SessionLogger
from backend.services.workspace_manager import WorkspaceManager
from backend.services.xml_parser import XMLParser, XMLParsingError

RETRY_ERROR = (
    "System error: The previous response did not contain valid XML tags or was incorrect. "
    "You MUST use <file>, <execute>, or <transition_to> tags. Please try again."
)


class CommandExecutor(Protocol):
    async def execute(self, command: str, *, working_dir: str): ...


@dataclass
class Orchestrator:
    llm_provider: LLMProvider
    workspace_manager: WorkspaceManager
    session_logger: SessionLogger
    command_executor: CommandExecutor | None = None
    execution_working_dir: str = "."
    action_hook: Callable[[str, dict], Awaitable[None]] | None = None

    def __post_init__(self) -> None:
        self.state_machine = StateMachine()
        self.event_bus = AsyncEventBus()

    async def pause(self) -> None:
        old_state, new_state = self.state_machine.transition(HermesState.PAUSED)
        await self.event_bus.publish(
            "StateTransition",
            {"old_state": old_state.value, "new_state": new_state.value},
        )

    async def resume(self) -> None:
        if self.state_machine.current_state == HermesState.PAUSED:
            old_state, new_state = self.state_machine.transition(HermesState.PM_BREAKDOWN)
            await self.event_bus.publish(
                "StateTransition",
                {"old_state": old_state.value, "new_state": new_state.value},
            )

    async def process_agent_turn(self, prompt: str, *, max_retries: int = 3):
        current_prompt = prompt

        for attempt in range(max_retries):
            await self.event_bus.publish("PromptAssembled", {"prompt": current_prompt})
            response = await self.llm_provider.generate_response(current_prompt)
            await self.event_bus.publish("LLMResponseReceived", {"response": response})
            await self.session_logger.save_prompt_response(
                self.state_machine.current_state.value,
                f"attempt_{attempt + 1}",
                current_prompt,
                response,
            )

            try:
                actions = XMLParser.parse(response)
            except XMLParsingError as error:
                await self.session_logger.log_event(
                    "XMLParsingError", {"attempt": attempt + 1, "error": str(error)}
                )
                if attempt + 1 >= max_retries:
                    raise
                current_prompt = f"{prompt}\n\n{RETRY_ERROR}"
                continue

            await self._apply_actions(actions)
            return actions

        return []

    async def _apply_actions(self, actions):
        for action in actions:
            if action.action_type in {"file", "doc_update"}:
                file_path = action.payload["path"]
                await self.workspace_manager.write_file(file_path, action.payload["content"])
                await self.event_bus.publish(
                    "FileModified",
                    {"path": file_path, "action": action.payload["action"]},
                )
                if self.action_hook:
                    await self.action_hook(
                        "FileModified",
                        {"path": file_path, "action": action.payload["action"]},
                    )
            elif action.action_type == "transition_to":
                requested_state = HermesState(action.payload["state"])
                old_state, new_state = self.state_machine.transition(requested_state)
                await self.event_bus.publish(
                    "StateTransition",
                    {"old_state": old_state.value, "new_state": new_state.value},
                )
                if self.action_hook:
                    await self.action_hook(
                        "StateTransition",
                        {"old_state": old_state.value, "new_state": new_state.value},
                    )
            elif action.action_type == "execute":
                payload = {"command": action.payload["command"]}
                if self.command_executor is not None:
                    result = await self.command_executor.execute(
                        action.payload["command"], working_dir=self.execution_working_dir
                    )
                    payload.update(
                        {
                            "return_code": result.return_code,
                            "stdout": result.stdout,
                            "stderr": result.stderr,
                            "timed_out": result.timed_out,
                            "success": result.success,
                        }
                    )
                await self.event_bus.publish("CommandExecuted", payload)
                if self.action_hook:
                    await self.action_hook("CommandExecuted", payload)
                if self.command_executor is not None and not payload.get("success", False):
                    raise RuntimeError(
                        f"Command execution failed: {action.payload['command']}"
                    )
