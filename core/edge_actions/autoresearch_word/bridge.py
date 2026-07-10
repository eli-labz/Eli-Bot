from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .config import AutoresearchWordConfig
from .models import WordActionRequest, WordActionResult
from .policy import WordActionPolicy
from .service import AutoresearchWordService
from .trace import WordTraceLogger
from .verifier import WordActionVerifier
from .word_document_controller import WordDocumentController


class AutoresearchWordBridge:
    def __init__(
        self,
        config: AutoresearchWordConfig | None = None,
        service: AutoresearchWordService | None = None,
        controller: WordDocumentController | None = None,
        policy: WordActionPolicy | None = None,
        verifier: WordActionVerifier | None = None,
        tracer: WordTraceLogger | None = None,
    ):
        self.config = config or AutoresearchWordConfig.from_env()
        self.service = service or AutoresearchWordService()
        self.controller = controller or WordDocumentController()
        self.policy = policy or WordActionPolicy(self.config)
        self.verifier = verifier or WordActionVerifier()
        self.tracer = tracer or WordTraceLogger(self.config.trace_dir)

    def enabled(self) -> bool:
        return self.config.enabled

    def run_from_prompt(self, prompt: str) -> dict[str, Any]:
        if not self.enabled():
            return {"status": "inactive", "message": "Autoresearch Word integration disabled."}

        parsed = self._parse_prompt(prompt)
        if parsed is None:
            return {"status": "ignored", "message": "Not an autoresearch-word prompt."}

        request, research = self._build_request(parsed)

        allowed, reason = self.policy.evaluate(request)
        if not allowed:
            blocked = WordActionResult(
                status="blocked",
                action=request.action,
                message="Action blocked by policy.",
                blocked_reason=reason,
            )
            blocked.verification = self.verifier.verify(request, blocked)
            trace_path = self.tracer.write(request, blocked, extra={"research": research})
            blocked.trace_path = str(trace_path)
            return asdict(blocked)

        result = self.controller.execute(request)
        result.verification = self.verifier.verify(request, result)
        trace_path = self.tracer.write(request, result, extra={"research": research})
        result.trace_path = str(trace_path)
        return asdict(result)

    def _build_request(self, parsed: dict[str, str]) -> tuple[WordActionRequest, dict[str, Any]]:
        command = parsed["command"]
        if command == "append_research":
            return self.service.build_research_append_request(parsed["query"])

        if command == "create":
            return WordActionRequest(action="create_document"), {}

        if command == "open":
            return WordActionRequest(action="open_document", path=parsed.get("path", "")), {}

        if command == "insert":
            return WordActionRequest(action="insert_text", text=parsed.get("text", "")), {}

        if command == "heading":
            return WordActionRequest(action="apply_heading", text=parsed.get("text", "")), {}

        if command == "save":
            return WordActionRequest(action="save_document"), {}

        if command == "save_as":
            return WordActionRequest(action="save_as", path=parsed.get("path", ""), approved=parsed.get("approved") == "yes"), {}

        if command == "export_pdf":
            return WordActionRequest(action="export_pdf", path=parsed.get("path", ""), approved=parsed.get("approved") == "yes"), {}

        if command == "close":
            return WordActionRequest(action="close_document", approved=parsed.get("approved") == "yes"), {}

        return WordActionRequest(action="detect_availability"), {}

    def _parse_prompt(self, prompt: str) -> dict[str, str] | None:
        raw = str(prompt or "").strip()
        low = raw.lower()

        if not (low.startswith("word research ") or low.startswith("winword research ")):
            return None

        content = raw.split(" ", 2)[2].strip() if len(raw.split(" ", 2)) >= 3 else ""
        if content.startswith("research "):
            return {"command": "append_research", "query": content[len("research "):].strip()}
        if content == "create":
            return {"command": "create"}
        if content.startswith("open "):
            return {"command": "open", "path": content[len("open "):].strip()}
        if content.startswith("insert "):
            return {"command": "insert", "text": content[len("insert "):].strip()}
        if content.startswith("heading "):
            return {"command": "heading", "text": content[len("heading "):].strip()}
        if content == "save":
            return {"command": "save"}
        if content.startswith("save as "):
            return {"command": "save_as", "path": content[len("save as "):].strip()}
        if content.startswith("export pdf "):
            return {"command": "export_pdf", "path": content[len("export pdf "):].strip()}
        if content.startswith("close"):
            return {"command": "close"}

        return {"command": "append_research", "query": content}


def autoresearch_word_bridge_available() -> bool:
    config = AutoresearchWordConfig.from_env()
    if not config.enabled:
        return False

    autoresearch_dir = Path(__file__).resolve().parent.parent.parent / "third_party" / "autoresearch-master"
    return autoresearch_dir.exists()
