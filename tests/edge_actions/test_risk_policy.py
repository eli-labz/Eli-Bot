import unittest
from unittest.mock import patch

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

    def test_brain_state_escalates_high_impact_action(self):
        task = get_task("company_research")
        policy = RiskPolicy()
        decision = policy.evaluate(
            task,
            ActionToken(action_type=ActionTokenType.CLICK, target="confirm"),
            brain_snapshot={"arousal": 0.8, "focus": 0.9, "valence": 0.0},
        )
        self.assertTrue(decision.requires_approval)

    def test_risk_brain_thresholds_are_configurable_via_env(self):
        task = get_task("company_research")
        with patch.dict(
            "os.environ",
            {
                "ELI_BRAIN_RISK_HIGH_AROUSAL_THRESHOLD": "0.95",
                "ELI_BRAIN_RISK_LOW_FOCUS_THRESHOLD": "0.05",
            },
            clear=False,
        ):
            policy = RiskPolicy()
            decision = policy.evaluate(
                task,
                ActionToken(action_type=ActionTokenType.CLICK, target="confirm"),
                brain_snapshot={"arousal": 0.8, "focus": 0.9, "valence": 0.0},
            )
            self.assertTrue(decision.allowed)
            self.assertFalse(decision.requires_approval)


if __name__ == "__main__":
    unittest.main()
