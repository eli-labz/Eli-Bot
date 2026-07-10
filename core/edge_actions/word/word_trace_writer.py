from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Dict, List

from .word_action_tokens import HumanActionToken, WordExecutionResult, WordState


class WordTraceWriter:
    def __init__(self, trace_dir: Path, memory_file: Path | None = None):
        self.trace_dir = trace_dir
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = memory_file or (trace_dir / "word_reusable_memory.jsonl")
        self.events: List[Dict[str, Any]] = []

    def write_audit_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self.events.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "event_type": event_type,
                "payload": payload,
            }
        )

    def write_action_event(
        self,
        token: HumanActionToken,
        policy_decision: Dict[str, Any],
        before: WordState,
        after: WordState,
        result: WordExecutionResult,
        verification_status: str,
    ) -> None:
        self.write_audit_event(
            "word_action",
            {
                "token": asdict(token),
                "policy_decision": policy_decision,
                "before": asdict(before),
                "after": asdict(after),
                "result": {
                    "status": result.status,
                    "message": result.message,
                    "error": result.error,
                    "outcome_tokens": [t.value for t in result.outcome_tokens],
                },
                "verification_status": verification_status,
            },
        )

    def persist_trace(self, task_id: str, status: str) -> Path:
        output = {
            "task_id": task_id,
            "status": status,
            "events": self.events,
        }
        out_path = self.trace_dir / f"word_{task_id}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
        out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
        return out_path

    def write_reusable_memory(self, payload: Dict[str, Any]) -> None:
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        with self.memory_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")
