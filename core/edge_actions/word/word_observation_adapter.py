from __future__ import annotations

from typing import Any, Optional

import psutil

from .word_action_tokens import WordState


class WordObservationAdapter:
    def __init__(self, process_name: str = "WINWORD.EXE", com_client: Any = None):
        self.process_name = process_name.upper()
        self.com_client = com_client

    def is_word_running(self) -> bool:
        for proc in psutil.process_iter(["name"]):
            try:
                name = str(proc.info.get("name") or "").upper()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if name == self.process_name:
                return True
        return False

    def observe_state(self, allow_word_count: bool = False) -> WordState:
        is_running = self.is_word_running()
        if not is_running:
            return WordState(
                is_running=False,
                active_window_title="",
                document_path=None,
                is_saved=None,
                selection_available=None,
                word_count=None,
            )

        app = self._get_word_app()
        if app is None:
            return WordState(
                is_running=True,
                active_window_title="WINWORD",
                document_path=None,
                is_saved=None,
                selection_available=None,
                word_count=None,
            )

        document_path: Optional[str] = None
        is_saved: Optional[bool] = None
        selection_available: Optional[bool] = None
        word_count: Optional[int] = None
        active_window_title = "WINWORD"

        try:
            active_window_title = str(getattr(app, "Caption", "WINWORD") or "WINWORD")
        except Exception:
            pass

        try:
            doc = app.ActiveDocument
        except Exception:
            doc = None

        if doc is not None:
            try:
                active_window_title = str(getattr(doc, "Name", active_window_title) or active_window_title)
            except Exception:
                pass
            try:
                full_name = str(getattr(doc, "FullName", "") or "")
                document_path = full_name or None
            except Exception:
                document_path = None
            try:
                is_saved = bool(getattr(doc, "Saved", False))
            except Exception:
                is_saved = None
            try:
                selection = getattr(app, "Selection", None)
                selection_available = selection is not None
            except Exception:
                selection_available = None
            if allow_word_count:
                try:
                    # wdStatisticWords = 0
                    word_count = int(doc.ComputeStatistics(0))
                except Exception:
                    word_count = None

        return WordState(
            is_running=True,
            active_window_title=active_window_title,
            document_path=document_path,
            is_saved=is_saved,
            selection_available=selection_available,
            word_count=word_count,
        )

    def _get_word_app(self):
        if self.com_client is not None:
            return self.com_client

        try:
            import win32com.client  # type: ignore

            return win32com.client.GetActiveObject("Word.Application")
        except Exception:
            return None
