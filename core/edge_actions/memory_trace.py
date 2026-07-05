from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Dict, List

from .models import ExecutionResult, Observation, TaskSpec


class MemoryTrace:
    def __init__(self, trace_dir: Path):
        self.trace_dir = trace_dir
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.events: List[Dict[str, Any]] = []

    def add_event(self, event: Dict[str, Any]) -> None:
        event["timestamp"] = datetime.now(UTC).isoformat()
        self.events.append(event)

    def add_result(self, result: ExecutionResult) -> None:
        self.add_event({"type": "execution_result", "payload": asdict(result)})

    def add_observation(self, label: str, observation: Observation) -> None:
        self.add_event({"type": "observation", "label": label, "payload": asdict(observation)})

    def finalize(self, task: TaskSpec, status: str) -> Path:
        output = {
            "task_id": task.id,
            "task_name": task.name,
            "status": status,
            "events": self.events,
        }
        out_path = self.trace_dir / f"{task.id}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
        out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
        return out_path
