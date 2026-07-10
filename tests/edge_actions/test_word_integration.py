import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core.assistant_intents import get_word_workflow_steps, looks_like_open_word_request
from core.edge_actions.word.word_action_executor import WordActionExecutor, WordComProvider
from core.edge_actions.word.word_action_registry import WordActionRegistry
from core.edge_actions.word.word_action_tokens import (
    HumanActionToken,
    WordExecutionResult,
    WordOutcomeToken,
    WordState,
)
from core.edge_actions.word.word_integration import WordWorkflowEngine
from core.edge_actions.word.word_observation_adapter import WordObservationAdapter
from core.edge_actions.word.word_outcome_verifier import WordOutcomeVerifier
from core.edge_actions.word.word_policy_gate import WordPolicyGate
from core.edge_actions.word.word_trace_writer import WordTraceWriter


class _FakeDoc:
    Name = "Report.docx"
    FullName = "C:\\Approved\\Report.docx"
    Saved = True

    def ComputeStatistics(self, _):
        return 120


class _FakeSelection:
    pass


class _FakeWordAppWithDoc:
    Caption = "Microsoft Word"
    ActiveDocument = _FakeDoc()
    Selection = _FakeSelection()


class _FakeWordAppNoDoc:
    Caption = "Microsoft Word"

    @property
    def ActiveDocument(self):
        raise RuntimeError("No active document")


class _StaticObservationAdapter:
    def __init__(self, before: WordState, after: WordState):
        self._states = [before, after]

    def observe_state(self, allow_word_count=False):
        _ = allow_word_count
        if len(self._states) > 1:
            return self._states.pop(0)
        return self._states[0]


class _AlwaysAllowPolicy:
    def evaluate(self, token, state):
        _ = token, state

        class _Decision:
            allowed = True
            requires_approval = False
            reason = "allowed"
            escalate = False

        return _Decision()


class _StaticExecutor:
    def __init__(self, result: WordExecutionResult):
        self.result = result

    def execute(self, token: HumanActionToken):
        _ = token
        return self.result


class _ProviderNoComWordRunning(WordComProvider):
    def ensure_app(self):
        return None

    def is_word_running(self) -> bool:
        return True


class _ProviderNoComWordNotRunning(WordComProvider):
    def ensure_app(self):
        return None

    def is_word_running(self) -> bool:
        return False


