import tempfile
import unittest
from pathlib import Path

from core.edge_actions.autoresearch_word.bridge import AutoresearchWordBridge
from core.edge_actions.autoresearch_word.config import AutoresearchWordConfig
from core.edge_actions.autoresearch_word.models import WordActionRequest, WordActionResult
from core.edge_actions.autoresearch_word.policy import WordActionPolicy
from core.edge_actions.autoresearch_word.service import AutoresearchWordService
from core.edge_actions.autoresearch_word.word_document_controller import WordDocumentController


class _FakeAdapter:
    def research(self, query, context=None):
        _ = context
        return {
            "query": query,
            "sources": [{"name": "README.md"}],
            "matches": [
                {"text": "Line one fact", "line": 1},
                {"text": "Line two fact", "line": 2},
            ],
        }

    def extract_actionable_facts(self, research_result):
        _ = research_result
        return [{"fact": "A"}, {"fact": "B"}]


class _FakeEngine:
    def __init__(self):
        self.prompts = []

    def run_prompt(self, prompt):
        self.prompts.append(prompt)
        return {"status": "completed", "message": "ok"}


class _FakeController:
    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return WordActionResult(status="ok", action=request.action, message="executed")


class AutoresearchWordBridgeTests(unittest.TestCase):
    def _enabled_config(self, trace_dir: Path, approved_dir: Path) -> AutoresearchWordConfig:
        return AutoresearchWordConfig(
            enabled=True,
            trace_dir=trace_dir,
            approved_input_dirs=(approved_dir,),
            approved_output_dir=approved_dir,
            allow_external_paths=False,
        )

    def test_feature_flag_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = AutoresearchWordConfig(
                enabled=False,
                trace_dir=Path(tmp),
                approved_input_dirs=(),
                approved_output_dir=None,
                allow_external_paths=False,
            )
            bridge = AutoresearchWordBridge(config=cfg)
            result = bridge.run_from_prompt("word research research test")
            self.assertEqual(result["status"], "inactive")

    def test_autoresearch_path_missing_or_unavailable(self):
        missing = Path("Z:/not-found-autoresearch")
        service = AutoresearchWordService(adapter=_FakeAdapter(), autoresearch_dir=missing)
        self.assertFalse(service.available())

    def test_worddocument_module_missing_or_unavailable(self):
        missing = Path("Z:/not-found-word-document")
        controller = WordDocumentController(word_project_dir=missing, workflow_engine=_FakeEngine())
        result = controller.detect_availability()
        self.assertEqual(result.status, "error")

    def test_bridge_initializes_successfully_when_dependencies_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            approved = base / "approved"
            approved.mkdir(parents=True, exist_ok=True)
            cfg = self._enabled_config(base / "trace", approved)
            service = AutoresearchWordService(adapter=_FakeAdapter(), autoresearch_dir=approved)
            bridge = AutoresearchWordBridge(config=cfg, service=service, controller=_FakeController())
            result = bridge.run_from_prompt("word research research ai safety")
            self.assertIn(result["status"], {"ok", "completed"})

    def test_research_output_is_converted_into_word_action_request(self):
        service = AutoresearchWordService(adapter=_FakeAdapter(), autoresearch_dir=Path("."))
        request, _research = service.build_research_append_request("ai testing")
        self.assertEqual(request.action, "append_research_output")
        self.assertIn("Research Query", request.text)

    def test_worddocument_receives_safe_insert_text_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "WordDocument.csproj").write_text("<Project/>", encoding="utf-8")
            engine = _FakeEngine()
            controller = WordDocumentController(word_project_dir=base, workflow_engine=engine)
            result = controller.execute(WordActionRequest(action="insert_text", text="hello world"))
            self.assertEqual(result.status, "ok")
            self.assertTrue(engine.prompts)
            self.assertTrue(engine.prompts[0].startswith("word type "))

    def test_worddocument_heading_request_maps_to_heading_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "WordDocument.csproj").write_text("<Project/>", encoding="utf-8")
            engine = _FakeEngine()
            controller = WordDocumentController(word_project_dir=base, workflow_engine=engine)
            result = controller.execute(WordActionRequest(action="apply_heading", text="Findings"))
            self.assertEqual(result.status, "ok")
            self.assertEqual(engine.prompts[-1], "word heading Findings")

    def test_save_is_allowed_for_approved_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            approved = base / "approved"
            approved.mkdir(parents=True, exist_ok=True)
            policy = WordActionPolicy(self._enabled_config(base / "trace", approved))
            request = WordActionRequest(action="save_as", path=str(approved / "doc.docx"))
            allowed, _reason = policy.evaluate(request)
            self.assertTrue(allowed)

    def test_save_is_blocked_for_unapproved_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            approved = base / "approved"
            approved.mkdir(parents=True, exist_ok=True)
            policy = WordActionPolicy(self._enabled_config(base / "trace", approved))
            request = WordActionRequest(action="save_as", path=str(base / "outside" / "doc.docx"))
            allowed, reason = policy.evaluate(request)
            self.assertFalse(allowed)
            self.assertIn("outside approved", reason.lower())

    def test_export_pdf_requires_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            approved = base / "approved"
            approved.mkdir(parents=True, exist_ok=True)
            policy = WordActionPolicy(self._enabled_config(base / "trace", approved))
            request = WordActionRequest(action="export_pdf", path=str(approved / "out.pdf"), approved=False)
            allowed, reason = policy.evaluate(request)
            self.assertFalse(allowed)
            self.assertIn("requires explicit approval", reason.lower())

    def test_existing_startup_behavior_safe_without_autoresearch(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = AutoresearchWordConfig(
                enabled=False,
                trace_dir=Path(tmp),
                approved_input_dirs=(),
                approved_output_dir=None,
                allow_external_paths=False,
            )
            bridge = AutoresearchWordBridge(config=cfg)
            result = bridge.run_from_prompt("word research create")
            self.assertEqual(result["status"], "inactive")


if __name__ == "__main__":
    unittest.main()
