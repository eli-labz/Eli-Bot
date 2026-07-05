import unittest

from core.edge_actions.models import ActionToken, ActionTokenType, Observation
from core.edge_actions.task_catalog import get_task
from core.edge_actions.verifier import Verifier


class VerifierTests(unittest.TestCase):
    def _obs(self, url: str, title: str):
        return Observation(
            url=url,
            title=title,
            visible_text="hello world",
            interactive_elements=[],
            downloads=[],
            active_tab=title,
            timestamp="2026-01-01T00:00:00",
            error_state=None,
        )

    def test_navigation_passes_on_url_change(self):
        verifier = Verifier()
        task = get_task("company_research")
        before = self._obs("https://a", "A")
        after = self._obs("https://b", "B")
        action = ActionToken(action_type=ActionTokenType.NAVIGATE, value="https://b")
        self.assertEqual(verifier.verify(task, action, before, after, "ok"), "pass")

    def test_verify_text_fails_when_not_found(self):
        verifier = Verifier()
        task = get_task("company_research")
        obs = self._obs("https://a", "A")
        action = ActionToken(action_type=ActionTokenType.VERIFY_TEXT, value="needle")
        self.assertEqual(verifier.verify(task, action, obs, obs, "not_found"), "fail")


if __name__ == "__main__":
    unittest.main()
