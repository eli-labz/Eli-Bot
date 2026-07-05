import unittest

from core.edge_actions.models import ActionToken, ActionTokenType
from core.edge_actions.risk_policy import RiskPolicy
from core.edge_actions.task_catalog import get_task


class RiskPolicyTests(unittest.TestCase):
    def test_blocks_forbidden_action(self):
        task = get_task("company_research")
        policy = RiskPolicy(global_forbidden_actions=["CLICK"])
        decision = policy.evaluate(task, ActionToken(action_type=ActionTokenType.CLICK, target="x"))
        self.assertFalse(decision.allowed)

    def test_requires_approval_for_risky_payload(self):
        task = get_task("company_research")
        policy = RiskPolicy()
        decision = policy.evaluate(task, ActionToken(action_type=ActionTokenType.TYPE, value="submit tax form"))
        self.assertTrue(decision.requires_approval)


if __name__ == "__main__":
    unittest.main()
