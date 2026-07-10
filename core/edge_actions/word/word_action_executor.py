from __future__ import annotations

import os
import time
import subprocess
from pathlib import Path
from typing import Any, Optional

import psutil

from .word_action_tokens import HumanActionToken, WordActionVerb, WordExecutionResult, WordOutcomeToken


class WordComProvider:
    def __init__(self, com_client: Any = None):
        self.com_client = com_client

    def get_app(self):
        if self.com_client is not None:
            return self.com_client

        try:
            import win32com.client  # type: ignore

            return win32com.client.GetActiveObject("Word.Application")
        except Exception:
            return None

    def ensure_app(self):
        app = self.get_app()
        if app is not None:
            return app

        subprocess.Popen(["cmd", "/c", "start", "", "winword"], shell=False)
        # Word COM can lag behind process startup; wait briefly and retry attach.
        deadline = time.time() + 4.0
        while time.time() < deadline:
            app = self.get_app()
            if app is not None:
                return app
            time.sleep(0.2)
        return None

    def is_word_running(self) -> bool:
        for proc in psutil.process_iter(["name"]):
            try:
                name = str(proc.info.get("name") or "").upper()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if name == "WINWORD.EXE":
                return True
        return False


class WordActionExecutor:
    def __init__(self, provider: Optional[WordComProvider] = None):
        self.provider = provider or WordComProvider()

    def execute(self, token: HumanActionToken) -> WordExecutionResult:
        verb = token.verb

        if bool(token.args.get("run_macro", False)):
            return WordExecutionResult(
                status="blocked",
                message="Macro execution is blocked by policy.",
                outcome_tokens=[WordOutcomeToken.ACTION_BLOCKED],
            )

        if bool(token.args.get("external_share", False)):
            return WordExecutionResult(
                status="blocked",
                message="External sharing is blocked by policy.",
                outcome_tokens=[WordOutcomeToken.ACTION_BLOCKED],
            )

        if verb == WordActionVerb.ESCALATE_TO_HUMAN.value:
            return WordExecutionResult(
                status="escalated",
                message=str(token.args.get("reason", "Escalated to human")),
                outcome_tokens=[WordOutcomeToken.TASK_ESCALATED],
            )

        try:
            app = self.provider.ensure_app()
        except Exception as e:
            return WordExecutionResult(status="error", message="Failed to start Word", error=str(e))

        if verb == WordActionVerb.OPEN_WORD.value:
            if app is None and not self.provider.is_word_running():
                return WordExecutionResult(
                    status="error",
                    message="Word process could not be confirmed after launch.",
                )
            return WordExecutionResult(
                status="ok",
                message="Word opened.",
                outcome_tokens=[WordOutcomeToken.WORD_OPENED],
            )

        try:
            if verb == WordActionVerb.OPEN_DOCUMENT.value:
                path = str(token.args.get("path") or token.target or "").strip()
                if not path:
                    return WordExecutionResult(status="error", message="Missing document path.")
                normalized = str(Path(path).expanduser().resolve())
                os.startfile(normalized)
                return WordExecutionResult(
                    status="ok",
                    message="Document opened.",
                    outcome_tokens=[WordOutcomeToken.DOCUMENT_OPENED],
                )

            if verb == WordActionVerb.CREATE_DOCUMENT.value:
                if app is not None:
                    app.Documents.Add()
                return WordExecutionResult(
                    status="ok",
                    message="New document created.",
                    outcome_tokens=[WordOutcomeToken.DOCUMENT_OPENED],
                )

            if app is None:
                return WordExecutionResult(status="error", message="Word COM session unavailable.")

            doc = getattr(app, "ActiveDocument", None)

            if verb == WordActionVerb.TYPE_TEXT.value:
                text = str(token.args.get("text") or "")
                selection = getattr(app, "Selection", None)
                if selection is None:
                    return WordExecutionResult(status="error", message="No active selection for typing.")
                selection.TypeText(text)
                return WordExecutionResult(
                    status="ok",
                    message="Text inserted.",
                    outcome_tokens=[WordOutcomeToken.TEXT_INSERTED],
                )

            if verb == WordActionVerb.FIND_TEXT.value:
                if doc is None:
                    return WordExecutionResult(status="error", message="No active document.")
                text = str(token.args.get("text") or "")
                found = bool(app.Selection.Find.Execute(text))
                msg = "Text found." if found else "Text not found."
                return WordExecutionResult(status="ok", message=msg, outcome_tokens=[WordOutcomeToken.TASK_COMPLETE])

            if verb == WordActionVerb.REPLACE_TEXT.value:
                if doc is None:
                    return WordExecutionResult(status="error", message="No active document.")
                old_text = str(token.args.get("old_text") or "")
                new_text = str(token.args.get("new_text") or "")
                app.Selection.Find.Execute(old_text, False, False, False, False, False, True, 1, False, new_text, 2)
                return WordExecutionResult(status="ok", message="Replace applied.", outcome_tokens=[WordOutcomeToken.TASK_COMPLETE])

            if verb == WordActionVerb.APPLY_STYLE.value:
                style_name = str(token.args.get("style") or "Normal")
                heading_text = str(token.args.get("text") or "")
                if heading_text:
                    selection = getattr(app, "Selection", None)
                    if selection is None:
                        return WordExecutionResult(status="error", message="No active selection for heading insertion.")
                    selection.TypeText(heading_text)
                app.Selection.Style = style_name
                return WordExecutionResult(
                    status="ok",
                    message="Style applied.",
                    outcome_tokens=[WordOutcomeToken.FORMAT_APPLIED],
                )

            if verb == WordActionVerb.APPLY_FORMATTING.value:
                sel = app.Selection
                font = sel.Font
                if "bold" in token.args:
                    font.Bold = bool(token.args["bold"])
                if "italic" in token.args:
                    font.Italic = bool(token.args["italic"])
                if "underline" in token.args:
                    font.Underline = 1 if bool(token.args["underline"]) else 0
                if "font_size" in token.args:
                    font.Size = int(token.args["font_size"])
                if "alignment" in token.args:
                    alignment = str(token.args["alignment"]).lower()
                    if alignment == "left":
                        sel.ParagraphFormat.Alignment = 0
                    elif alignment == "center":
                        sel.ParagraphFormat.Alignment = 1
                    elif alignment == "right":
                        sel.ParagraphFormat.Alignment = 2
                    elif alignment == "justify":
                        sel.ParagraphFormat.Alignment = 3
                if token.args.get("bullets", False):
                    sel.Range.ListFormat.ApplyBulletDefault()
                if token.args.get("numbered", False):
                    sel.Range.ListFormat.ApplyNumberDefault()
                return WordExecutionResult(
                    status="ok",
                    message="Formatting applied.",
                    outcome_tokens=[WordOutcomeToken.FORMAT_APPLIED],
                )

            if verb == WordActionVerb.INSERT_TABLE.value:
                rows = int(token.args.get("rows", 2))
                cols = int(token.args.get("cols", 2))
                app.ActiveDocument.Tables.Add(app.Selection.Range, rows, cols)
                return WordExecutionResult(status="ok", message="Table inserted.", outcome_tokens=[WordOutcomeToken.TASK_COMPLETE])

            if verb == WordActionVerb.INSERT_PAGE_BREAK.value:
                app.Selection.InsertBreak()
                return WordExecutionResult(status="ok", message="Page break inserted.", outcome_tokens=[WordOutcomeToken.TASK_COMPLETE])

            if verb == WordActionVerb.SAVE_DOCUMENT.value:
                if doc is None:
                    return WordExecutionResult(status="error", message="No active document.")
                doc.Save()
                return WordExecutionResult(
                    status="ok",
                    message="Document saved.",
                    outcome_tokens=[WordOutcomeToken.DOCUMENT_SAVED],
                )

            if verb == WordActionVerb.SAVE_AS.value:
                if doc is None:
                    return WordExecutionResult(status="error", message="No active document.")
                path = str(token.args.get("path") or token.target or "").strip()
                if not path:
                    return WordExecutionResult(status="error", message="Missing Save As path.")
                normalized = str(Path(path).expanduser().resolve())
                doc.SaveAs(normalized)
                return WordExecutionResult(
                    status="ok",
                    message="Document saved as new file.",
                    outcome_tokens=[WordOutcomeToken.DOCUMENT_SAVED],
                )

            if verb == WordActionVerb.EXPORT_PDF.value:
                if doc is None:
                    return WordExecutionResult(status="error", message="No active document.")
                path = str(token.args.get("path") or token.target or "").strip()
                if not path:
                    return WordExecutionResult(status="error", message="Missing PDF export path.")
                normalized = str(Path(path).expanduser().resolve())
                # wdExportFormatPDF = 17
                doc.ExportAsFixedFormat(normalized, 17)
                return WordExecutionResult(
                    status="ok",
                    message="PDF exported.",
                    outcome_tokens=[WordOutcomeToken.PDF_EXPORTED],
                )

            if verb == WordActionVerb.CLOSE_DOCUMENT.value:
                if doc is not None:
                    doc.Close(SaveChanges=0)
                return WordExecutionResult(status="ok", message="Document closed.", outcome_tokens=[WordOutcomeToken.TASK_COMPLETE])

            if verb == WordActionVerb.CLOSE_WORD.value:
                app.Quit()
                return WordExecutionResult(status="ok", message="Word closed.", outcome_tokens=[WordOutcomeToken.TASK_COMPLETE])

            if verb in {WordActionVerb.GET_WORD_STATE.value, WordActionVerb.VERIFY_DOCUMENT_STATE.value}:
                return WordExecutionResult(status="ok", message="State query complete.", outcome_tokens=[WordOutcomeToken.TASK_COMPLETE])

            return WordExecutionResult(status="error", message=f"Unsupported Word action verb: {verb}")
        except Exception as e:
            return WordExecutionResult(status="error", message="Word action execution failed.", error=str(e))
