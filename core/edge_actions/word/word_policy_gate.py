from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from .word_action_tokens import HumanActionToken, WordActionVerb, WordRiskLevel, WordState


HIGH_RISK_VERBS = {
    WordActionVerb.REPLACE_TEXT.value,
    WordActionVerb.EXPORT_PDF.value,
    WordActionVerb.CLOSE_DOCUMENT.value,
    WordActionVerb.CLOSE_WORD.value,
}

MEDIUM_RISK_VERBS = {
    WordActionVerb.SAVE_DOCUMENT.value,
    WordActionVerb.SAVE_AS.value,
    WordActionVerb.FIND_TEXT.value,
    WordActionVerb.INSERT_TABLE.value,
    WordActionVerb.APPLY_FORMATTING.value,
    WordActionVerb.APPLY_STYLE.value,
}

LOW_RISK_VERBS = {
    WordActionVerb.GET_WORD_STATE.value,
    WordActionVerb.OPEN_WORD.value,
    WordActionVerb.CREATE_DOCUMENT.value,
    WordActionVerb.TYPE_TEXT.value,
}


@dataclass
class WordPolicyDecision:
    allowed: bool
    requires_approval: bool
    reason: str
    escalate: bool = False


class WordPolicyGate:
    def __init__(
        self,
        approved_dirs: Optional[Iterable[str]] = None,
        approved_output_dir: Optional[str] = None,
        approval_callback: Optional[Callable[[HumanActionToken, str], bool]] = None,
        confidence_threshold: float = 0.65,
    ):
        self.approval_callback = approval_callback
        self.confidence_threshold = confidence_threshold
        self.approved_dirs = self._build_approved_dirs(approved_dirs)
        self.approved_output_dir = Path(approved_output_dir).resolve() if approved_output_dir else None

    def evaluate(self, token: HumanActionToken, state: WordState) -> WordPolicyDecision:
        if not token.preconditions:
            return WordPolicyDecision(False, False, "Missing preconditions.", escalate=True)
        if not token.expected_outcome:
            return WordPolicyDecision(False, False, "Missing expected_outcome.", escalate=True)

        confidence = float(token.args.get("confidence", 1.0))
        if confidence < self.confidence_threshold:
            return WordPolicyDecision(False, False, "Low confidence. Escalating to human.", escalate=True)

        if bool(token.args.get("run_macro", False)):
            return WordPolicyDecision(False, False, "Macros are blocked by default.", escalate=True)

        if bool(token.args.get("external_share", False)):
            return WordPolicyDecision(False, False, "External sharing is blocked by default.", escalate=True)

        if token.verb in {
            WordActionVerb.OPEN_DOCUMENT.value,
            WordActionVerb.SAVE_DOCUMENT.value,
            WordActionVerb.SAVE_AS.value,
            WordActionVerb.EXPORT_PDF.value,
        }:
            path = str(token.args.get("path") or token.target or "").strip()
            if not self._is_path_approved(path, is_export=(token.verb == WordActionVerb.EXPORT_PDF.value)):
                return WordPolicyDecision(False, False, "Path not in approved allowlist.", escalate=True)

        risk = str(token.risk or "").lower()
        if token.verb in HIGH_RISK_VERBS:
            risk = WordRiskLevel.HIGH.value
        elif token.verb in MEDIUM_RISK_VERBS and risk not in {WordRiskLevel.HIGH.value}:
            risk = WordRiskLevel.MEDIUM.value
        elif token.verb in LOW_RISK_VERBS and risk not in {WordRiskLevel.MEDIUM.value, WordRiskLevel.HIGH.value}:
            risk = WordRiskLevel.LOW.value

        if token.verb in {WordActionVerb.CLOSE_DOCUMENT.value, WordActionVerb.CLOSE_WORD.value} and state.is_saved is False:
            return self._approval_decision(token, "Document has unsaved changes.")

        if token.verb in {
            WordActionVerb.REPLACE_TEXT.value,
            WordActionVerb.EXPORT_PDF.value,
            WordActionVerb.CLOSE_DOCUMENT.value,
            WordActionVerb.CLOSE_WORD.value,
            WordActionVerb.SAVE_AS.value,
        }:
            return self._approval_decision(token, "High-impact Word action requires explicit approval.")

        if token.requiresApproval or risk == WordRiskLevel.HIGH.value:
            return self._approval_decision(token, "Action is policy-gated by risk level.")

        return WordPolicyDecision(True, False, "Allowed by Word policy.")

    def _approval_decision(self, token: HumanActionToken, reason: str) -> WordPolicyDecision:
        explicit_approval = bool(token.args.get("approved", False))
        if explicit_approval:
            return WordPolicyDecision(True, False, f"Approved: {reason}")

        if self.approval_callback is not None:
            approved = bool(self.approval_callback(token, reason))
            if approved:
                return WordPolicyDecision(True, False, f"Human approved: {reason}")

        return WordPolicyDecision(False, True, reason, escalate=False)

    def _build_approved_dirs(self, approved_dirs: Optional[Iterable[str]]) -> List[Path]:
        if approved_dirs:
            values = list(approved_dirs)
        else:
            env_value = os.environ.get("ELI_WORD_ALLOWED_DIRS", "")
            values = [x for x in env_value.split(";") if x.strip()]

        normalized: List[Path] = []
        for item in values:
            raw = str(item).strip()
            if not raw:
                continue
            try:
                normalized.append(Path(raw).expanduser().resolve())
            except Exception:
                continue
        return normalized

    def _is_path_approved(self, path: str, is_export: bool = False) -> bool:
        if not path:
            return False

        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve()
        else:
            candidate = candidate.resolve()

        if is_export and self.approved_output_dir is not None:
            try:
                candidate.relative_to(self.approved_output_dir)
                return True
            except Exception:
                return False

        if not self.approved_dirs:
            return False

        for approved_dir in self.approved_dirs:
            try:
                candidate.relative_to(approved_dir)
                return True
            except Exception:
                continue
        return False
