from __future__ import annotations

from urllib.parse import urlparse

from .models import ActionToken, ActionTokenType, ConsequenceAssessment, Observation, TaskSpec


HIGH_SEVERITY_TYPES = {ActionTokenType.UPLOAD, ActionTokenType.DOWNLOAD}


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().strip()
    except Exception:
        return ""


def _safe_text(value: str | None) -> str:
    return str(value or "").strip().lower()


class ConsequenceAnalyzer:
    """Assess whether an action outcome appears intended and suggest bounded recovery."""

    def assess(
        self,
        task: TaskSpec,
        action: ActionToken,
        before: Observation,
        after: Observation,
        execute_status: str,
        verification_status: str,
        error: str | None = None,
    ) -> ConsequenceAssessment:
        action_type = action.action_type

        if error:
            return ConsequenceAssessment(
                understood=True,
                severity="high",
                summary=f"Action raised an execution error: {error}",
                unintended=True,
                recommended_recovery="planner_recovery",
            )

        if after.error_state:
            return ConsequenceAssessment(
                understood=True,
                severity="high",
                summary=f"Page entered error state: {after.error_state}",
                unintended=True,
                recommended_recovery="planner_recovery",
            )

        before_host = _host(before.url)
        after_host = _host(after.url)
        host_changed = bool(before_host and after_host and before_host != after_host)

        if action_type == ActionTokenType.NAVIGATE:
            target = _safe_text(action.value or action.target)
            if target and target.startswith("http") and target not in _safe_text(after.url):
                return ConsequenceAssessment(
                    understood=True,
                    severity="high",
                    summary="Navigation landed on an unexpected URL.",
                    unintended=True,
                    recommended_recovery="revert_to_before_url",
                )
            return ConsequenceAssessment(True, "low", "Navigation outcome appears consistent.")

        if action_type == ActionTokenType.CLICK:
            if host_changed:
                return ConsequenceAssessment(
                    understood=True,
                    severity="medium",
                    summary="Click changed site host, likely unintended link/button activation.",
                    unintended=True,
                    recommended_recovery="revert_to_before_url",
                )
            if verification_status == "fail":
                return ConsequenceAssessment(
                    understood=True,
                    severity="medium",
                    summary="Click failed verification checks and may be wrong target.",
                    unintended=True,
                    recommended_recovery="planner_recovery",
                )
            return ConsequenceAssessment(True, "low", "Click outcome not obviously harmful.")

        if action_type in HIGH_SEVERITY_TYPES and verification_status in {"fail", "unknown"}:
            return ConsequenceAssessment(
                understood=True,
                severity="high",
                summary="High-impact action completed without strong verification.",
                unintended=True,
                recommended_recovery="planner_recovery",
            )

        if execute_status not in {"ok", "halt"}:
            return ConsequenceAssessment(
                understood=True,
                severity="medium",
                summary=f"Action returned non-ok status: {execute_status}",
                unintended=True,
                recommended_recovery="planner_recovery",
            )

        if verification_status == "fail":
            return ConsequenceAssessment(
                understood=True,
                severity="medium",
                summary="Verification failed; action likely diverged from intent.",
                unintended=True,
                recommended_recovery="planner_recovery",
            )

        # Default conservative interpretation.
        return ConsequenceAssessment(
            understood=True,
            severity="low",
            summary="No strong evidence of harmful unintended consequence.",
            unintended=False,
            recommended_recovery="none",
        )
