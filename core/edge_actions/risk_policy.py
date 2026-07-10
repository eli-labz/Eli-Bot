from __future__ import annotations

import os
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

HIGH_IMPACT_ACTIONS = {
    "TYPE",
    "CLICK",
    "UPLOAD",
    "DOWNLOAD",
    "NAVIGATE",
}


class RiskPolicy:
    def __init__(self, global_forbidden_actions: Iterable[str] | None = None):
        self.global_forbidden_actions = {a.upper() for a in (global_forbidden_actions or [])}
        self.brain_policy_enabled = self._read_bool_env("ELI_BRAIN_RISK_POLICY_ENABLED", True)
        self.high_arousal_threshold = self._read_float_env("ELI_BRAIN_RISK_HIGH_AROUSAL_THRESHOLD", 0.7, 0.0, 1.0)
        self.low_focus_threshold = self._read_float_env("ELI_BRAIN_RISK_LOW_FOCUS_THRESHOLD", 0.3, 0.0, 1.0)
        self.high_risk_negative_valence_threshold = self._read_float_env(
            "ELI_BRAIN_RISK_HIGH_TASK_NEGATIVE_VALENCE_THRESHOLD",
            -0.35,
            -1.0,
            1.0,
        )
        configured_actions = str(os.environ.get("ELI_BRAIN_RISK_HIGH_IMPACT_ACTIONS", "")).strip()
        if configured_actions:
            parsed_actions = {x.strip().upper() for x in configured_actions.split(",") if x.strip()}
            self.high_impact_actions = parsed_actions if parsed_actions else set(HIGH_IMPACT_ACTIONS)
        else:
            self.high_impact_actions = set(HIGH_IMPACT_ACTIONS)

    def _read_bool_env(self, key: str, default: bool) -> bool:
        raw = str(os.environ.get(key, "1" if default else "0")).strip().lower()
        return raw in {"1", "true", "yes", "on"}

    def _read_float_env(self, key: str, default: float, min_value: float, max_value: float) -> float:
        raw = str(os.environ.get(key, str(default))).strip()
        try:
            parsed = float(raw)
        except Exception:
            parsed = default
        return max(min_value, min(max_value, parsed))

    def evaluate(self, task: TaskSpec, action: ActionToken, brain_snapshot: dict | None = None) -> RiskDecision:
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

        if self.brain_policy_enabled and brain_snapshot:
            arousal = float(brain_snapshot.get("arousal", 0.0))
            focus = float(brain_snapshot.get("focus", 1.0))
            valence = float(brain_snapshot.get("valence", 0.0))
            if action_name in self.high_impact_actions and (
                arousal > self.high_arousal_threshold
                or focus < self.low_focus_threshold
                or (task.risk_level.lower() == "high" and valence < self.high_risk_negative_valence_threshold)
            ):
                return RiskDecision(
                    False,
                    True,
                    "Brain-state policy: high-impact action requires approval under current cognitive state.",
                )

        return RiskDecision(True, False, "Allowed")

    def approval_token(self, reason: str) -> ActionToken:
        return ActionToken(action_type=ActionTokenType.ASK_HUMAN_APPROVAL, value=reason)
