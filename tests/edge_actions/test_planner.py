import unittest
from unittest.mock import patch

from core.edge_actions.models import Observation, ActionTokenType
from core.edge_actions.planner import Planner
from core.edge_actions.task_catalog import get_task


class PlannerTests(unittest.TestCase):
    def _obs(self):
        return Observation(
            url="https://example.com",
            title="Example",
            visible_text="text",
            interactive_elements=[],
            downloads=[],
            active_tab="Example",
            timestamp="2026-01-01T00:00:00",
            error_state=None,
        )

    def test_next_action_returns_valid_token(self):
        planner = Planner()
        task = get_task("company_research")
        token = planner.next_action(task, self._obs())
        self.assertIn(token.action_type, list(ActionTokenType))

    def test_brain_high_arousal_inserts_wait_guard(self):
        planner = Planner()
        task = get_task("company_research")
        token = planner.next_action(task, self._obs(), brain_snapshot={"arousal": 0.9, "focus": 0.8})
        self.assertEqual(token.action_type, ActionTokenType.WAIT)

    def test_brain_low_focus_inserts_inspect_guard(self):
        planner = Planner()
        task = get_task("company_research")
        token = planner.next_action(task, self._obs(), brain_snapshot={"arousal": 0.1, "focus": 0.2})
        self.assertEqual(token.action_type, ActionTokenType.INSPECT_STATE)

    def test_planner_thresholds_are_configurable_via_env(self):
        with patch.dict(
            "os.environ",
            {
                "ELI_BRAIN_PLANNER_HIGH_AROUSAL_THRESHOLD": "0.5",
                "ELI_BRAIN_PLANNER_HIGH_AROUSAL_WAIT_SECONDS": "3",
            },
            clear=False,
        ):
            planner = Planner()
            task = get_task("company_research")
            token = planner.next_action(task, self._obs(), brain_snapshot={"arousal": 0.6, "focus": 0.9})
            self.assertEqual(token.action_type, ActionTokenType.WAIT)
            self.assertEqual(token.value, "3")


if __name__ == "__main__":
    unittest.main()
