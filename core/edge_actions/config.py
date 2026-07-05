from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _is_true(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class EdgeActionsConfig:
    enabled: bool
    headless: bool
    edge_channel: str
    max_steps: int
    trace_dir: Path


    @staticmethod
    def from_env() -> "EdgeActionsConfig":
        trace_dir = Path(os.environ.get("ELI_EDGE_ACTIONS_TRACE_DIR", "edge_action_traces"))
        return EdgeActionsConfig(
            enabled=_is_true(os.environ.get("ELI_EDGE_ACTIONS_ENABLED", "false")),
            headless=_is_true(os.environ.get("ELI_EDGE_ACTIONS_HEADLESS", "false")),
            edge_channel=os.environ.get("ELI_EDGE_ACTIONS_CHANNEL", "msedge"),
            max_steps=int(os.environ.get("ELI_EDGE_ACTIONS_MAX_STEPS", "40")),
            trace_dir=trace_dir,
        )


def edge_actions_enabled() -> bool:
    return EdgeActionsConfig.from_env().enabled
