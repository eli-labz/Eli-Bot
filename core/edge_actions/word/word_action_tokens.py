from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class WordActionVerb(str, Enum):
    OPEN_WORD = "OPEN_WORD"
    OPEN_DOCUMENT = "OPEN_DOCUMENT"
    CREATE_DOCUMENT = "CREATE_DOCUMENT"
    TYPE_TEXT = "TYPE_TEXT"
    FIND_TEXT = "FIND_TEXT"
    REPLACE_TEXT = "REPLACE_TEXT"
    APPLY_STYLE = "APPLY_STYLE"
    APPLY_FORMATTING = "APPLY_FORMATTING"
    INSERT_TABLE = "INSERT_TABLE"
    INSERT_PAGE_BREAK = "INSERT_PAGE_BREAK"
    SAVE_DOCUMENT = "SAVE_DOCUMENT"
    SAVE_AS = "SAVE_AS"
    EXPORT_PDF = "EXPORT_PDF"
    CLOSE_DOCUMENT = "CLOSE_DOCUMENT"
    CLOSE_WORD = "CLOSE_WORD"
    GET_WORD_STATE = "GET_WORD_STATE"
    VERIFY_DOCUMENT_STATE = "VERIFY_DOCUMENT_STATE"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"


class WordRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class WordOutcomeToken(str, Enum):
    WORD_OPENED = "WORD_OPENED"
    DOCUMENT_OPENED = "DOCUMENT_OPENED"
    DOCUMENT_SAVED = "DOCUMENT_SAVED"
    TEXT_INSERTED = "TEXT_INSERTED"
    FORMAT_APPLIED = "FORMAT_APPLIED"
    PDF_EXPORTED = "PDF_EXPORTED"
    ACTION_BLOCKED = "ACTION_BLOCKED"
    TASK_ESCALATED = "TASK_ESCALATED"
    TASK_COMPLETE = "TASK_COMPLETE"


@dataclass
class HumanActionToken:
    verb: str
    target: str
    args: Dict[str, Any]
    preconditions: List[str]
    expected_outcome: str
    cost: float
    risk: str
    requiresApproval: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WordState:
    is_running: bool
    active_window_title: str
    document_path: Optional[str]
    is_saved: Optional[bool]
    selection_available: Optional[bool]
    word_count: Optional[int]
    process_name: str = "WINWORD.EXE"


@dataclass
class WordExecutionResult:
    status: str
    message: str
    outcome_tokens: List[WordOutcomeToken] = field(default_factory=list)
    error: Optional[str] = None
