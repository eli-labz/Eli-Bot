from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class AutoResearchAdapter:
    base_dir: Path

    def __init__(self, base_dir: Path | None = None):
        default = Path(__file__).resolve().parent.parent / "third_party" / "autoresearch-master"
        self.base_dir = base_dir or default

    def research(self, query: str, context: dict | None = None) -> dict:
        context = context or {}
        readme = self._read_safe("README.md")
        program = self._read_safe("program.md")
        hits = self._search_lines(readme + "\n" + program, query)
        return {
            "query": query,
            "context": context,
            "sources": [
                {"name": "README.md", "path": str(self.base_dir / "README.md")},
                {"name": "program.md", "path": str(self.base_dir / "program.md")},
            ],
            "matches": hits,
            "summary": self.summarize_sources(hits),
        }

    def summarize_sources(self, sources: List[dict]) -> str:
        if not sources:
            return "No relevant sources found in AutoResearch context."
        top = sources[:5]
        parts = [f"{item.get('file', 'source')}:{item.get('line', 0)} {item.get('text', '')}" for item in top]
        return " | ".join(parts)

    def extract_actionable_facts(self, research_result: dict) -> List[dict]:
        facts: List[dict] = []
        for match in research_result.get("matches", [])[:20]:
            facts.append(
                {
                    "fact": match.get("text", "").strip(),
                    "source": match.get("file", ""),
                    "line": match.get("line", 0),
                }
            )
        return facts

    def _read_safe(self, name: str) -> str:
        path = self.base_dir / name
        if not path.exists():
            return ""
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ""

    def _search_lines(self, blob: str, query: str) -> List[Dict[str, str]]:
        query_terms = [t for t in query.lower().split() if t]
        results: List[Dict[str, str]] = []
        for idx, line in enumerate(blob.splitlines(), start=1):
            low = line.lower()
            if query_terms and not any(term in low for term in query_terms):
                continue
            if line.strip():
                results.append({"file": "autoresearch", "line": idx, "text": line.strip()})
        return results
