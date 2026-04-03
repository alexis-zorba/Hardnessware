from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hardness.config import ProviderConfig
from hardness.providers import MockProviderAdapter, build_provider_adapter


class CompatibilitySuiteTests(unittest.TestCase):
    def test_mock_provider_supports_basic_probe(self) -> None:
        adapter = MockProviderAdapter()
        result = adapter.run_probe("basic")
        self.assertTrue(result["ok"])

    def test_openrouter_builder_exposes_probe_capability(self) -> None:
        adapter = build_provider_adapter(
            ProviderConfig(name="openrouter", model="minimax/minimax-m2.7", api_key="dummy")
        )
        self.assertTrue(hasattr(adapter, "run_probe"))


if __name__ == "__main__":
    unittest.main()
