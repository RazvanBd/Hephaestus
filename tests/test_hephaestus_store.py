import asyncio
import tempfile
import unittest

from backend.hephaestus.models import RunStatus, TaskStatus
from backend.hephaestus.store import HephaestusStore


class HephaestusStoreTests(unittest.TestCase):
    def test_persists_tasks_runs_and_events(self):
        async def run_test():
            with tempfile.TemporaryDirectory() as tmp:
                store = HephaestusStore(project_root=tmp)
                await store.initialize()

                task = await store.create_task("Build feature", "Do it")
                self.assertEqual(task.status, TaskStatus.QUEUED)

                run = await store.create_run(task.id, max_steps=3)
                self.assertEqual(run.status, RunStatus.CREATED)

                await store.append_event(run.id, "RunCreated", {"task_id": task.id})
                events = await store.read_events(run.id)
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0]["event_type"], "RunCreated")

                artifact_path = await store.add_artifact(run.id, "summary.txt", "done")
                self.assertTrue(artifact_path.endswith("summary.txt"))
                artifacts = await store.list_artifacts(run.id)
                self.assertEqual(len(artifacts), 1)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
