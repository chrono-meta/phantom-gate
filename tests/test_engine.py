"""Tests for 2-pass pipeline and MetaDetector"""

import pytest
from phantom_gate.core.detector import (
    BaseDetector,
    MetaDetector,
    DetectionContext,
    ConflictResolver,
)
from phantom_gate.core.models import Finding, Severity, Evidence, Verdict
from phantom_gate.pipeline.engine import DetectionEngine
from phantom_gate.detectors.universal import M1, M2


class MockDetector(BaseDetector):
    """Mock detector for testing"""

    def __init__(self, findings_to_return):
        super().__init__()
        self.findings = findings_to_return

    def detect(self, context: DetectionContext):
        return self.findings


class MockMetaDetector(MetaDetector):
    """Mock meta-detector that marks all findings as TRUE_POSITIVE"""

    def review(self, findings, context):
        for f in findings:
            f.verdict = Verdict.TRUE_POSITIVE
        return findings


def test_engine_single_pass():
    """Test engine with single pass (no meta-detectors)"""
    finding1 = Finding(
        detector_id="mock",
        severity=Severity.HIGH,
        category="test",
        message="Test finding",
    )
    detector = MockDetector([finding1])
    engine = DetectionEngine([detector])

    findings = engine.scan("test content")

    assert len(findings) == 1
    assert findings[0].detector_id == "mock"


def test_engine_two_pass_with_meta():
    """Test engine with 2-pass architecture (meta-detector modifies findings)"""
    finding1 = Finding(
        detector_id="mock",
        severity=Severity.HIGH,
        category="test",
        message="Test finding",
    )
    detector = MockDetector([finding1])
    meta = MockMetaDetector()
    engine = DetectionEngine([detector], meta_detectors=[meta])

    findings = engine.scan("test content")

    assert len(findings) == 1
    assert findings[0].verdict == Verdict.TRUE_POSITIVE  # Modified by meta


def test_engine_disabled_detector():
    """Test engine skips disabled detectors"""
    finding1 = Finding(
        detector_id="mock",
        severity=Severity.HIGH,
        category="test",
        message="Test finding",
    )
    detector = MockDetector([finding1])
    detector.disable()
    engine = DetectionEngine([detector])

    findings = engine.scan("test content")

    assert len(findings) == 0  # Disabled detector should be skipped


def test_conflict_resolver_basic():
    """Test ConflictResolver marks conflicts"""
    # Two findings at same location with different categories
    finding1 = Finding(
        detector_id="M1",
        severity=Severity.HIGH,
        category="phantom",
        message="Finding 1",
        evidence=[Evidence(source="test.txt", excerpt="test", line_number=10)],
    )
    finding2 = Finding(
        detector_id="M2",
        severity=Severity.MEDIUM,
        category="self-reference",
        message="Finding 2",
        evidence=[Evidence(source="test.txt", excerpt="test", line_number=10)],
    )

    resolver = ConflictResolver()
    context = DetectionContext(content="test", source_path="test.txt")
    refined = resolver.review([finding1, finding2], context)

    # Both should be marked as CONFLICT
    assert len(refined) == 2
    assert refined[0].verdict == Verdict.CONFLICT
    assert refined[1].verdict == Verdict.CONFLICT


def test_conflict_resolver_no_conflict():
    """Test ConflictResolver does not flag non-conflicting findings"""
    finding1 = Finding(
        detector_id="M1",
        severity=Severity.HIGH,
        category="phantom",
        message="Finding 1",
        evidence=[Evidence(source="test.txt", excerpt="test", line_number=10)],
    )
    finding2 = Finding(
        detector_id="M1",
        severity=Severity.HIGH,
        category="phantom",
        message="Finding 2",
        evidence=[Evidence(source="test.txt", excerpt="test", line_number=20)],
    )

    resolver = ConflictResolver()
    context = DetectionContext(content="test", source_path="test.txt")
    refined = resolver.review([finding1, finding2], context)

    # No conflict (different lines)
    assert len(refined) == 2
    assert refined[0].verdict != Verdict.CONFLICT
    assert refined[1].verdict != Verdict.CONFLICT


def test_engine_with_real_detectors():
    """Integration test with M1 + M2 + ConflictResolver"""
    content = """
    This tool always works perfectly.
    As mentioned above, we verify the system.
    """

    engine = DetectionEngine(
        detectors=[M1(), M2()],
        meta_detectors=[ConflictResolver()],
    )
    findings = engine.scan(content, source_path="test.txt")

    # Should have findings from M1 and M2
    assert len(findings) >= 2
    detector_ids = {f.detector_id for f in findings}
    assert "M1" in detector_ids
    assert "M2" in detector_ids


