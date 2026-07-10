from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Dict

from .models import ActionToken, ActionTokenType, Observation, TaskSpec


@dataclass
class PlannerState:
    step_index: int = 0
    retries: int = 0
    cognitive_guard_uses: int = 0


class Planner:
    def __init__(self):
        self.state: Dict[str, PlannerState] = {}
        self.brain_guards_enabled = self._read_bool_env("ELI_BRAIN_PLANNER_GUARDS_ENABLED", True)
        self.max_cognitive_guards = self._read_int_env("ELI_BRAIN_PLANNER_MAX_COGNITIVE_GUARDS", 2, 0, 10)
        self.high_arousal_threshold = self._read_float_env("ELI_BRAIN_PLANNER_HIGH_AROUSAL_THRESHOLD", 0.65, 0.0, 1.0)
        self.low_focus_threshold = self._read_float_env("ELI_BRAIN_PLANNER_LOW_FOCUS_THRESHOLD", 0.35, 0.0, 1.0)
        self.high_arousal_wait_seconds = self._read_int_env(
            "ELI_BRAIN_PLANNER_HIGH_AROUSAL_WAIT_SECONDS",
            1,
            1,
            30,
        )

    def _read_bool_env(self, key: str, default: bool) -> bool:
        raw = str(os.environ.get(key, "1" if default else "0")).strip().lower()
        return raw in {"1", "true", "yes", "on"}

    def _read_float_env(self, key: str, default: float, min_value: float, max_value: float) -> float:
        raw = str(os.environ.get(key, str(default))).strip()
        try:
            parsed = float(raw)
        except Exception:
            parsed = default
        return max(min_value, min(max_value, parsed))

    def _read_int_env(self, key: str, default: int, min_value: int, max_value: int) -> int:
        raw = str(os.environ.get(key, str(default))).strip()
        try:
            parsed = int(raw)
        except Exception:
            parsed = default
        return max(min_value, min(max_value, parsed))

    def next_action(self, task: TaskSpec, observation: Observation, brain_snapshot: dict | None = None) -> ActionToken:
        state = self.state.setdefault(task.id, PlannerState())

        if self.brain_guards_enabled and brain_snapshot and state.cognitive_guard_uses < self.max_cognitive_guards:
            arousal = float(brain_snapshot.get("arousal", 0.0))
            focus = float(brain_snapshot.get("focus", 1.0))
            if arousal > self.high_arousal_threshold:
                state.cognitive_guard_uses += 1
                return ActionToken(
                    action_type=ActionTokenType.WAIT,
                    value=str(self.high_arousal_wait_seconds),
                    metadata={"cognitive_guard": "high_arousal", "title": observation.title},
                )
            if focus < self.low_focus_threshold:
                state.cognitive_guard_uses += 1
                return ActionToken(
                    action_type=ActionTokenType.INSPECT_STATE,
                    value="pre_action_state_check",
                    metadata={"cognitive_guard": "low_focus", "title": observation.title},
                )

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
