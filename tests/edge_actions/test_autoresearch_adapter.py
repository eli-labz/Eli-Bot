import tempfile
import unittest
from pathlib import Path

from core.edge_actions.autoresearch_adapter import AutoResearchAdapter


class AutoResearchAdapterTests(unittest.TestCase):
    def test_adapter_interface(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "README.md").write_text("Edge research line\n", encoding="utf-8")
            (base / "program.md").write_text("Task loop details\n", encoding="utf-8")
            adapter = AutoResearchAdapter(base_dir=base)
            result = adapter.research("edge")
            self.assertIn("sources", result)
            facts = adapter.extract_actionable_facts(result)
            self.assertIsInstance(facts, list)


if __name__ == "__main__":
    unittest.main()
