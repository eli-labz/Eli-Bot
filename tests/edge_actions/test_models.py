import unittest

from core.edge_actions.models import ActionToken, ActionTokenType


class ModelTests(unittest.TestCase):
    def test_action_token_enum(self):
        token = ActionToken(action_type=ActionTokenType.CLICK, target="button")
        self.assertEqual(token.action_type.value, "CLICK")

    def test_action_token_type_contains_required_actions(self):
        names = {a.value for a in ActionTokenType}
        required = {
            "CLICK",
            "TYPE",
            "SCROLL",
            "NAVIGATE",
            "WAIT",
            "SELECT",
            "UPLOAD",
            "DOWNLOAD",
            "COPY_TEXT",
            "OPEN_TAB",
            "CLOSE_TAB",
            "EXTRACT_TEXT",
            "VERIFY_TEXT",
            "VERIFY_DOWNLOAD",
            "ASK_HUMAN_APPROVAL",
            "STOP",
        }
        self.assertTrue(required.issubset(names))


if __name__ == "__main__":
    unittest.main()
