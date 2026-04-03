from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hardness.agent import AgentLoop
from hardness.cli import _parse_api_file
from hardness.config import HardnessConfig, ModelProfile, PolicyConfig, ProviderConfig, RuntimeConfig
from hardness.providers import OpenAICompatibleAdapter, ProviderError, build_provider_adapter
from hardness.router import ModelRouter


class AgentLoopTests(unittest.TestCase):
    def test_mock_provider_returns_text_when_no_tool_is_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agent = self._build_agent(root)
            result = agent.run("hello harness")
            self.assertEqual(result["status"], "ok")
            self.assertIn("Mock response", result["final_text"])

    def test_mock_provider_can_dispatch_read_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "example.txt").write_text("sample", encoding="utf-8")
            agent = self._build_agent(root)
            result = agent.run("read example.txt")
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["tool_results"][0]["name"], "read")
            self.assertEqual(result["tool_results"][0]["content"], "sample")

    def test_search_tool_promotes_verified_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "alpha.txt").write_text("needle needle", encoding="utf-8")
            agent = self._build_agent(root)
            result = agent.run("search needle")
            self.assertEqual(result["status"], "ok")
            notes_root = root / ".hardness" / "memory" / "notes"
            notes = list(notes_root.glob("*.json"))
            self.assertTrue(notes)
            payload = json.loads(notes[0].read_text(encoding="utf-8"))
            self.assertTrue(payload["verified"])

    def test_provider_builders_support_openai_groq_and_openrouter(self) -> None:
        openai_adapter = build_provider_adapter(
            ProviderConfig(name="openai", model="gpt-4.1-mini", api_key="test-key")
        )
        groq_adapter = build_provider_adapter(
            ProviderConfig(name="groq", model="llama-3.3-70b", api_key="test-key")
        )
        openrouter_adapter = build_provider_adapter(
            ProviderConfig(name="openrouter", model="openai/gpt-4.1-mini", api_key="test-key")
        )

        self.assertIsInstance(openai_adapter, OpenAICompatibleAdapter)
        self.assertIsInstance(groq_adapter, OpenAICompatibleAdapter)
        self.assertIsInstance(openrouter_adapter, OpenAICompatibleAdapter)
        self.assertEqual(openai_adapter.config.base_url, None)
        self.assertEqual(groq_adapter.config.base_url, "https://api.groq.com/openai/v1")
        self.assertEqual(openrouter_adapter.config.base_url, "https://openrouter.ai/api/v1")

    def test_openai_compatible_adapter_requires_api_key(self) -> None:
        adapter = build_provider_adapter(ProviderConfig(name="openai", model="gpt-4.1-mini"))
        with self.assertRaises(ProviderError):
            adapter.generate([], [])

    def test_write_guardrail_blocks_disallowed_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agent = AgentLoop(
                HardnessConfig(
                    workspace_root=root,
                    storage_root=root / ".hardness",
                    provider=ProviderConfig(name="mock", model="mock-model"),
                    policy=PolicyConfig(workspace_root=root, allowed_extensions=(".txt",)),
                )
            )
            result = agent.tools.execute("write", {"path": "allowed.txt", "content": "ok"})
            self.assertTrue(result.success)
            with self.assertRaises(Exception):
                agent.tools.execute("write", {"path": "blocked.bin", "content": "no"})

    def test_cli_parser_can_read_api_file_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "API.txt"
            path.write_text("Openrouter:\nrouter-key\n\nGroq:\ngroq-key\n", encoding="utf-8")
            parsed = _parse_api_file(path)
            self.assertEqual(parsed["openrouter"], "router-key")
            self.assertEqual(parsed["groq"], "groq-key")

    def test_loop_stops_after_repeated_identical_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "example.txt").write_text("sample", encoding="utf-8")
            agent = AgentLoop(
                HardnessConfig(
                    workspace_root=root,
                    storage_root=root / ".hardness",
                    provider=ProviderConfig(name="mock", model="mock-model"),
                    runtime=RuntimeConfig(max_turns=4, max_repeated_identical_actions=1),
                )
            )
            result = agent.run("read example.txt")
            self.assertIn(result["stop_reason"], {"completed", "repeated_action_limit", "max_turns_reached", "redundant_read_suppressed"})
            self.assertGreaterEqual(result["metrics"]["final_after_success_rate"], 0.0)

    def test_router_uses_default_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agent = AgentLoop(
                HardnessConfig(
                    workspace_root=root,
                    storage_root=root / ".hardness",
                    provider=ProviderConfig(name="groq", model="fallback-model", api_key="test-key"),
                    model_profiles=(
                        ModelProfile(
                            name="minimax-default",
                            provider="openrouter",
                            model="minimax/minimax-m2.7",
                            role="default",
                        ),
                    ),
                )
            )
            result = agent.run("hello harness")
            self.assertEqual(result["status"], "error")

    def test_router_opportunistic_qwen_for_low_risk_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = HardnessConfig(
                workspace_root=root,
                storage_root=root / ".hardness",
                provider=ProviderConfig(name="openrouter", model="minimax/minimax-m2.7", api_key="test-key"),
                model_profiles=(
                    ModelProfile(name="minimax-default", provider="openrouter", model="minimax/minimax-m2.7", role="default"),
                    ModelProfile(name="qwen-opportunistic", provider="openrouter", model="qwen/qwen3.6-plus-preview:free", role="opportunistic"),
                ),
                enable_opportunistic_qwen=True,
            )
            router = ModelRouter(config)
            provider, decision = router.route("read README.md", opportunistic=True)
            self.assertEqual(provider.model, "qwen/qwen3.6-plus-preview:free")
            self.assertEqual(decision.reason, "opportunistic_low_risk")

    def test_router_blocks_opportunistic_qwen_for_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = HardnessConfig(
                workspace_root=root,
                storage_root=root / ".hardness",
                provider=ProviderConfig(name="openrouter", model="minimax/minimax-m2.7", api_key="test-key"),
                model_profiles=(
                    ModelProfile(name="minimax-default", provider="openrouter", model="minimax/minimax-m2.7", role="default"),
                    ModelProfile(name="qwen-opportunistic", provider="openrouter", model="qwen/qwen3.6-plus-preview:free", role="opportunistic"),
                ),
                enable_opportunistic_qwen=True,
            )
            router = ModelRouter(config)
            provider, decision = router.route("write tmp/x.txt with note", opportunistic=True)
            self.assertEqual(provider.model, "minimax/minimax-m2.7")
            self.assertEqual(decision.reason, "default_profile")

    def test_write_task_stops_with_write_completed_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agent = AgentLoop(
                HardnessConfig(
                    workspace_root=root,
                    storage_root=root / ".hardness",
                    provider=ProviderConfig(name="mock", model="mock-model"),
                )
            )
            result = agent.run("write note.txt with hello")
            self.assertEqual(result["status"], "ok")
            self.assertIn(result["stop_reason"], {"write_completed", "completed"})

    def _build_agent(self, root: Path) -> AgentLoop:
        return AgentLoop(
            HardnessConfig(
                workspace_root=root,
                storage_root=root / ".hardness",
                provider=ProviderConfig(name="mock", model="mock-model"),
            )
        )


if __name__ == "__main__":
    unittest.main()
