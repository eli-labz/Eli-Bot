from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Dict, List

from .config import EdgeActionsConfig
from .models import Observation


@dataclass
class BrowserSession:
    config: EdgeActionsConfig
    playwright: Any = None
    browser: Any = None
    context: Any = None
    page: Any = None

    def start(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            raise RuntimeError(
                "Playwright is required for Edge Actions. Install with: pip install playwright && playwright install"
            ) from e

        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            channel=self.config.edge_channel,
            headless=self.config.headless,
        )
        self.context = self.browser.new_context(accept_downloads=True)
        self.page = self.context.new_page()

    def stop(self) -> None:
        if self.context is not None:
            self.context.close()
            self.context = None
        if self.browser is not None:
            self.browser.close()
            self.browser = None
        if self.playwright is not None:
            self.playwright.stop()
            self.playwright = None

    def observe(self) -> Observation:
        if self.page is None:
            return Observation(
                url="",
                title="",
                visible_text="",
                interactive_elements=[],
                downloads=[],
                active_tab="",
                timestamp=datetime.now(UTC).isoformat(),
                error_state="page_not_initialized",
            )

        url = self.page.url or ""
        title = self.page.title() if self.page else ""
        visible_text = self.page.locator("body").inner_text(timeout=3000) if self.page else ""

        interactive_elements: List[Dict[str, Any]] = []
        selectors = ["a", "button", "input", "textarea", "select", "[role='button']"]
        for sel in selectors:
            nodes = self.page.query_selector_all(sel)
            for node in nodes[:20]:
                text = (node.inner_text() or "").strip()
                name = (node.get_attribute("name") or "").strip()
                aria = (node.get_attribute("aria-label") or "").strip()
                interactive_elements.append({
                    "selector": sel,
                    "text": text[:120],
                    "name": name,
                    "aria_label": aria,
                })

        active_tab = title or url
        return Observation(
            url=url,
            title=title,
            visible_text=visible_text[:4000],
            interactive_elements=interactive_elements,
            downloads=[],
            active_tab=active_tab,
            timestamp=datetime.now(UTC).isoformat(),
            error_state=None,
        )
