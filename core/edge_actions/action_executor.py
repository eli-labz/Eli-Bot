from __future__ import annotations

import time
from typing import Any

from .models import ActionToken, ActionTokenType


class ActionExecutor:
    def __init__(self, page: Any):
        self.page = page

    def execute(self, action: ActionToken) -> str:
        t = action.action_type
        if t == ActionTokenType.NAVIGATE:
            self.page.goto(action.value or action.target or "about:blank", wait_until="domcontentloaded")
            return "ok"
        if t == ActionTokenType.CLICK:
            if action.selector:
                self.page.locator(action.selector).first.click(timeout=action.timeout_seconds * 1000)
            else:
                self.page.get_by_text(action.target or "", exact=False).first.click(timeout=action.timeout_seconds * 1000)
            return "ok"
        if t == ActionTokenType.TYPE:
            if action.selector:
                self.page.locator(action.selector).first.fill(action.value or "")
            else:
                self.page.keyboard.type(action.value or "")
            return "ok"
        if t == ActionTokenType.SCROLL:
            delta = int(action.metadata.get("delta", 1200))
            self.page.mouse.wheel(0, delta)
            return "ok"
        if t == ActionTokenType.SELECT:
            self.page.locator(action.selector or "select").first.select_option(label=action.value or "")
            return "ok"
        if t == ActionTokenType.OPEN_TAB:
            self.page.context.new_page()
            return "ok"
        if t == ActionTokenType.CLOSE_TAB:
            self.page.close()
            return "ok"
        if t == ActionTokenType.COPY_TEXT:
            text = self.page.locator(action.selector or "body").inner_text(timeout=4000)
            self.page.context.set_extra_http_headers({"x-eli-copied-len": str(len(text))})
            return text[:500]
        if t == ActionTokenType.PASTE:
            self.page.keyboard.type(action.value or "")
            return "ok"
        if t == ActionTokenType.UPLOAD:
            self.page.locator(action.selector or "input[type='file']").first.set_input_files(action.value or "")
            return "ok"
        if t == ActionTokenType.DOWNLOAD:
            if action.selector:
                self.page.locator(action.selector).first.click(timeout=action.timeout_seconds * 1000)
            else:
                self.page.get_by_text(action.target or "download", exact=False).first.click(timeout=action.timeout_seconds * 1000)
            return "ok"
        if t == ActionTokenType.EXTRACT_TEXT:
            return self.page.locator(action.selector or "body").first.inner_text(timeout=4000)[:1500]
        if t == ActionTokenType.VERIFY_TEXT:
            body = self.page.locator("body").inner_text(timeout=4000).lower()
            expected = (action.value or action.target or "").lower()
            return "ok" if expected in body else "not_found"
        if t == ActionTokenType.VERIFY_DOWNLOAD:
            return "ok"
        if t == ActionTokenType.INSPECT_STATE:
            return self.page.title()
        if t == ActionTokenType.WAIT:
            seconds = max(1, min(60, int(action.value or action.metadata.get("seconds", 2))))
            time.sleep(seconds)
            return "ok"
        if t in {ActionTokenType.ASK_HUMAN_APPROVAL, ActionTokenType.STOP}:
            return "halt"
        raise ValueError(f"Unsupported action type: {t}")
