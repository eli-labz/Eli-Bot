from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class WordActionRequest:
    action: str
    path: Optional[str] = None
    text: str = ""
    heading: str = "Heading 1"
    approved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WordActionResult:
    status: str
    action: str
    message: str
    verification: str = "unknown"
    blocked_reason: str = ""
    trace_path: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
