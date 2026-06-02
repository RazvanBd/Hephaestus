import asyncio
import tempfile
import unittest

from backend.hephaestus.sandbox_executor import SandboxExecutor


class SandboxExecutorTests(unittest.TestCase):
    def test_executes_command_and_captures_output(self):
        async def run_test():
            with tempfile.TemporaryDirectory() as tmp:
                executor = SandboxExecutor(timeout_seconds=5)
                result = await executor.execute("python -c \"print('ok')\"", working_dir=tmp)
                self.assertTrue(result.success)
                self.assertEqual(result.return_code, 0)
                self.assertIn("ok", result.stdout)

        asyncio.run(run_test())

    def test_marks_timeout(self):
        async def run_test():
            with tempfile.TemporaryDirectory() as tmp:
                executor = SandboxExecutor(timeout_seconds=1)
                result = await executor.execute("python -c \"import time; time.sleep(2)\"", working_dir=tmp)
                self.assertTrue(result.timed_out)
                self.assertFalse(result.success)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
