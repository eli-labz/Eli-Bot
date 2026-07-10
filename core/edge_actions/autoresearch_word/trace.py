from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Dict

from .models import WordActionRequest, WordActionResult


class WordTraceLogger:
    def __init__(self, trace_dir: Path):
        self.trace_dir = trace_dir
        self.trace_dir.mkdir(parents=True, exist_ok=True)

    def write(self, request: WordActionRequest, result: WordActionResult, extra: Dict[str, Any] | None = None) -> Path:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "request": asdict(request),
            "result": asdict(result),
            "extra": extra or {},
        }
        out_path = self.trace_dir / f"autoresearch_word_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return out_path
