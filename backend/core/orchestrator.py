from __future__ import annotations

from dataclasses import dataclass

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


@dataclass
class Orchestrator:
    llm_provider: LLMProvider
    workspace_manager: WorkspaceManager
    session_logger: SessionLogger

    def __post_init__(self) -> None:
        self.state_machine = StateMachine()
        self.event_bus = AsyncEventBus()

    async def pause(self) -> None:
        old_state = self.state_machine.current_state
        self.state_machine.current_state = HermesState.PAUSED
        await self.event_bus.publish(
            "StateTransition",
            {"old_state": old_state.value, "new_state": HermesState.PAUSED.value},
        )

    async def resume(self) -> None:
        if self.state_machine.current_state == HermesState.PAUSED:
            self.state_machine.current_state = HermesState.PM_BREAKDOWN
            await self.event_bus.publish(
                "StateTransition",
                {
                    "old_state": HermesState.PAUSED.value,
                    "new_state": HermesState.PM_BREAKDOWN.value,
                },
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
            elif action.action_type == "transition_to":
                requested_state = HermesState(action.payload["state"])
                old_state, new_state = self.state_machine.transition(requested_state)
                await self.event_bus.publish(
                    "StateTransition",
                    {"old_state": old_state.value, "new_state": new_state.value},
                )
            elif action.action_type == "execute":
                await self.event_bus.publish(
                    "CommandExecuted", {"command": action.payload["command"]}
                )
