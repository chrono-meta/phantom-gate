"""Core data models for hallucination findings"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


@dataclass
class ProjectContext:
    """Multi-file context for project-scoped detection (M5).

    Phase 1: Cross-axis contradiction detection across project files.

    Args:
        root_path: Absolute path to project root.
        files: Relative POSIX path → file content mapping.
        metadata: Additional project-level metadata.
    """

    root_path: Path
    files: Dict[str, str]  # relative POSIX path → content
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_file(self, rel_path: str) -> Optional[str]:
        """Get file content by relative path (None if not loaded)."""
        return self.files.get(rel_path)

    def find_files(self, pattern: str) -> List[str]:
        """Return relative paths matching a glob pattern."""
        return [p for p in self.files if fnmatch.fnmatch(p, pattern)]

    def abs_path(self, rel_path: str) -> Path:
        """Resolve relative path to absolute."""
        return self.root_path / rel_path


class Verdict(str, Enum):
    """Four-way finding verdict.

    Based on arXiv 2605.25665 four-way arbiter pattern.
    - TRUE_POSITIVE: confirmed hallucination
    - FALSE_POSITIVE: not a hallucination (detector error)
    - UNKNOWN: insufficient evidence for judgment
    - CONFLICT: multiple detectors disagree on this finding
    """
    TRUE_POSITIVE = "tp"
    FALSE_POSITIVE = "fp"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"

    @property
    def is_resolved(self) -> bool:
        return self in (Verdict.TRUE_POSITIVE, Verdict.FALSE_POSITIVE)

    @property
    def needs_review(self) -> bool:
        return self in (Verdict.UNKNOWN, Verdict.CONFLICT)


class Severity(str, Enum):
    """Severity classification for hallucination findings"""
    CRITICAL = "critical"  # Must fix - blocks release
    HIGH = "high"          # Should fix - significant risk
    MEDIUM = "medium"      # Should review - moderate risk
    LOW = "low"            # Can defer - minor concern
    INFO = "info"          # Informational only


class Evidence(BaseModel):
    """Evidence supporting a hallucination finding"""

    source: str = Field(..., description="Where this evidence was found")
    excerpt: str = Field(..., description="Relevant text excerpt")
    line_number: Optional[int] = Field(None, description="Line number if applicable")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

    def __str__(self) -> str:
        loc = f":{self.line_number}" if self.line_number else ""
        return f"{self.source}{loc}: {self.excerpt[:80]}..."


class Finding(BaseModel):
    """A detected hallucination pattern"""

    detector_id: str = Field(..., description="ID of detector that found this (e.g., 'M1', 'P3')")
    severity: Severity = Field(..., description="Impact severity")
    category: str = Field(..., description="Hallucination category (e.g., 'phantom', 'self-reference')")
    message: str = Field(..., description="Human-readable description")
    evidence: List[Evidence] = Field(default_factory=list, description="Supporting evidence")
    suggestion: Optional[str] = Field(None, description="Recommended fix")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional detector-specific data")

    # Feedback loop support (4-way verdict replaces is_true_positive)
    verdict: Verdict = Field(default=Verdict.UNKNOWN, description="Four-way arbiter verdict")
    feedback_notes: Optional[str] = Field(None, description="Human feedback notes")

    @property
    def is_true_positive(self) -> Optional[bool]:
        """Backward compatibility property"""
        if self.verdict == Verdict.TRUE_POSITIVE:
            return True
        elif self.verdict == Verdict.FALSE_POSITIVE:
            return False
        return None  # UNKNOWN, CONFLICT → None

    @is_true_positive.setter
    def is_true_positive(self, value: Optional[bool]):
        if value is True:
            self.verdict = Verdict.TRUE_POSITIVE
        elif value is False:
            self.verdict = Verdict.FALSE_POSITIVE
        else:
            self.verdict = Verdict.UNKNOWN

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] {self.detector_id}: {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """Export as JSON-serializable dict"""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Finding":
        """Import from dict"""
        return cls.model_validate(data)
