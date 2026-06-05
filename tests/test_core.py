"""Tests for core data models (Verdict, Finding)"""

import pytest
from phantom_gate.core.models import Verdict, Severity, Evidence, Finding


def test_verdict_enum():
    """Test Verdict enum values"""
    assert Verdict.TRUE_POSITIVE == "tp"
    assert Verdict.FALSE_POSITIVE == "fp"
    assert Verdict.UNKNOWN == "unknown"
    assert Verdict.CONFLICT == "conflict"


def test_verdict_is_resolved():
    """Test verdict resolution status"""
    assert Verdict.TRUE_POSITIVE.is_resolved is True
    assert Verdict.FALSE_POSITIVE.is_resolved is True
    assert Verdict.UNKNOWN.is_resolved is False
    assert Verdict.CONFLICT.is_resolved is False


def test_verdict_needs_review():
    """Test verdict review requirement"""
    assert Verdict.UNKNOWN.needs_review is True
    assert Verdict.CONFLICT.needs_review is True
    assert Verdict.TRUE_POSITIVE.needs_review is False
    assert Verdict.FALSE_POSITIVE.needs_review is False


def test_finding_verdict_field():
    """Test Finding.verdict field with default UNKNOWN"""
    finding = Finding(
        detector_id="M1",
        severity=Severity.HIGH,
        category="phantom",
        message="Test finding",
    )
    assert finding.verdict == Verdict.UNKNOWN


def test_finding_verdict_set():
    """Test setting verdict directly"""
    finding = Finding(
        detector_id="M1",
        severity=Severity.HIGH,
        category="phantom",
        message="Test finding",
    )
    finding.verdict = Verdict.TRUE_POSITIVE
    assert finding.verdict == Verdict.TRUE_POSITIVE
    assert finding.is_true_positive is True


def test_finding_backward_compat_property():
    """Test backward compatibility is_true_positive property"""
    finding = Finding(
        detector_id="M1",
        severity=Severity.HIGH,
        category="phantom",
        message="Test",
        verdict=Verdict.TRUE_POSITIVE,
    )

    # Getter
    assert finding.is_true_positive is True

    finding.verdict = Verdict.FALSE_POSITIVE
    assert finding.is_true_positive is False

    finding.verdict = Verdict.UNKNOWN
    assert finding.is_true_positive is None

    finding.verdict = Verdict.CONFLICT
    assert finding.is_true_positive is None


def test_finding_backward_compat_setter():
    """Test backward compatibility is_true_positive setter"""
    finding = Finding(
        detector_id="M1",
        severity=Severity.HIGH,
        category="phantom",
        message="Test",
    )

    # Setter
    finding.is_true_positive = True
    assert finding.verdict == Verdict.TRUE_POSITIVE

    finding.is_true_positive = False
    assert finding.verdict == Verdict.FALSE_POSITIVE

    finding.is_true_positive = None
    assert finding.verdict == Verdict.UNKNOWN


def test_evidence_model():
    """Test Evidence model"""
    evidence = Evidence(
        source="test.py",
        excerpt="This is test evidence",
        line_number=42,
    )
    assert evidence.source == "test.py"
    assert evidence.line_number == 42
    assert "test.py:42" in str(evidence)


def test_finding_serialization():
    """Test Finding to_dict and from_dict"""
    finding = Finding(
        detector_id="M1",
        severity=Severity.HIGH,
        category="phantom",
        message="Test finding",
        verdict=Verdict.TRUE_POSITIVE,
        evidence=[
            Evidence(source="test.py", excerpt="test", line_number=1)
        ],
    )

    data = finding.to_dict()
    assert data["verdict"] == "tp"
    assert data["detector_id"] == "M1"

    restored = Finding.from_dict(data)
    assert restored.verdict == Verdict.TRUE_POSITIVE
    assert restored.detector_id == "M1"
