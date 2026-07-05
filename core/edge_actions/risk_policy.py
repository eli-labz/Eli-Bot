from __future__ import annotations

from typing import Iterable

from .models import ActionToken, ActionTokenType, RiskDecision, TaskSpec


APPROVAL_KEYWORDS = {
    "send",
    "publish",
    "submit",
    "book",
    "purchase",
    "pay",
    "money",
    "bank",
    "payroll",
    "benefits",
    "retirement",
    "investment",
    "medical",
    "legal",
    "tax",
    "insurance",
    "government",
    "merge",
    "delete",
    "restart",
    "production",
    "irreversible",
    "external communication",
}


class RiskPolicy:
    def __init__(self, global_forbidden_actions: Iterable[str] | None = None):
        self.global_forbidden_actions = {a.upper() for a in (global_forbidden_actions or [])}

    def evaluate(self, task: TaskSpec, action: ActionToken) -> RiskDecision:
        action_name = action.action_type.value.upper()
        if action_name in self.global_forbidden_actions:
            return RiskDecision(False, False, "Blocked by global forbidden action policy.")

        if action_name in {a.upper() for a in task.forbidden_actions}:
            return RiskDecision(False, False, "Blocked by task forbidden actions.")

        if action_name in {a.upper() for a in task.approval_required_actions}:
            return RiskDecision(False, True, "Action requires explicit human approval.")

        payload = " ".join(
            x for x in [action.target or "", action.value or "", str(action.metadata)] if x
        ).lower()
        if any(k in payload for k in APPROVAL_KEYWORDS):
            return RiskDecision(False, True, "Detected high-risk keyword requiring approval.")

        return RiskDecision(True, False, "Allowed")

    def approval_token(self, reason: str) -> ActionToken:
        return ActionToken(action_type=ActionTokenType.ASK_HUMAN_APPROVAL, value=reason)
