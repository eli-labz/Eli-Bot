from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ActionTokenType(str, Enum):
    CLICK = "CLICK"
    TYPE = "TYPE"
    SCROLL = "SCROLL"
    NAVIGATE = "NAVIGATE"
    WAIT = "WAIT"
    SELECT = "SELECT"
    UPLOAD = "UPLOAD"
    DOWNLOAD = "DOWNLOAD"
    COPY_TEXT = "COPY_TEXT"
    OPEN_TAB = "OPEN_TAB"
    CLOSE_TAB = "CLOSE_TAB"
    EXTRACT_TEXT = "EXTRACT_TEXT"
    VERIFY_TEXT = "VERIFY_TEXT"
    VERIFY_DOWNLOAD = "VERIFY_DOWNLOAD"
    ASK_HUMAN_APPROVAL = "ASK_HUMAN_APPROVAL"
    PASTE = "PASTE"
    INSPECT_STATE = "INSPECT_STATE"
    STOP = "STOP"


@dataclass
class ActionToken:
    action_type: ActionTokenType
    target: Optional[str] = None
    value: Optional[str] = None
    selector: Optional[str] = None
    timeout_seconds: int = 15
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskSpec:
    id: str
    name: str
    description: str
    domain: str
    risk_level: str
    required_inputs: List[str]
    success_criteria: List[str]
    forbidden_actions: List[str]
    approval_required_actions: List[str]
    allowed_actions: List[str]
    verification_steps: List[str]
    recovery_behavior: List[str]
    timeout_behavior: str
    example_steps: List[Dict[str, Any]]


@dataclass
class Observation:
    url: str
    title: str
    visible_text: str
    interactive_elements: List[Dict[str, Any]]
    downloads: List[str]
    active_tab: str
    timestamp: str
    error_state: Optional[str] = None


@dataclass
class ExecutionResult:
    action_id: str
    action_type: str
    target: Optional[str]
    status: str
    before_observation: Observation
    after_observation: Observation
    verification_status: str
    error: Optional[str] = None
    recovery_attempted: bool = False


@dataclass
class RiskDecision:
    allowed: bool
    requires_approval: bool
    reason: str = ""


@dataclass
class ConsequenceAssessment:
    understood: bool
    severity: str
    summary: str
    unintended: bool = False
    recommended_recovery: str = "none"
