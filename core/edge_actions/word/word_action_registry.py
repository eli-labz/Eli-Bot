from __future__ import annotations

import re
from typing import Dict, List

from .word_action_tokens import HumanActionToken, WordActionVerb, WordRiskLevel


class WordActionRegistry:
    def __init__(self):
        self._catalog: Dict[str, Dict[str, object]] = self._build_catalog()

    def verbs(self) -> List[str]:
        return list(self._catalog.keys())

    def make_token(self, verb: str, target: str = "", args: Dict[str, object] | None = None) -> HumanActionToken:
        if verb not in self._catalog:
            raise KeyError(f"Unknown Word action verb: {verb}")

        spec = self._catalog[verb]
        merged_args = dict(args or {})

        return HumanActionToken(
            verb=verb,
            target=target,
            args=merged_args,
            preconditions=list(spec["preconditions"]),
            expected_outcome=str(spec["expected_outcome"]),
            cost=float(spec["cost"]),
            risk=str(spec["risk"]),
            requiresApproval=bool(spec["requiresApproval"]),
        )

    def propose_from_prompt(self, prompt: str) -> HumanActionToken:
        raw = str(prompt or "").strip()
        if raw.lower().startswith("winword "):
            raw = f"word {raw.split(' ', 1)[1]}"

        lowered = raw.lower()

        if lowered in {"word open", "word open word", "word start", "word start word", "word launch word"}:
            return self.make_token(WordActionVerb.OPEN_WORD.value, target="word")

        if lowered.startswith("word get state"):
            return self.make_token(WordActionVerb.GET_WORD_STATE.value, target="word")

        if lowered.startswith("word open "):
            path = raw.split(" ", 2)[2].strip() if len(raw.split(" ", 2)) >= 3 else ""
            return self.make_token(WordActionVerb.OPEN_DOCUMENT.value, target=path, args={"path": path})

        if lowered.startswith("word new") or lowered.startswith("word create document"):
            return self.make_token(WordActionVerb.CREATE_DOCUMENT.value, target="new_document")

        if lowered.startswith("word type "):
            text = raw.split(" ", 2)[2].strip() if len(raw.split(" ", 2)) >= 3 else ""
            return self.make_token(WordActionVerb.TYPE_TEXT.value, target="active_document", args={"text": text})

        if lowered.startswith("word find "):
            text = raw.split(" ", 2)[2].strip() if len(raw.split(" ", 2)) >= 3 else ""
            return self.make_token(WordActionVerb.FIND_TEXT.value, target="active_document", args={"text": text})

        if lowered.startswith("word replace ") and " -> " in raw:
            pair = raw.split(" ", 2)[2]
            old_text, new_text = pair.split(" -> ", 1)
            return self.make_token(
                WordActionVerb.REPLACE_TEXT.value,
                target="active_document",
                args={"old_text": old_text.strip(), "new_text": new_text.strip()},
            )

        if lowered.startswith("word heading "):
            text = raw.split(" ", 2)[2].strip() if len(raw.split(" ", 2)) >= 3 else ""
            return self.make_token(
                WordActionVerb.APPLY_STYLE.value,
                target="active_document",
                args={"style": "Heading 1", "text": text},
            )

        if lowered.startswith("word style "):
            style_name = raw.split(" ", 2)[2].strip() if len(raw.split(" ", 2)) >= 3 else "Normal"
            return self.make_token(
                WordActionVerb.APPLY_STYLE.value,
                target="active_document",
                args={"style": style_name},
            )

        if lowered == "word page break":
            return self.make_token(WordActionVerb.INSERT_PAGE_BREAK.value, target="active_document")

        if lowered.startswith("word insert table "):
            spec = raw.split(" ", 3)[3].strip() if len(raw.split(" ", 3)) >= 4 else ""
            match = re.match(r"^(\d+)\s*[x, ]\s*(\d+)$", spec)
            rows = int(match.group(1)) if match else 2
            cols = int(match.group(2)) if match else 2
            return self.make_token(
                WordActionVerb.INSERT_TABLE.value,
                target="active_document",
                args={"rows": rows, "cols": cols},
            )

        if lowered.startswith("word save as "):
            path = raw.split(" ", 3)[3].strip() if len(raw.split(" ", 3)) >= 4 else ""
            return self.make_token(WordActionVerb.SAVE_AS.value, target=path, args={"path": path})

        if lowered.startswith("word save"):
            return self.make_token(WordActionVerb.SAVE_DOCUMENT.value, target="active_document")

        if lowered.startswith("word export pdf "):
            path = raw.split(" ", 3)[3].strip() if len(raw.split(" ", 3)) >= 4 else ""
            return self.make_token(WordActionVerb.EXPORT_PDF.value, target=path, args={"path": path})

        if lowered.startswith("word close document"):
            return self.make_token(WordActionVerb.CLOSE_DOCUMENT.value, target="active_document")

        if lowered.startswith("word close"):
            return self.make_token(WordActionVerb.CLOSE_WORD.value, target="word")

        return self.make_token(
            WordActionVerb.ESCALATE_TO_HUMAN.value,
            target="word",
            args={"reason": "Prompt not mapped to safe Word verb", "prompt": raw},
        )

    def _build_catalog(self) -> Dict[str, Dict[str, object]]:
        return {
            WordActionVerb.OPEN_WORD.value: {
                "risk": WordRiskLevel.LOW.value,
                "requiresApproval": False,
                "preconditions": ["Windows desktop available"],
                "expected_outcome": "WORD_OPENED",
                "cost": 1.0,
            },
            WordActionVerb.OPEN_DOCUMENT.value: {
                "risk": WordRiskLevel.MEDIUM.value,
                "requiresApproval": False,
                "preconditions": ["Approved file path", "Word installed"],
                "expected_outcome": "DOCUMENT_OPENED",
                "cost": 1.5,
            },
            WordActionVerb.CREATE_DOCUMENT.value: {
                "risk": WordRiskLevel.LOW.value,
                "requiresApproval": False,
                "preconditions": ["Word installed"],
                "expected_outcome": "DOCUMENT_OPENED",
                "cost": 1.0,
            },
            WordActionVerb.TYPE_TEXT.value: {
                "risk": WordRiskLevel.LOW.value,
                "requiresApproval": False,
                "preconditions": ["Active document exists", "Selection available"],
                "expected_outcome": "TEXT_INSERTED",
                "cost": 1.0,
            },
            WordActionVerb.FIND_TEXT.value: {
                "risk": WordRiskLevel.MEDIUM.value,
                "requiresApproval": False,
                "preconditions": ["Active document exists"],
                "expected_outcome": "TASK_COMPLETE",
                "cost": 1.0,
            },
            WordActionVerb.REPLACE_TEXT.value: {
                "risk": WordRiskLevel.HIGH.value,
                "requiresApproval": True,
                "preconditions": ["Active document exists", "Explicit human approval"],
                "expected_outcome": "TASK_COMPLETE",
                "cost": 2.0,
            },
            WordActionVerb.APPLY_STYLE.value: {
                "risk": WordRiskLevel.MEDIUM.value,
                "requiresApproval": False,
                "preconditions": ["Active document exists", "Selection available"],
                "expected_outcome": "FORMAT_APPLIED",
                "cost": 1.0,
            },
            WordActionVerb.APPLY_FORMATTING.value: {
                "risk": WordRiskLevel.MEDIUM.value,
                "requiresApproval": False,
                "preconditions": ["Active document exists", "Selection available"],
                "expected_outcome": "FORMAT_APPLIED",
                "cost": 1.0,
            },
            WordActionVerb.INSERT_TABLE.value: {
                "risk": WordRiskLevel.MEDIUM.value,
                "requiresApproval": False,
                "preconditions": ["Active document exists"],
                "expected_outcome": "TASK_COMPLETE",
                "cost": 1.2,
            },
            WordActionVerb.INSERT_PAGE_BREAK.value: {
                "risk": WordRiskLevel.MEDIUM.value,
                "requiresApproval": False,
                "preconditions": ["Active document exists"],
                "expected_outcome": "TASK_COMPLETE",
                "cost": 1.0,
            },
            WordActionVerb.SAVE_DOCUMENT.value: {
                "risk": WordRiskLevel.MEDIUM.value,
                "requiresApproval": False,
                "preconditions": ["Active document exists"],
                "expected_outcome": "DOCUMENT_SAVED",
                "cost": 1.0,
            },
            WordActionVerb.SAVE_AS.value: {
                "risk": WordRiskLevel.MEDIUM.value,
                "requiresApproval": True,
                "preconditions": ["Approved output path", "Active document exists"],
                "expected_outcome": "DOCUMENT_SAVED",
                "cost": 1.5,
            },
            WordActionVerb.EXPORT_PDF.value: {
                "risk": WordRiskLevel.HIGH.value,
                "requiresApproval": True,
                "preconditions": ["Approved output path", "Explicit human approval"],
                "expected_outcome": "PDF_EXPORTED",
                "cost": 2.0,
            },
            WordActionVerb.CLOSE_DOCUMENT.value: {
                "risk": WordRiskLevel.HIGH.value,
                "requiresApproval": True,
                "preconditions": ["Document saved or explicit approval"],
                "expected_outcome": "TASK_COMPLETE",
                "cost": 1.0,
            },
            WordActionVerb.CLOSE_WORD.value: {
                "risk": WordRiskLevel.HIGH.value,
                "requiresApproval": True,
                "preconditions": ["Document saved or explicit approval"],
                "expected_outcome": "TASK_COMPLETE",
                "cost": 1.0,
            },
            WordActionVerb.GET_WORD_STATE.value: {
                "risk": WordRiskLevel.LOW.value,
                "requiresApproval": False,
                "preconditions": ["Word process may or may not be running"],
                "expected_outcome": "TASK_COMPLETE",
                "cost": 0.5,
            },
            WordActionVerb.VERIFY_DOCUMENT_STATE.value: {
                "risk": WordRiskLevel.LOW.value,
                "requiresApproval": False,
                "preconditions": ["State snapshot available"],
                "expected_outcome": "TASK_COMPLETE",
                "cost": 0.5,
            },
            WordActionVerb.ESCALATE_TO_HUMAN.value: {
                "risk": WordRiskLevel.LOW.value,
                "requiresApproval": False,
                "preconditions": ["Human channel available"],
                "expected_outcome": "TASK_ESCALATED",
                "cost": 0.2,
            },
        }
