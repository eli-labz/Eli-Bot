from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .models import ActionToken, ActionTokenType, Observation, TaskSpec


@dataclass
class PlannerState:
    step_index: int = 0
    retries: int = 0


class Planner:
    def __init__(self):
        self.state: Dict[str, PlannerState] = {}

    def next_action(self, task: TaskSpec, observation: Observation) -> ActionToken:
        state = self.state.setdefault(task.id, PlannerState())

        if state.step_index >= len(task.example_steps):
            return ActionToken(action_type=ActionTokenType.STOP, value="Task steps exhausted")

        raw = task.example_steps[state.step_index]
        state.step_index += 1

        action_name = str(raw.get("action", "INSPECT_STATE")).upper()
        try:
            action_type = ActionTokenType[action_name]
        except KeyError:
            action_type = ActionTokenType.INSPECT_STATE

        return ActionToken(
            action_type=action_type,
            target=raw.get("target"),
            value=raw.get("value"),
            selector=raw.get("selector"),
            timeout_seconds=int(raw.get("timeout_seconds", 15)),
            metadata={"planner_step": state.step_index, "title": observation.title},
        )

    def recovery_action(self, error: str) -> ActionToken:
        return ActionToken(
            action_type=ActionTokenType.WAIT,
            value="2",
            metadata={"recovery": True, "error": error},
        )
