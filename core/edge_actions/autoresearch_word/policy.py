from __future__ import annotations

from pathlib import Path

from .config import AutoresearchWordConfig
from .models import WordActionRequest


class WordActionPolicy:
    def __init__(self, config: AutoresearchWordConfig):
        self.config = config

    def evaluate(self, request: WordActionRequest, has_unsaved_changes: bool = False) -> tuple[bool, str]:
        action = request.action

        if request.metadata.get("run_macro", False):
            return False, "Macro execution is blocked by default."

        if request.metadata.get("external_share", False):
            return False, "Silent external sharing is blocked by default."

        if action in {"open_document", "save_as", "export_pdf"}:
            if not request.path:
                return False, "Missing file path."
            approved, reason = self._check_path(request.path, action)
            if not approved:
                return False, reason

        if action == "export_pdf" and not request.approved:
            return False, "Export to PDF requires explicit approval."

        if action == "close_document" and has_unsaved_changes and not request.approved:
            return False, "Closing unsaved document requires explicit approval."

        if action == "save_as" and request.metadata.get("overwrite", False) and not request.approved:
            return False, "Overwrite requires explicit approval."

        return True, "Allowed"

    def _check_path(self, raw_path: str, action: str) -> tuple[bool, str]:
        path = Path(raw_path).expanduser()
        path = path.resolve() if path.is_absolute() else (Path.cwd() / path).resolve()

        if action == "open_document" and path.suffix.lower() != ".docx":
            return False, "Only .docx files are supported for open_document."

        if action == "export_pdf" and path.suffix.lower() != ".pdf":
            return False, "Only .pdf extension is supported for export_pdf."

        if self.config.allow_external_paths:
            return True, "Allowed"

        if action in {"save_as", "export_pdf"} and self.config.approved_output_dir is not None:
            try:
                path.relative_to(self.config.approved_output_dir)
                return True, "Allowed"
            except Exception:
                return False, "Path is outside approved output directory."

        if not self.config.approved_input_dirs:
            return False, "Path allowlist is empty; configure ELI_WORD_ALLOWED_DIRS."

        for approved_dir in self.config.approved_input_dirs:
            try:
                path.relative_to(approved_dir)
                return True, "Allowed"
            except Exception:
                continue

        return False, "Path is outside approved allowlist."
