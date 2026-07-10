import unittest

from core.edge_actions.consequence import ConsequenceAnalyzer
from core.edge_actions.models import ActionToken, ActionTokenType, Observation
from core.edge_actions.task_catalog import get_task


class ConsequenceAnalyzerTests(unittest.TestCase):
    def _obs(self, url: str, title: str):
        return Observation(
            url=url,
            title=title,
            visible_text="body text",
            interactive_elements=[],
            downloads=[],
            active_tab=title,
            timestamp="2026-01-01T00:00:00",
            error_state=None,
        )

    def test_click_cross_host_detected_as_unintended(self):
        analyzer = ConsequenceAnalyzer()
        task = get_task("company_research")
        before = self._obs("https://example.com/home", "Home")
        after = self._obs("https://evil.example.org/phish", "Phish")
        action = ActionToken(action_type=ActionTokenType.CLICK, target="login")

        assessment = analyzer.assess(task, action, before, after, "ok", "unknown", error=None)

        self.assertTrue(assessment.unintended)
        self.assertEqual("revert_to_before_url", assessment.recommended_recovery)

    def test_verify_fail_marks_unintended(self):
        analyzer = ConsequenceAnalyzer()
        task = get_task("company_research")
        before = self._obs("https://example.com", "A")
        after = self._obs("https://example.com", "A")
        action = ActionToken(action_type=ActionTokenType.TYPE, value="hello")

        assessment = analyzer.assess(task, action, before, after, "ok", "fail", error=None)

        self.assertTrue(assessment.unintended)
        self.assertEqual("medium", assessment.severity)


if __name__ == "__main__":
    unittest.main()
