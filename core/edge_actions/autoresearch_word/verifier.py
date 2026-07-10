from __future__ import annotations

from .models import WordActionRequest, WordActionResult


class WordActionVerifier:
    def verify(self, request: WordActionRequest, result: WordActionResult) -> str:
        if result.status in {"blocked", "error"}:
            return "fail"
        if result.status in {"ok", "completed"}:
            return "pass"
        return "unknown"
