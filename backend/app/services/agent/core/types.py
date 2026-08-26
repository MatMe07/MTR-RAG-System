# agent/core/types.py

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolStatus(str, Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ToolResult:
    """Результат выполнения тула"""
    text: str = ""
    components: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    review: bool = False
    status: ToolStatus = ToolStatus.SUCCESS
    error: Optional[str] = None
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "components": self.components,
            "warnings": self.warnings,
            "sources": self.sources,
            "missing": self.missing,
            "review": self.review,
            "status": self.status.value,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class NodeResult:
    """Результат выполнения узла графа"""
    node_name: str
    status: NodeStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
