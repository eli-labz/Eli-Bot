import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.edge_actions.config import EdgeActionsConfig
from core.edge_actions.models import Observation
from core.edge_actions.runner import EdgeActionRunner


class _FakeSession:
    def __init__(self, config):
        self.config = config
        self.page = object()

    def start(self):
        return None

    def stop(self):
        return None

    def observe(self):
        return Observation(
            url="https://example.com",
            title="Example",
            visible_text="hello",
            interactive_elements=[],
            downloads=[],
            active_tab="Example",
            timestamp="2026-01-01T00:00:00",
            error_state=None,
        )


class _FakeExecutor:
    def __init__(self, page):
        self.page = page

    def execute(self, action):
        return "ok"


class RunnerIntegrationTests(unittest.TestCase):
    def test_runner_with_mocked_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = EdgeActionsConfig(
                enabled=True,
                headless=True,
                edge_channel="msedge",
                max_steps=2,
                trace_dir=Path(tmp),
            )
            with patch("core.edge_actions.runner.BrowserSession", _FakeSession), patch(
                "core.edge_actions.runner.ActionExecutor", _FakeExecutor
            ):
                runner = EdgeActionRunner(cfg)
                result = runner.run_task("company_research", {"objective": "test"})
                self.assertIn(result["status"], {"completed", "paused_for_approval", "verification_failed"})
                self.assertTrue(Path(result["trace_path"]).exists())


if __name__ == "__main__":
    unittest.main()