def test_engine_enable_disable_detector():
    """Test engine enable/disable detector methods"""
    engine = DetectionEngine([M1(), M2()])

    # Disable M1
    engine.disable_detector("M1")
    enabled = engine.get_enabled_detectors()
    assert len(enabled) == 1
    assert enabled[0].detector_id == "M2"

    # Re-enable M1
    engine.enable_detector("M1")
    enabled = engine.get_enabled_detectors()
    assert len(enabled) == 2


def test_engine_multiple_meta_detectors():
    """Test engine with multiple meta-detectors in sequence"""
    finding = Finding(
        detector_id="mock",
        severity=Severity.HIGH,
        category="test",
        message="Test",
    )

    class MetaDetector1(MetaDetector):
        def review(self, findings, context):
            # Add metadata tag
            for f in findings:
                f.metadata["meta1"] = True
            return findings

    class MetaDetector2(MetaDetector):
        def review(self, findings, context):
            # Add another metadata tag
            for f in findings:
                f.metadata["meta2"] = True
            return findings

    detector = MockDetector([finding])
    engine = DetectionEngine(
        [detector],
        meta_detectors=[MetaDetector1(), MetaDetector2()],
    )

    findings = engine.scan("test")

    assert len(findings) == 1
    assert findings[0].metadata["meta1"] is True
    assert findings[0].metadata["meta2"] is True


def test_scan_project_detects_version_contradiction(tmp_path):
    """scan_project() runs M5 on a project directory and finds version mismatch"""
    from phantom_gate.detectors.universal import M5

    (tmp_path / "README.md").write_text("# Tool\n\nRequires Python 3.12+.\n")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "tool"\nrequires-python = ">=3.10"\n'
    )

    engine = DetectionEngine([M2(), M5()])
    findings = engine.scan_project(tmp_path)

    m5_findings = [f for f in findings if f.detector_id == "M5"]
    assert len(m5_findings) == 1
    assert m5_findings[0].category == "cross-axis-version"


def test_scan_project_no_false_positive_consistent(tmp_path):
    """scan_project() produces no M5 finding when versions match"""
    from phantom_gate.detectors.universal import M5

    (tmp_path / "README.md").write_text("# Tool\n\nRequires Python 3.10+.\n")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "tool"\nrequires-python = ">=3.10"\n'
    )

    engine = DetectionEngine([M5()])
    findings = engine.scan_project(tmp_path)

    m5_findings = [f for f in findings if f.detector_id == "M5"]
    assert len(m5_findings) == 0


def test_scan_project_file_detectors_run_per_file(tmp_path):
    """scan_project() runs file-scoped detectors on each file"""
    (tmp_path / "README.md").write_text(
        "This tool always works perfectly.\n"
    )
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "tool"\n')

    engine = DetectionEngine([M1()])
    findings = engine.scan_project(tmp_path)

    m1_findings = [f for f in findings if f.detector_id == "M1"]
    assert len(m1_findings) >= 1
    # Source should be a relative file path, not "<project>"
    assert m1_findings[0].evidence[0].source == "README.md"


def test_scan_project_m5_runs_once(tmp_path):
    """M5 (project-scoped) runs exactly once even with multiple files"""
    from phantom_gate.detectors.universal import M5

    (tmp_path / "README.md").write_text("# Tool\n\nRequires Python 3.12+.\n")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "tool"\nrequires-python = ">=3.10"\n'
    )

    engine = DetectionEngine([M5()])
    findings = engine.scan_project(tmp_path)

    m5_findings = [f for f in findings if f.detector_id == "M5"]
    assert len(m5_findings) == 1  # Not once per file — exactly once


def test_load_project_relative_keys(tmp_path):
    """load_project() uses relative POSIX path keys in files dict"""
    from phantom_gate.pipeline.engine import load_project

    (tmp_path / "README.md").write_text("# Hello\n")
    (tmp_path / "pyproject.toml").write_text("[project]\n")

    project = load_project(tmp_path)

    assert "README.md" in project.files
    assert "pyproject.toml" in project.files
    # Keys must be relative, not absolute
    for key in project.files:
        assert not key.startswith("/")
