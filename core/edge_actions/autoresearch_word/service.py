from __future__ import annotations

from pathlib import Path
from typing import Any

from core.edge_actions.autoresearch_adapter import AutoResearchAdapter

from .models import WordActionRequest


class AutoresearchWordService:
    def __init__(self, adapter: Any = None, autoresearch_dir: Path | None = None):
        self.autoresearch_dir = autoresearch_dir or (
            Path(__file__).resolve().parent.parent.parent / "third_party" / "autoresearch-master"
        )
        self.adapter = adapter or AutoResearchAdapter(base_dir=self.autoresearch_dir)

    def available(self) -> bool:
        return self.autoresearch_dir.exists() and (self.autoresearch_dir / "README.md").exists()

    def build_research_append_request(self, query: str) -> tuple[WordActionRequest, dict]:
        research = self.adapter.research(query=query, context={"mode": "word"})
        facts = self.adapter.extract_actionable_facts(research)

        lines = [f"Research Query: {query}"]
        for fact in facts[:8]:
            text = str(fact.get("fact", "")).strip()
            if text:
                lines.append(f"- {text}")

        text_block = "\n".join(lines)
        request = WordActionRequest(
            action="append_research_output",
            text=text_block,
            metadata={"query": query, "source_count": len(research.get("sources", []))},
        )
        return request, research
