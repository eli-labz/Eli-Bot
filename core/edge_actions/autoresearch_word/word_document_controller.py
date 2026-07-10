from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .models import WordActionRequest, WordActionResult


class WordDocumentController:
    def __init__(self, word_project_dir: Path | None = None, workflow_engine: Any = None):
        self.word_project_dir = word_project_dir or (
            Path(__file__).resolve().parent.parent.parent / "office" / "word" / "WordDocument"
        )
        self.workflow_engine = workflow_engine

    def detect_availability(self) -> WordActionResult:
        project_file = self.word_project_dir / "WordDocument.csproj"
        if not self.word_project_dir.exists() or not project_file.exists():
            return WordActionResult(
                status="error",
                action="detect_availability",
                message="WordDocument module is unavailable.",
                payload={"word_project_dir": str(self.word_project_dir)},
            )
        return WordActionResult(
            status="ok",
            action="detect_availability",
            message="WordDocument module detected.",
            payload={"word_project_dir": str(self.word_project_dir)},
        )

    def execute(self, request: WordActionRequest) -> WordActionResult:
        availability = self.detect_availability()
        if availability.status != "ok":
            return availability

        prompt = self._to_prompt(request)
        if not prompt:
            return WordActionResult(status="error", action=request.action, message="Unsupported Word action.")

        engine = self._get_engine()
        if engine is None:
            return WordActionResult(
                status="error",
                action=request.action,
                message="Word workflow engine unavailable.",
            )

        try:
            result = engine.run_prompt(prompt)
        except Exception as e:
            return WordActionResult(status="error", action=request.action, message=f"Word execution failed: {e}")

        status = str(result.get("status", "unknown"))
        mapped_status = "ok" if status in {"completed", "ok"} else status
        return WordActionResult(
            status=mapped_status,
            action=request.action,
            message=str(result.get("message", status)),
            payload=result,
        )

    def _get_engine(self) -> Optional[Any]:
        if self.workflow_engine is not None:
            return self.workflow_engine

        try:
            from core.edge_actions.word import WordWorkflowEngine

            self.workflow_engine = WordWorkflowEngine()
            return self.workflow_engine
        except Exception:
            return None

    def _to_prompt(self, request: WordActionRequest) -> str:
        if request.action == "create_document":
            return "word create document"
        if request.action == "open_document" and request.path:
            return f"word open {request.path}"
        if request.action in {"insert_text", "append_research_output"}:
            return f"word type {request.text}"
        if request.action == "apply_heading":
            return f"word heading {request.text}" if request.text else "word style Heading 1"
        if request.action == "save_document":
            return "word save"
        if request.action == "save_as" and request.path:
            return f"word save as {request.path}"
        if request.action == "export_pdf" and request.path:
            return f"word export pdf {request.path}"
        if request.action == "close_document":
            return "word close"
        if request.action == "detect_availability":
            return "word get state"
        return ""
