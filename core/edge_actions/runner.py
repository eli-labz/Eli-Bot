from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Optional

from .action_executor import ActionExecutor
from .autoresearch_adapter import AutoResearchAdapter
from .browser_session import BrowserSession
from .config import EdgeActionsConfig
from .memory_trace import MemoryTrace
from .models import ActionTokenType, ExecutionResult
from .planner import Planner
from .risk_policy import RiskPolicy
from .task_catalog import get_task
from .verifier import Verifier


class EdgeActionRunner:
    def __init__(self, config: Optional[EdgeActionsConfig] = None):
        self.config = config or EdgeActionsConfig.from_env()
        self.policy = RiskPolicy()
        self.planner = Planner()
        self.verifier = Verifier()
        self.research = AutoResearchAdapter()

    def run_task(self, task_id: str, inputs: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        if not self.config.enabled:
            raise RuntimeError("Edge Actions are disabled. Set ELI_EDGE_ACTIONS_ENABLED=true")

        task = get_task(task_id)
        inputs = inputs or {}
        trace = MemoryTrace(self.config.trace_dir)
        session = BrowserSession(self.config)

        trace.add_event({"type": "task_start", "task": task_id, "inputs": inputs})
        trace.add_event({"type": "task_spec", "payload": asdict(task)})

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

                action = self.planner.next_action(task, before)
                risk = self.policy.evaluate(task, action)
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

                if verification == "fail":
                    status = "verification_failed"
                    break
        finally:
            session.stop()

        trace_path = trace.finalize(task, status)
        return {"status": status, "trace_path": str(trace_path), "task_id": task.id}
