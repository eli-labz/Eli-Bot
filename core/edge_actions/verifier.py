from __future__ import annotations

from .models import ActionToken, ActionTokenType, Observation, TaskSpec


class Verifier:
    def verify(self, task: TaskSpec, action: ActionToken, before: Observation, after: Observation, execute_status: str) -> str:
        if execute_status == "halt":
            return "halted"

        if action.action_type == ActionTokenType.NAVIGATE:
            return "pass" if after.url != before.url else "fail"
        if action.action_type == ActionTokenType.CLICK:
            if after.title != before.title or after.url != before.url:
                return "pass"
            return "unknown"
        if action.action_type == ActionTokenType.TYPE:
            return "pass"
        if action.action_type == ActionTokenType.VERIFY_TEXT:
            return "pass" if execute_status == "ok" else "fail"
        if action.action_type == ActionTokenType.VERIFY_DOWNLOAD:
            return "pass" if execute_status == "ok" else "unknown"
        if action.action_type == ActionTokenType.STOP:
            return "pass"

        # Generic bounded heuristic.
        if before.url != after.url or before.title != after.title:
            return "pass"
        return "unknown"
