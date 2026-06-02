import asyncio
import tempfile
import unittest

from backend.hephaestus.git_service import GitService
from backend.services.llm_gateway import LLMProvider
from main import RunControlRequest, RunCreateRequest, TaskCreateRequest, create_app


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


def find_route_endpoint(app, path: str, method: str):
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return route.endpoint
    raise AssertionError(f"Route not found: {method} {path}")


class HephaestusApiTests(unittest.TestCase):
    def test_routes_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(project_root=tmp, llm_provider=FakeProvider(), git_service=FakeGitService())
            expected = {
                ("/api/hephaestus/tasks", "POST"),
                ("/api/hephaestus/tasks", "GET"),
                ("/api/hephaestus/runs", "POST"),
                ("/api/hephaestus/runs", "GET"),
                ("/api/hephaestus/runs/{run_id}", "GET"),
                ("/api/hephaestus/runs/{run_id}/control", "POST"),
                ("/api/hephaestus/runs/{run_id}/events", "GET"),
                ("/api/hephaestus/runs/{run_id}/artifacts", "GET"),
                ("/api/hephaestus/runs/{run_id}/result", "GET"),
            }
            actual = {
                (route.path, method)
                for route in app.routes
                for method in getattr(route, "methods", set())
            }
            for item in expected:
                self.assertIn(item, actual)

    def test_endpoint_flow_without_http_client(self):
        async def run_test():
            with tempfile.TemporaryDirectory() as tmp:
                app = create_app(project_root=tmp, llm_provider=FakeProvider(), git_service=FakeGitService())
                create_task = find_route_endpoint(app, "/api/hephaestus/tasks", "POST")
                create_run = find_route_endpoint(app, "/api/hephaestus/runs", "POST")
                control_run = find_route_endpoint(app, "/api/hephaestus/runs/{run_id}/control", "POST")
                get_run = find_route_endpoint(app, "/api/hephaestus/runs/{run_id}", "GET")

                async with app.router.lifespan_context(app):
                    task_payload = await create_task(TaskCreateRequest(title="Task", description="Desc"))
                    task_id = task_payload["task"]["id"]

                    run_payload = await create_run(RunCreateRequest(task_id=task_id, max_steps=8))
                    run_id = run_payload["run"]["id"]

                    await control_run(run_id, RunControlRequest(command="START"))

                    for _ in range(80):
                        run_state = await get_run(run_id)
                        if run_state["run"]["status"] == "WAITING_APPROVAL":
                            break
                        await asyncio.sleep(0.05)

                    run_state = await get_run(run_id)
                    self.assertEqual(run_state["run"]["status"], "WAITING_APPROVAL")

                    approved = await control_run(run_id, RunControlRequest(command="APPROVE"))
                    self.assertEqual(approved["run"]["status"], "COMPLETED")

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
