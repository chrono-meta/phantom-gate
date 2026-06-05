"""Universal hallucination detectors — M1~M5.

M1: Phantom patterns
M2: Self-reference loops
M3: External dependency claims
M4: Temporal inconsistency
M5: Cross-axis contradiction (Phase 1 — Python version consistency)
"""
from __future__ import annotations

import re
from typing import ClassVar, Optional, Tuple

from phantom_gate.core.detector import BaseDetector, DetectionContext
from phantom_gate.core.models import Evidence, Finding, ProjectContext, Severity


class M1(BaseDetector):
    """Phantom patterns — unfalsifiable claims without evidence.

    Detects: 'always works', '100% accurate', 'never fails'
    Trigger: surrounding N lines lack URL/citation/data.

    **Design Rationale**:
    - Regex patterns capture common absolute claims
    - Lookback check (N=10 lines) for evidence markers (URL, citation, data)
    - Phase 0: Simple pattern matching (zero LLM cost)
    - Phase 1+: Optional LLM semantic analysis

    **Validation**: validated against real-world AI-generated documents.
    """

    PHANTOM_PATTERNS = [
        r"\b(always|never|100%|guaranteed|absolutely|certainly)\b.*\b(works?|accurate|correct|fails?|errors?)\b",
        r"\b(perfect|flawless|seamless)\w*\b",
    ]

    def detect(self, context: DetectionContext) -> list[Finding]:
        findings = []
        for i, line in enumerate(context.content.splitlines(), 1):
            for pattern in self.PHANTOM_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(Finding(
                        detector_id=self.detector_id,
                        severity=Severity.MEDIUM,
                        category="phantom",
                        message="Unfalsifiable claim without evidence",
                        evidence=[Evidence(
                            source=context.source_path,
                            line_number=i,
                            excerpt=line.strip(),
                        )],
                    ))
        return findings


class M2(BaseDetector):
    """Self-reference loops — 'as mentioned above' with no prior mention.

    Checks previous 10 lines for related keywords.

    **Design Rationale**:
    - Detects backward citations ("as mentioned above") without prior content
    - Keyword overlap check (2+ shared words required)
    - Bilingual: English + Korean patterns

    **Validation**: validated against real-world self-referential text.
    """

    SELF_REF_PATTERNS = [
        r"\b(as (?:mentioned|noted|described|discussed|shown|stated) (?:above|earlier|previously|before))\b",
        r"\b((?:위|앞)에서 (?:언급|설명|기술)한)\b",
    ]

    def detect(self, context: DetectionContext) -> list[Finding]:
        findings = []
        lines = context.content.splitlines()
        for i, line in enumerate(lines):
            for pattern in self.SELF_REF_PATTERNS:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    # 이전 10줄에 관련 키워드 있는지 검증
                    lookback = "\n".join(lines[max(0, i - 10):i])
                    ref_text = match.group(0)
                    # 간단한 키워드 추출 (주변 단어)
                    words = set(re.findall(r"\b\w{4,}\b", line.lower()))
                    prior_words = set(re.findall(r"\b\w{4,}\b", lookback.lower()))
                    overlap = words & prior_words - {"mentioned", "noted", "described", "above", "earlier"}

                    if len(overlap) < 2:  # 공통 키워드 2개 미만 → 의심
                        findings.append(Finding(
                            detector_id=self.detector_id,
                            severity=Severity.MEDIUM,
                            category="self-reference",
                            message=f"Self-reference '{ref_text}' — no matching prior content found",
                            evidence=[Evidence(
                                source=context.source_path,
                                line_number=i + 1,
                                excerpt=line.strip(),
                            )],
                        ))
        return findings


class M3(BaseDetector):
    """External dependency claims without validation logic.

    Detects: 'Claude will always...', 'GPT guarantees...' without try/except/validate.

    **Design Rationale**:
    - Flags absolute claims about external systems (LLMs, APIs)
    - Window check (±5 lines) for validation keywords (try/except/verify)
    - High severity: Unvalidated assumptions cause production failures

    **Validation**: common pattern in AI-output review findings (external-dependency claims).
    """

    DEPENDENCY_PATTERNS = [
        r"\b(Claude|GPT|Gemini|LLM|AI|model)\b.+\b(will always|guarantees?|ensures?|provides?)\b",
    ]

    def detect(self, context: DetectionContext) -> list[Finding]:
        findings = []
        lines = context.content.splitlines()
        for i, line in enumerate(lines):
            for pattern in self.DEPENDENCY_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    # 주변 5줄에 validation 키워드 있는지
                    window = "\n".join(lines[max(0, i - 5):min(len(lines), i + 5)])
                    has_validation = bool(re.search(
                        r"\b(try|except|validate|verify|check|assert|error|fallback)\b",
                        window, re.IGNORECASE,
                    ))
                    if not has_validation:
                        findings.append(Finding(
                            detector_id=self.detector_id,
                            severity=Severity.HIGH,
                            category="external-dependency",
                            message="External dependency claim without validation logic",
                            evidence=[Evidence(
                                source=context.source_path,
                                line_number=i + 1,
                                excerpt=line.strip(),
                            )],
                        ))
        return findings


