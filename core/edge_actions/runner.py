from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Optional

from .action_executor import ActionExecutor
from .autoresearch_adapter import AutoResearchAdapter
from .browser_session import BrowserSession
from .consequence import ConsequenceAnalyzer
from .config import EdgeActionsConfig
from .memory_trace import MemoryTrace
from .models import ActionToken, ActionTokenType, ExecutionResult
from .planner import Planner
from .risk_policy import RiskPolicy
from .task_catalog import get_task
from .verifier import Verifier

try:
    from core.human_brain import HumanBrain
except Exception:
    try:
        from human_brain import HumanBrain
    except Exception:
        HumanBrain = None


class EdgeActionRunner:
    def __init__(self, config: Optional[EdgeActionsConfig] = None):
        self.config = config or EdgeActionsConfig.from_env()
        self.policy = RiskPolicy()
        self.planner = Planner()
        self.verifier = Verifier()
        self.consequence = ConsequenceAnalyzer()
        self.research = AutoResearchAdapter()
        self.brain = HumanBrain() if HumanBrain is not None else None

    def _resolve_brain_domain(self, task_domain: str) -> str:
        normalized = str(task_domain or "").strip().lower()
        finance_hints = {
            "finance",
            "bank",
            "banking",
            "payroll",
            "tax",
            "invoice",
            "billing",
            "treasury",
            "payment",
            "money",
            "accounting",
        }
        return "finance" if any(h in normalized for h in finance_hints) else "tasks"

    def run_task(self, task_id: str, inputs: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        if not self.config.enabled:
            raise RuntimeError("Edge Actions are disabled. Set ELI_EDGE_ACTIONS_ENABLED=true")

        task = get_task(task_id)
        brain_domain = self._resolve_brain_domain(task.domain)
        inputs = inputs or {}
        trace = MemoryTrace(self.config.trace_dir)
        session = BrowserSession(self.config)

        trace.add_event({"type": "task_start", "task": task_id, "inputs": inputs})
        trace.add_event({"type": "task_spec", "payload": asdict(task)})

        brain_snapshot = None
        if self.brain is not None:
            objective = str(inputs.get("objective", ""))
            guidance = self.brain.execution_guidance(task.name, objective, page_title="", domain=brain_domain)
            brain_snapshot = self.brain.state_snapshot(domain=brain_domain)
            trace.add_event(
                {
                    "type": "brain_guidance",
                    "domain": brain_domain,
                    "guidance": guidance,
                    "brain": brain_snapshot,
                }
            )

        # Research context is optional but always traceable.
        if inputs.get("query"):
            research_result = self.research.research(inputs["query"], context={"task": task_id})
            trace.add_event({"type": "research", "payload": research_result})

        session.start()
        executor = ActionExecutor(session.page)

        status = "completed"
        try:
            for step in range(self.config.max_steps):
                before = session.observe()
                trace.add_observation("before", before)

                if self.brain is not None:
                    objective = str(inputs.get("objective", ""))
                    _ = self.brain.execution_guidance(task.name, objective, before.title, domain=brain_domain)
                    brain_snapshot = self.brain.state_snapshot(domain=brain_domain)
                    trace.add_event({"type": "brain_state", "step": step, "domain": brain_domain, "brain": brain_snapshot})

                action = self.planner.next_action(task, before, brain_snapshot=brain_snapshot)
                risk = self.policy.evaluate(task, action, brain_snapshot=brain_snapshot)
                if risk.requires_approval:
                    approval_action = self.policy.approval_token(risk.reason)
                    trace.add_event({
                        "type": "approval_required",
                        "step": step,
                        "reason": risk.reason,
                        "action": asdict(approval_action),
                    })
                    status = "paused_for_approval"
                    break

                if not risk.allowed:
                    trace.add_event({
                        "type": "blocked_action",
                        "step": step,
                        "reason": risk.reason,
                        "action": asdict(action),
                    })
                    status = "blocked"
                    break

                if action.action_type == ActionTokenType.STOP:
                    trace.add_event({"type": "stop", "step": step, "action": asdict(action)})
                    break

                recovery_attempted = False
                error = None
                execute_status = "ok"
                try:
                    execute_status = executor.execute(action)
                except Exception as e:
                    error = str(e)
                    recovery_attempted = True
                    recovery = self.planner.recovery_action(error)
                    trace.add_event({"type": "recovery_attempt", "step": step, "error": error, "action": asdict(recovery)})
                    try:
                        executor.execute(recovery)
                    except Exception as re:
                        error = f"{error}; recovery_failed={re}"

                after = session.observe()
                trace.add_observation("after", after)

                verification = self.verifier.verify(task, action, before, after, execute_status)
                consequence = self.consequence.assess(
                    task=task,
                    action=action,
                    before=before,
                    after=after,
                    execute_status=execute_status,
                    verification_status=verification,
                    error=error,
                )
                result = ExecutionResult(
                    action_id=f"{task.id}-{step}",
                    action_type=action.action_type.value,
                    target=action.target,
                    status="ok" if error is None else "error",
                    before_observation=before,
                    after_observation=after,
                    verification_status=verification,
                    error=error,
                    recovery_attempted=recovery_attempted,
                )
                trace.add_result(result)
                trace.add_event(
                    {
                        "type": "consequence_assessment",
                        "step": step,
                        "action": action.action_type.value,
                        "severity": consequence.severity,
                        "unintended": consequence.unintended,
                        "summary": consequence.summary,
                        "recommended_recovery": consequence.recommended_recovery,
                    }
                )

                if consequence.unintended and consequence.recommended_recovery == "revert_to_before_url" and before.url:
                    correction = ActionToken(
                        action_type=ActionTokenType.NAVIGATE,
                        value=before.url,
                        metadata={"auto_correction": "revert_to_before_url", "trigger_step": step},
                    )
                    try:
                        executor.execute(correction)
                        correction_after = session.observe()
                        trace.add_event(
                            {
                                "type": "consequence_correction",
                                "step": step,
                                "status": "ok",
                                "from": after.url,
                                "to": correction_after.url,
                            }
                        )
                    except Exception as correction_error:
                        trace.add_event(
                            {
                                "type": "consequence_correction",
                                "step": step,
                                "status": "error",
                                "error": str(correction_error),
                            }
                        )

                if consequence.unintended and consequence.severity in {"medium", "high"} and self.brain is not None:
                    _ = self.brain.apply_feedback("verification_failed", confidence=0.7, domain=brain_domain)

                if verification == "fail":
                    status = "verification_failed"
                    break
        finally:
            session.stop()

        if self.brain is not None:
            confidence_by_status = {
                "completed": 0.85,
                "paused_for_approval": 0.55,
                "blocked": 0.65,
                "verification_failed": 0.75,
            }
            confidence = float(confidence_by_status.get(status, 0.6))
            adapted = self.brain.apply_feedback(status, confidence=confidence, domain=brain_domain)
            trace.add_event(
                {
                    "type": "brain_feedback",
                    "domain": brain_domain,
                    "status": status,
                    "confidence": confidence,
                    "brain": adapted,
                }
            )

        trace_path = trace.finalize(task, status)
        return {"status": status, "trace_path": str(trace_path), "task_id": task.id}
