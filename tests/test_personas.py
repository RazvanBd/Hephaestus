import unittest
from pathlib import Path

from backend.core.state_machine import HermesState
from backend.hephaestus.personas import build_persona_prompt


class PersonaPromptTests(unittest.TestCase):
    def test_prompt_includes_agent_roster_and_current_contract(self):
        project_root = Path(__file__).resolve().parents[1]

        prompt = build_persona_prompt(
            project_root=str(project_root),
            task_title="Tighten flow",
            task_description="Need specialist consultation support",
            state=HermesState.DEV_CODING,
            recent_events=[],
        )

        self.assertIn("Agent roster:", prompt)
        self.assertIn("ARCHITECT_REVIEW — Solution Architect", prompt)
        self.assertIn("SECURITY_REVIEW — Security Reviewer", prompt)
        self.assertIn("UX_REVIEW — UX/UI Reviewer", prompt)
        self.assertIn("# Persona: Hermes Senior Developer (Dev)", prompt)


if __name__ == "__main__":
    unittest.main()
