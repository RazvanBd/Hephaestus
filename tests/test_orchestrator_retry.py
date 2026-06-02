import asyncio
import tempfile
import unittest
from pathlib import Path

from backend.core.orchestrator import Orchestrator
from backend.core.state_machine import HermesState
from backend.services.llm_gateway import LLMProvider
from backend.services.session_logger import SessionLogger
from backend.services.workspace_manager import WorkspaceManager


class FakeProvider(LLMProvider):
    def __init__(self):
        self.calls = 0

    async def generate_response(self, prompt: str) -> str:
        self.calls += 1
        if self.calls < 3:
            return "not xml"
        return "<transition_to>PO_ANALYSIS</transition_to>"


class OrchestratorRetryTests(unittest.TestCase):
    def test_retries_without_changing_state_until_valid_xml(self):
        async def run_test():
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                manager = WorkspaceManager(str(root))
                logger = SessionLogger(str(root))
                await manager.initialize_workspace()
                await logger.initialize_session()
                orchestrator = Orchestrator(FakeProvider(), manager, logger)
                self.assertEqual(
                    orchestrator.state_machine.current_state,
                    HermesState.WAITING_FOR_CLIENT,
                )

                actions = await orchestrator.process_agent_turn("Test prompt")

                self.assertEqual(len(actions), 1)
                self.assertEqual(
                    orchestrator.state_machine.current_state,
                    HermesState.PO_ANALYSIS,
                )

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
