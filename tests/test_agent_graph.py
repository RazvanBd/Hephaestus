import unittest

from backend.core.agent_graph import build_agent_graph
from backend.core.state_machine import HermesState


class AgentGraphTests(unittest.TestCase):
    def test_marks_current_agent_and_active_links(self):
        graph = build_agent_graph(HermesState.PM_BREAKDOWN)

        current_nodes = [node for node in graph["nodes"] if node["isCurrent"]]
        self.assertEqual(len(current_nodes), 1)
        self.assertEqual(current_nodes[0]["id"], "pm")

        active_links = {
            (link["source"], link["target"])
            for link in graph["links"]
            if link["isActive"]
        }
        self.assertEqual(active_links, {("pm", "architect"), ("pm", "ux"), ("pm", "dev"), ("pm", "paused")})

    def test_exposes_loopback_paths_for_qa(self):
        graph = build_agent_graph(HermesState.QA_TESTING)

        qa_links = [
            link
            for link in graph["links"]
            if link["source"] == "qa"
        ]

        self.assertEqual(
            {(link["source"], link["target"]) for link in qa_links},
            {("qa", "pm"), ("qa", "dev"), ("qa", "security"), ("qa", "paused")},
        )
        self.assertTrue(all(link["isActive"] for link in qa_links))

    def test_exposes_specialist_consultation_routes_for_dev(self):
        graph = build_agent_graph(HermesState.DEV_CODING)

        dev_links = [
            link
            for link in graph["links"]
            if link["source"] == "dev"
        ]

        self.assertEqual(
            {(link["source"], link["target"]) for link in dev_links},
            {("dev", "architect"), ("dev", "ux"), ("dev", "security"), ("dev", "qa"), ("dev", "paused")},
        )
        self.assertTrue(all(link["isActive"] for link in dev_links))


if __name__ == "__main__":
    unittest.main()
