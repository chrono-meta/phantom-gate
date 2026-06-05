"""Base detector abstraction for hallucination detection"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional

from phantom_gate.core.models import Finding, Verdict

if TYPE_CHECKING:
    from phantom_gate.core.models import ProjectContext


class DetectionContext:
    """Context passed to detectors during scanning"""

    def __init__(
        self,
        content: str,
        source_path: str = "<input>",
        metadata: Dict[str, Any] = None,
        project: Optional["ProjectContext"] = None,
    ):
        self.content = content
        self.source_path = source_path
        self.metadata = metadata or {}
        self.lines = content.splitlines()
        self.project = project  # ProjectContext for M5 cross-file analysis

    def get_line(self, line_number: int) -> str:
        """Get line by number (1-indexed)"""
        if 1 <= line_number <= len(self.lines):
            return self.lines[line_number - 1]
        return ""


class BaseDetector(ABC):
    """Abstract base for all hallucination detectors

    Subclass this to create:
    - PMH universal detectors (M1~M5)
    - Domain-specific detectors (P-series for QASP, mobile patterns for mate, etc.)

    Class Variables:
        scope: "file" (default) or "project". File detectors run per-file;
               project detectors run once per project with a synthetic context.
    """

    scope: ClassVar[str] = "file"

    _VALID_SCOPES = frozenset({"file", "project"})

    def __init__(self):
        self.detector_id = self.__class__.__name__
        self.enabled = True
        if self.scope not in self._VALID_SCOPES:
            raise ValueError(
                f"{self.__class__.__name__}.scope={self.scope!r} is invalid. "
                f"Must be one of: {sorted(self._VALID_SCOPES)}"
            )

    @abstractmethod
    def detect(self, context: DetectionContext) -> List[Finding]:
        """Run detection on given context

        Args:
            context: Detection context with content and metadata

        Returns:
            List of findings (empty if no hallucinations detected)
        """
        pass

    def is_enabled(self) -> bool:
        """Check if this detector is enabled"""
        return self.enabled

    def disable(self):
        """Disable this detector"""
        self.enabled = False

    def enable(self):
        """Enable this detector"""
        self.enabled = True

    def __repr__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"<{self.detector_id} [{status}]>"


class MetaDetector(ABC):
    """Second-pass detector for cross-finding verification.

    Unlike BaseDetector (content → findings), MetaDetector operates on
    already-detected findings (findings → refined findings).

    Use cases:
    - Conflict resolution between detectors
    - Cross-finding pattern detection
    - Verdict promotion (UNKNOWN → TP/FP based on cross-evidence)
    - Duplicate finding merging

    Two-pass contract (arXiv 2605.25665):
      Pass 1: BaseDetector.detect(context) → raw findings
      Pass 2: MetaDetector.review(findings, context) → refined findings
    """

    def __init__(self):
        self.detector_id: str = self.__class__.__name__

    @abstractmethod
    def review(
        self,
        findings: List[Finding],
        context: DetectionContext,
    ) -> List[Finding]:
        """Review and refine pass-1 findings.

        Must return a list of findings (may be modified, merged, or extended).
        The returned list replaces the previous findings list.
        """
        ...


class ConflictResolver(MetaDetector):
    """Built-in: marks CONFLICT when detectors disagree on same evidence location."""

    def review(self, findings, context):
        from collections import defaultdict

        by_location: Dict[str, List[Finding]] = defaultdict(list)
        for f in findings:
            for e in f.evidence:
                key = f"{e.source}:{e.line_number}"
                by_location[key].append(f)

        for key, group in by_location.items():
            if len(group) >= 2:
                categories = {f.category for f in group}
                if len(categories) > 1:
                    for f in group:
                        f.verdict = Verdict.CONFLICT

        return findings
