import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from core.edge_actions.config import EdgeActionsConfig
from core.edge_actions.models import ActionToken, ActionTokenType, Observation
from core.edge_actions.runner import EdgeActionRunner


class _FakeSession:
    def __init__(self, config):
        self.config = config
        self.page = object()
        self._obs_count = 0

    def start(self):
        return None

    def stop(self):
        return None

    def observe(self):
        self._obs_count += 1
        # before step 0
        if self._obs_count == 1:
            return Observation(
                url="https://example.com/home",
                title="Home",
                visible_text="hello",
                interactive_elements=[],
                downloads=[],
                active_tab="Home",
                timestamp="2026-01-01T00:00:00",
                error_state=None,
            )
        # after step 0 (unintended cross-host)
        if self._obs_count == 2:
            return Observation(
                url="https://wrong.example.org",
                title="Wrong",
                visible_text="hello",
                interactive_elements=[],
                downloads=[],
                active_tab="Wrong",
                timestamp="2026-01-01T00:00:01",
                error_state=None,
            )
        # correction observation and later observations
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
        # Allow auto-correction NAVIGATE calls without failure.
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
                # Deterministically force a click then stop to test consequence handling.
                forced_actions = [
                    ActionToken(action_type=ActionTokenType.CLICK, target="wrong link"),
                    ActionToken(action_type=ActionTokenType.STOP, value="done"),
                ]
                runner.planner.next_action = lambda task, obs, brain_snapshot=None: forced_actions.pop(0)
                result = runner.run_task("company_research", {"objective": "test"})
                self.assertIn(result["status"], {"completed", "paused_for_approval", "verification_failed"})
                self.assertTrue(Path(result["trace_path"]).exists())

                payload = json.loads(Path(result["trace_path"]).read_text(encoding="utf-8"))
                events = payload.get("events", []) if isinstance(payload, dict) else []
                has_consequence = any(e.get("type") == "consequence_assessment" for e in events if isinstance(e, dict))
                has_correction = any(e.get("type") == "consequence_correction" for e in events if isinstance(e, dict))
                self.assertTrue(has_consequence)
                self.assertTrue(has_correction)


if __name__ == "__main__":
    unittest.main()