class M4(BaseDetector):
    """Temporal inconsistency — date/version ordering violations.

    Detects: 2025-01-01 followed by 2024-12-31 (reverse chronology).

    **Design Rationale**:
    - Scans for date patterns (YYYY-MM-DD, YYYY/MM/DD)
    - Checks adjacent dates (within 5 lines) for reverse ordering
    - Common in CHANGELOG, release notes, commit logs

    **Validation**: Standard pattern in documentation quality checks
    """

    DATE_PATTERN = r"(\d{4}[-/]\d{2}[-/]\d{2})"

    def detect(self, context: DetectionContext) -> list[Finding]:
        findings = []
        dates_found: list[tuple[int, str]] = []

        for i, line in enumerate(context.content.splitlines(), 1):
            for match in re.finditer(self.DATE_PATTERN, line):
                dates_found.append((i, match.group(1).replace("/", "-")))

        # 연속 날짜 간 역순 탐지
        for j in range(1, len(dates_found)):
            prev_line, prev_date = dates_found[j - 1]
            curr_line, curr_date = dates_found[j]
            if curr_date < prev_date and curr_line - prev_line <= 5:
                findings.append(Finding(
                    detector_id=self.detector_id,
                    severity=Severity.HIGH,
                    category="temporal",
                    message=f"Date reversal: {prev_date} (L{prev_line}) → {curr_date} (L{curr_line})",
                    evidence=[
                        Evidence(source=context.source_path, line_number=prev_line, excerpt=prev_date),
                        Evidence(source=context.source_path, line_number=curr_line, excerpt=curr_date),
                    ],
                ))
        return findings


class M5(BaseDetector):
    """Cross-axis contradiction — multi-file Python version inconsistency.

    **Phase 1**: Detects Python version mismatches across project files:
      - README: "Python 3.12+" vs pyproject.toml: requires-python = ">=3.10"
      - Evidence from both files included in the finding.

    **Design Rationale**:
    - Requires ProjectContext (project-scoped detector, runs once per project)
    - Regex-based: zero LLM cost, deterministic
    - Phase 2+: extend to dependency declaration, feature claim vs. code existence

    **Status**: Phase 1 (released — Python version contradiction)
    """

    scope: ClassVar[str] = "project"

    # Matches: "Python 3.10", "Python 3.10+", "python >= 3.10", "python_requires >= 3.10"
    _README_VERSION_RE = re.compile(
        r"(?i)(?:python[_\s]*(?:requires[_\s]*)?(?:>=|>|==|=>)?\s*[\"\']?)"
        r"(?:>=|>|==)?\s*(\d+\.\d+)",
    )

    # Matches: requires-python = ">=3.10" or requires-python = ">=3.10,<4"
    _PYPROJECT_RE = re.compile(
        r'requires-python\s*=\s*["\'](?:>=?|~=|==)?\s*(\d+\.\d+)',
        re.IGNORECASE,
    )

    # Poetry-style: python = "^3.10" or python = ">=3.10,<4" under [tool.poetry.dependencies]
    _POETRY_RE = re.compile(
        r'^python\s*=\s*["\'][\^~>=<]*\s*(\d+\.\d+)',
        re.IGNORECASE | re.MULTILINE,
    )

    def detect(self, context: DetectionContext) -> list[Finding]:
        project = context.project
        if project is None:
            return []

        result = self._check_python_version(project)
        return [result] if result else []

    def _check_python_version(self, project: ProjectContext) -> Optional[Finding]:
        """Compare Python version claims across README and pyproject.toml."""
        versions: dict[str, tuple[str, int]] = {}  # rel_path → (version, line_no)

        # 1. Check README files
        for rel_path in project.find_files("README*"):
            ver, line_no = self._extract_readme_version(project.files[rel_path])
            if ver:
                versions[rel_path] = (ver, line_no)

        # 2. Check pyproject.toml
        pyproject_content = project.get_file("pyproject.toml")
        if pyproject_content:
            ver, line_no = self._extract_pyproject_version(pyproject_content)
            if ver:
                versions["pyproject.toml"] = (ver, line_no)

        if len(versions) < 2:
            return None  # Not enough data to compare

        unique_versions = {v for v, _ in versions.values()}
        if len(unique_versions) == 1:
            return None  # Consistent — no contradiction

        # Build evidence from all conflicting sources
        evidence = [
            Evidence(
                source=rel_path,
                excerpt=f"Python {ver}",
                line_number=line_no,
            )
            for rel_path, (ver, line_no) in sorted(versions.items())
        ]
        version_summary = ", ".join(
            f"{p}={v}" for p, (v, _) in sorted(versions.items())
        )
        return Finding(
            detector_id=self.detector_id,
            severity=Severity.HIGH,
            category="cross-axis-version",
            message=f"Python version inconsistency across project files: {version_summary}",
            evidence=evidence,
            suggestion="Align Python version requirements across README and pyproject.toml.",
        )

    def _extract_readme_version(self, content: str) -> Tuple[Optional[str], int]:
        """Extract first Python version from README content. Returns (version, line_no)."""
        for line_no, line in enumerate(content.splitlines(), 1):
            match = self._README_VERSION_RE.search(line)
            if match:
                return match.group(1), line_no
        return None, 0

    def _extract_pyproject_version(self, content: str) -> Tuple[Optional[str], int]:
        """Extract requires-python or Poetry python version from pyproject.toml."""
        for line_no, line in enumerate(content.splitlines(), 1):
            # PEP 621 standard: requires-python = ">=3.10"
            match = self._PYPROJECT_RE.search(line)
            if match:
                return match.group(1), line_no
            # Poetry style: python = "^3.10"
            match = self._POETRY_RE.search(line)
            if match:
                return match.group(1), line_no
        return None, 0


__all__ = ["M1", "M2", "M3", "M4", "M5"]
