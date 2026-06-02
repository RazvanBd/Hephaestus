import asyncio
import tempfile
import unittest
from pathlib import Path

from backend.services.workspace_manager import WorkspaceManager


class WorkspaceManagerTests(unittest.TestCase):
    def test_blocks_path_traversal(self):
        async def run_test():
            with tempfile.TemporaryDirectory() as tmp:
                manager = WorkspaceManager(tmp)
                await manager.initialize_workspace()
                with self.assertRaises(ValueError):
                    await manager.write_file("../bad.txt", "nope")

        asyncio.run(run_test())

    def test_resolve_doc_context_prefers_matching_doc_file(self):
        async def run_test():
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                manager = WorkspaceManager(tmp)
                await manager.initialize_workspace()
                target = root / "docs" / "core" / "router.md"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("rules", encoding="utf-8")

                doc = await manager.resolve_doc_context("core/router.py")
                self.assertEqual(doc, target)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
