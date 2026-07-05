import unittest

from core.edge_actions.action_executor import ActionExecutor
from core.edge_actions.models import ActionToken, ActionTokenType


class _FakeLocator:
    def __init__(self):
        self.first = self

    def click(self, timeout=None):
        return None

    def fill(self, value):
        return None

    def select_option(self, label=None):
        return None

    def inner_text(self, timeout=None):
        return "body text"


class _FakeKeyboard:
    def type(self, value):
        return None


class _FakeMouse:
    def wheel(self, x, y):
        return None


class _FakeContext:
    def __init__(self):
        self.headers = {}

    def new_page(self):
        return None

    def set_extra_http_headers(self, headers):
        self.headers.update(headers)


class _FakePage:
    def __init__(self):
        self.context = _FakeContext()
        self.keyboard = _FakeKeyboard()
        self.mouse = _FakeMouse()

    def goto(self, url, wait_until=None):
        return None

    def locator(self, selector):
        return _FakeLocator()

    def get_by_text(self, text, exact=False):
        return _FakeLocator()

    def close(self):
        return None

    def title(self):
        return "Fake"


class ActionExecutorTests(unittest.TestCase):
    def test_executor_click(self):
        execu = ActionExecutor(_FakePage())
        result = execu.execute(ActionToken(action_type=ActionTokenType.CLICK, target="Go"))
        self.assertEqual(result, "ok")

    def test_executor_extract(self):
        execu = ActionExecutor(_FakePage())
        result = execu.execute(ActionToken(action_type=ActionTokenType.EXTRACT_TEXT, selector="body"))
        self.assertIn("body", result)


if __name__ == "__main__":
    unittest.main()
