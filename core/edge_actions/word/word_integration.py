from __future__ import annotations

from dataclasses import asdict
from dataclasses import is_dataclass
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .word_action_executor import WordActionExecutor
from .word_action_registry import WordActionRegistry
from .word_action_tokens import WordActionVerb, WordExecutionResult, WordOutcomeToken
from .word_observation_adapter import WordObservationAdapter
from .word_outcome_verifier import WordOutcomeVerifier
from .word_policy_gate import WordPolicyGate
from .word_trace_writer import WordTraceWriter


class WordWorkflowEngine:
    def __init__(
        self,
        trace_dir: Path | None = None,
        registry: Optional[WordActionRegistry] = None,
        observation_adapter: Optional[WordObservationAdapter] = None,
        policy_gate: Optional[WordPolicyGate] = None,
        executor: Optional[WordActionExecutor] = None,
        verifier: Optional[WordOutcomeVerifier] = None,
        trace_writer: Optional[WordTraceWriter] = None,
    ):
        self.trace_dir = trace_dir or Path(os.environ.get("ELI_WORD_TRACE_DIR", "edge_action_traces/word"))
        self.registry = registry or WordActionRegistry()
        self.observation_adapter = observation_adapter or WordObservationAdapter()
        self.policy_gate = policy_gate or WordPolicyGate(
            approved_dirs=_split_semicolon_env("ELI_WORD_ALLOWED_DIRS"),
            approved_output_dir=os.environ.get("ELI_WORD_APPROVED_OUTPUT_DIR"),
        )
        self.executor = executor or WordActionExecutor()
        self.verifier = verifier or WordOutcomeVerifier()
        self.trace_writer = trace_writer or WordTraceWriter(self.trace_dir)

    def run_prompt(self, prompt: str, allow_word_count: bool = False) -> Dict[str, Any]:
        token = self.registry.propose_from_prompt(prompt)
        before = self.observation_adapter.observe_state(allow_word_count=allow_word_count)

        decision = self.policy_gate.evaluate(token, before)
        if not decision.allowed:
            status = "paused_for_approval" if decision.requires_approval else "blocked"
            if decision.escalate:
                status = "escalated"
            result = WordExecutionResult(
                status=status,
                message=decision.reason,
                outcome_tokens=[
                    WordOutcomeToken.TASK_ESCALATED if decision.escalate else WordOutcomeToken.ACTION_BLOCKED
                ],
            )
            after = self.observation_adapter.observe_state(allow_word_count=allow_word_count)
            verify_status = self.verifier.verify(token, before, after, result)
            self.trace_writer.write_action_event(token, _decision_to_dict(decision), before, after, result, verify_status)
            trace_path = self.trace_writer.persist_trace("word_prompt", status)
            return {
                "status": status,
                "reason": decision.reason,
                "trace_path": str(trace_path),
                "outcome_tokens": [t.value for t in result.outcome_tokens],
            }

        result = self.executor.execute(token)
        after = self.observation_adapter.observe_state(allow_word_count=allow_word_count)
        verify_status = self.verifier.verify(token, before, after, result)

        if verify_status == "fail":
            status = "verification_failed"
        elif result.status == "escalated" or token.verb == WordActionVerb.ESCALATE_TO_HUMAN.value:
            status = "escalated"
        elif result.status == "blocked":
            status = "blocked"
        elif result.status == "ok":
            status = "completed"
        else:
            status = "error"

        self.trace_writer.write_action_event(token, _decision_to_dict(decision), before, after, result, verify_status)
        self.trace_writer.write_reusable_memory(
            {
                "verb": token.verb,
                "status": status,
                "verification": verify_status,
                "outcome_tokens": [t.value for t in result.outcome_tokens],
                "reason": result.message,
            }
        )
        trace_path = self.trace_writer.persist_trace("word_prompt", status)

        return {
            "status": status,
            "verification": verify_status,
            "trace_path": str(trace_path),
            "outcome_tokens": [t.value for t in result.outcome_tokens],
            "message": result.message,
            "error": result.error,
        }


def word_actions_enabled() -> bool:
    return str(os.environ.get("ELI_WORD_ACTIONS_ENABLED", "true")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _split_semicolon_env(key: str):
    raw = str(os.environ.get(key, "")).strip()
    if not raw:
        return []
    return [item for item in raw.split(";") if item.strip()]


def _decision_to_dict(decision: Any) -> Dict[str, Any]:
    if is_dataclass(decision):
        return asdict(decision)

    return {
        "allowed": bool(getattr(decision, "allowed", False)),
        "requires_approval": bool(getattr(decision, "requires_approval", False)),
        "reason": str(getattr(decision, "reason", "")),
        "escalate": bool(getattr(decision, "escalate", False)),
    }
