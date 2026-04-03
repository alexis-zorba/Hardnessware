from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hardness.agent import AgentLoop
from hardness.config import HardnessConfig, ProviderConfig


class TaskSuiteTests(unittest.TestCase):
    def test_realistic_task_suite_file_is_valid(self) -> None:
        path = Path(__file__).resolve().parents[1] / "HARDNESS" / "05_synthesis" / "task_suite.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(payload["tasks"]), 10)

    def test_search_then_write_task_runs_with_mock_harness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("needle here", encoding="utf-8")
            agent = AgentLoop(
                HardnessConfig(
                    workspace_root=root,
                    storage_root=root / ".hardness",
                    provider=ProviderConfig(name="mock", model="mock-model"),
                )
            )
            result = agent.run("search needle")
            self.assertEqual(result["status"], "ok")
            self.assertGreaterEqual(result["metrics"]["tool_calls"], 1)


if __name__ == "__main__":
    unittest.main()