class WordIntegrationTests(unittest.TestCase):
    def test_plain_open_word_intent_is_detected(self):
        self.assertTrue(looks_like_open_word_request("open Microsoft Word"))
        self.assertTrue(looks_like_open_word_request("launch winword"))
        self.assertFalse(looks_like_open_word_request("open Notepad"))

    def test_combined_open_word_new_document_workflow_is_detected(self):
        self.assertEqual(
            get_word_workflow_steps("open Word and create a new document"),
            ["word open", "word create document"],
        )
        self.assertEqual(
            get_word_workflow_steps("launch Microsoft Word then new document"),
            ["word open", "word create document"],
        )
        self.assertEqual(get_word_workflow_steps("open Notepad and create a new document"), [])

    def test_combined_open_word_type_workflow_is_detected(self):
        self.assertEqual(
            get_word_workflow_steps("open Word and type Hello World"),
            ["word open", "word type Hello World"],
        )
        self.assertEqual(
            get_word_workflow_steps("launch Microsoft Word then write Quarterly summary"),
            ["word open", "word type Quarterly summary"],
        )

    def test_combined_open_word_save_as_workflow_is_detected(self):
        self.assertEqual(
            get_word_workflow_steps("open Word and save as C:\\Approved\\hello.docx"),
            ["word open", "word save as C:\\Approved\\hello.docx"],
        )
        self.assertEqual(
            get_word_workflow_steps("start winword then save it as C:\\Approved\\draft.docx"),
            ["word open", "word save as C:\\Approved\\draft.docx"],
        )

    def test_winword_not_running(self):
        adapter = WordObservationAdapter()
        adapter.is_word_running = lambda: False
        state = adapter.observe_state()
        self.assertFalse(state.is_running)
        self.assertIsNone(state.document_path)

    def test_word_running_no_active_document(self):
        adapter = WordObservationAdapter(com_client=_FakeWordAppNoDoc())
        adapter.is_word_running = lambda: True
        state = adapter.observe_state()
        self.assertTrue(state.is_running)
        self.assertIsNone(state.document_path)

    def test_active_document_detected(self):
        adapter = WordObservationAdapter(com_client=_FakeWordAppWithDoc())
        adapter.is_word_running = lambda: True
        state = adapter.observe_state(allow_word_count=True)
        self.assertTrue(state.is_running)
        self.assertEqual(state.document_path, "C:\\Approved\\Report.docx")
        self.assertEqual(state.word_count, 120)

    def test_registry_accepts_winword_prefix(self):
        token = WordActionRegistry().propose_from_prompt("winword save")
        self.assertEqual(token.verb, "SAVE_DOCUMENT")

    def test_registry_maps_heading_prompt_to_apply_style(self):
        token = WordActionRegistry().propose_from_prompt("word heading Executive Summary")
        self.assertEqual(token.verb, "APPLY_STYLE")
        self.assertEqual(token.args["style"], "Heading 1")
        self.assertEqual(token.args["text"], "Executive Summary")

    def test_save_succeeds(self):
        before = WordState(True, "Microsoft Word", "C:\\Approved\\Report.docx", False, True, 100)
        after = WordState(True, "Microsoft Word", "C:\\Approved\\Report.docx", True, True, 101)

        with tempfile.TemporaryDirectory() as tmp:
            engine = WordWorkflowEngine(
                trace_dir=Path(tmp),
                registry=WordActionRegistry(),
                observation_adapter=_StaticObservationAdapter(before, after),
                policy_gate=_AlwaysAllowPolicy(),
                executor=_StaticExecutor(
                    WordExecutionResult(status="ok", message="saved", outcome_tokens=[WordOutcomeToken.DOCUMENT_SAVED])
                ),
                verifier=WordOutcomeVerifier(),
                trace_writer=WordTraceWriter(Path(tmp)),
            )
            result = engine.run_prompt("word save")
            self.assertEqual(result["status"], "completed")
            self.assertIn("DOCUMENT_SAVED", result["outcome_tokens"])

    def test_save_blocked_because_path_not_approved(self):
        policy = WordPolicyGate(approved_dirs=["C:\\Approved"], approved_output_dir="C:\\ApprovedOutput")
        state = WordState(True, "Microsoft Word", "C:\\Approved\\Report.docx", True, True, 50)
        registry = WordActionRegistry()
        token = registry.make_token("SAVE_AS", target="C:\\Blocked\\out.docx", args={"path": "C:\\Blocked\\out.docx"})
        decision = policy.evaluate(token, state)
        self.assertFalse(decision.allowed)
        self.assertIn("allowlist", decision.reason.lower())

    def test_replace_text_blocked_pending_approval(self):
        policy = WordPolicyGate(approved_dirs=["C:\\Approved"])
        state = WordState(True, "Microsoft Word", "C:\\Approved\\Report.docx", True, True, 50)
        registry = WordActionRegistry()
        token = registry.make_token("REPLACE_TEXT", target="active_document", args={"old_text": "a", "new_text": "b"})
        decision = policy.evaluate(token, state)
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_approval)

    def test_export_pdf_blocked_pending_approval(self):
        policy = WordPolicyGate(approved_dirs=["C:\\Approved"], approved_output_dir="C:\\ApprovedOutput")
        state = WordState(True, "Microsoft Word", "C:\\Approved\\Report.docx", True, True, 50)
        registry = WordActionRegistry()
        token = registry.make_token("EXPORT_PDF", target="C:\\ApprovedOutput\\out.pdf", args={"path": "C:\\ApprovedOutput\\out.pdf"})
        decision = policy.evaluate(token, state)
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_approval)

    def test_unsaved_close_blocked_pending_approval(self):
        policy = WordPolicyGate(approved_dirs=["C:\\Approved"])
        state = WordState(True, "Microsoft Word", "C:\\Approved\\Report.docx", False, True, 50)
        registry = WordActionRegistry()
        token = registry.make_token("CLOSE_WORD", target="word")
        decision = policy.evaluate(token, state)
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_approval)

    def test_verifier_detects_expected_outcome(self):
        verifier = WordOutcomeVerifier()
        before = WordState(True, "Microsoft Word", "C:\\Approved\\Report.docx", False, True, 100)
        after = WordState(True, "Microsoft Word", "C:\\Approved\\Report.docx", True, True, 100)
        token = WordActionRegistry().make_token("SAVE_DOCUMENT", target="active_document")
        result = WordExecutionResult(status="ok", message="saved", outcome_tokens=[WordOutcomeToken.DOCUMENT_SAVED])
        status = verifier.verify(token, before, after, result)
        self.assertEqual(status, "pass")

    def test_trace_writer_records_success_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = WordTraceWriter(Path(tmp))
            token = WordActionRegistry().make_token("TYPE_TEXT", target="active_document", args={"text": "hello"})
            before = WordState(True, "Microsoft Word", "C:\\Approved\\Report.docx", True, True, 10)
            after = WordState(True, "Microsoft Word", "C:\\Approved\\Report.docx", False, True, 11)

            writer.write_action_event(
                token,
                {"allowed": True},
                before,
                after,
                WordExecutionResult(status="ok", message="typed", outcome_tokens=[WordOutcomeToken.TEXT_INSERTED]),
                "pass",
            )
            writer.write_action_event(
                token,
                {"allowed": False},
                after,
                after,
                WordExecutionResult(status="error", message="failed", error="boom"),
                "fail",
            )

            trace_path = writer.persist_trace("word_tests", "mixed")
            self.assertTrue(trace_path.exists())
            self.assertEqual(len(writer.events), 2)

    def test_open_word_succeeds_when_process_running_but_com_not_attached(self):
        executor = WordActionExecutor(provider=_ProviderNoComWordRunning())
        token = WordActionRegistry().make_token("OPEN_WORD", target="word")
        result = executor.execute(token)
        self.assertEqual(result.status, "ok")
        self.assertIn(WordOutcomeToken.WORD_OPENED, result.outcome_tokens)

    def test_open_word_fails_when_process_not_running_and_com_missing(self):
        executor = WordActionExecutor(provider=_ProviderNoComWordNotRunning())
        token = WordActionRegistry().make_token("OPEN_WORD", target="word")
        result = executor.execute(token)
        self.assertEqual(result.status, "error")

    def test_provider_ensure_app_retries_before_failing(self):
        provider = WordComProvider(com_client=None)
        with patch("core.edge_actions.word.word_action_executor.subprocess.Popen") as mock_popen, patch(
            "core.edge_actions.word.word_action_executor.time.sleep"
        ) as _mock_sleep, patch.object(provider, "get_app", side_effect=[None] * 4 + [object()]):
            app = provider.ensure_app()
            self.assertIsNotNone(app)
            mock_popen.assert_called_once()


if __name__ == "__main__":
    unittest.main()
