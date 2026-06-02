import asyncio
import tempfile
import unittest

from backend.hephaestus.coordinator import HephaestusCoordinator
from backend.hephaestus.git_service import GitService
from backend.hephaestus.models import RunControlCommand, RunStatus
from backend.hephaestus.store import HephaestusStore
from backend.services.llm_gateway import LLMProvider


class FakeProvider(LLMProvider):
    def __init__(self):
        self.responses = [
            "<transition_to>PO_ANALYSIS</transition_to>",
            "<transition_to>BA_PLANNING</transition_to>",
            "<transition_to>PM_BREAKDOWN</transition_to>",
            "<transition_to>DEV_CODING</transition_to>",
            "<transition_to>QA_TESTING</transition_to>",
        ]

    async def generate_response(self, prompt: str) -> str:
        if self.responses:
            return self.responses.pop(0)
        return "<transition_to>QA_TESTING</transition_to>"


class FakeGitService(GitService):
    def __init__(self):
        pass

    def commit_run(self, *, run_id: str, task_title: str) -> str:
        return f"fake-{run_id}"


class HephaestusCoordinatorTests(unittest.TestCase):
    def test_run_reaches_waiting_approval_and_can_be_approved(self):
        async def run_test():
            with tempfile.TemporaryDirectory() as tmp:
                store = HephaestusStore(project_root=tmp)
                coordinator = HephaestusCoordinator(
                    project_root=tmp,
                    llm_provider=FakeProvider(),
                    store=store,
                    git_service=FakeGitService(),
                )
                await coordinator.initialize()
                task = await coordinator.create_task("Build", "Need QA")
                run = await coordinator.create_run(task.id, max_steps=8)

                await coordinator.apply_control(run.id, RunControlCommand.START)

                for _ in range(40):
                    current = await coordinator.get_run(run.id)
                    if current.status == RunStatus.WAITING_APPROVAL:
                        break
                    await asyncio.sleep(0.05)

                current = await coordinator.get_run(run.id)
                self.assertEqual(current.status, RunStatus.WAITING_APPROVAL)

                approved = await coordinator.apply_control(run.id, RunControlCommand.APPROVE)
                self.assertEqual(approved.status, RunStatus.COMPLETED)
                self.assertTrue((approved.commit_hash or "").startswith("fake-"))

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
