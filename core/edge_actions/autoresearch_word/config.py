from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _is_true(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AutoresearchWordConfig:
    enabled: bool
    trace_dir: Path
    approved_input_dirs: tuple[Path, ...]
    approved_output_dir: Path | None
    allow_external_paths: bool

    @staticmethod
    def from_env() -> "AutoresearchWordConfig":
        dirs_raw = str(os.environ.get("ELI_WORD_ALLOWED_DIRS", "")).strip()
        approved_dirs = tuple(
            Path(item.strip()).expanduser().resolve()
            for item in dirs_raw.split(";")
            if item.strip()
        )

        output_raw = str(os.environ.get("ELI_WORD_APPROVED_OUTPUT_DIR", "")).strip()
        approved_output_dir = Path(output_raw).expanduser().resolve() if output_raw else None

        return AutoresearchWordConfig(
            enabled=_is_true(os.environ.get("ENABLE_AUTORESEARCH_WORD", "false")),
            trace_dir=Path(os.environ.get("ELI_WORD_TRACE_DIR", "edge_action_traces/word")),
            approved_input_dirs=approved_dirs,
            approved_output_dir=approved_output_dir,
            allow_external_paths=_is_true(os.environ.get("ELI_WORD_ALLOW_EXTERNAL_PATHS", "false")),
        )


def autoresearch_word_enabled() -> bool:
    return AutoresearchWordConfig.from_env().enabled
