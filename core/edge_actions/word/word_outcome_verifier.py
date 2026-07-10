from __future__ import annotations

from .word_action_tokens import HumanActionToken, WordActionVerb, WordExecutionResult, WordState


class WordOutcomeVerifier:
    def verify(
        self,
        token: HumanActionToken,
        before: WordState,
        after: WordState,
        result: WordExecutionResult,
    ) -> str:
        if result.status in {"blocked", "escalated"}:
            return "pass"

        if result.status != "ok":
            return "fail"

        verb = token.verb

        if verb == WordActionVerb.OPEN_WORD.value:
            return "pass" if after.is_running else "fail"

        if verb in {WordActionVerb.OPEN_DOCUMENT.value, WordActionVerb.CREATE_DOCUMENT.value}:
            return "pass" if after.document_path is not None or after.is_running else "unknown"

        if verb == WordActionVerb.SAVE_DOCUMENT.value:
            return "pass" if after.is_saved is True else "unknown"

        if verb == WordActionVerb.EXPORT_PDF.value:
            return "pass" if "PDF_EXPORTED" in {t.value for t in result.outcome_tokens} else "unknown"

        if verb in {
            WordActionVerb.TYPE_TEXT.value,
            WordActionVerb.APPLY_STYLE.value,
            WordActionVerb.APPLY_FORMATTING.value,
            WordActionVerb.FIND_TEXT.value,
            WordActionVerb.REPLACE_TEXT.value,
            WordActionVerb.INSERT_TABLE.value,
            WordActionVerb.INSERT_PAGE_BREAK.value,
            WordActionVerb.SAVE_AS.value,
            WordActionVerb.CLOSE_DOCUMENT.value,
            WordActionVerb.CLOSE_WORD.value,
            WordActionVerb.GET_WORD_STATE.value,
            WordActionVerb.VERIFY_DOCUMENT_STATE.value,
        }:
            return "pass"

        return "unknown"
