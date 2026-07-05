import unittest

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


if __name__ == "__main__":
    unittest.main()
