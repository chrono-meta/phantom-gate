"""Tests for M1~M4 basic detection (M5 skipped)

Uses independent fixtures (tests/conftest.py) to avoid AI circular validation.
"""

import pytest
from phantom_gate.core.detector import DetectionContext
from phantom_gate.detectors.universal import M1, M2, M3, M4, M5


def test_m1_phantom_detection(sample_content):
    """Test M1 detects unfalsifiable claims — independent fixture input"""
    detector = M1()
    context = DetectionContext(content=sample_content, source_path="test.txt")
    findings = detector.detect(context)

    assert len(findings) >= 1  # Should catch at least "always" or "100%" or "never"
    assert all(f.category == "phantom" for f in findings)
    assert all(f.detector_id == "M1" for f in findings)


def test_m1_no_false_positive():
    """Test M1 does not flag normal content"""
    detector = M1()
    content = "This tool works in most cases based on empirical data."
    context = DetectionContext(content=content, source_path="test.txt")
    findings = detector.detect(context)

    assert len(findings) == 0


def test_m2_self_reference_detection():
    """Test M2 detects self-reference loops"""
    detector = M2()
    content = """
    This is the first line.
    As mentioned above, we need to verify something.
    """
    context = DetectionContext(content=content, source_path="test.txt")
    findings = detector.detect(context)

    # Should catch "as mentioned above" with insufficient prior content
    assert len(findings) >= 1
    assert findings[0].category == "self-reference"
    assert findings[0].detector_id == "M2"


def test_m2_valid_self_reference():
    """Test M2 allows valid self-references with prior content"""
    detector = M2()
    content = """
    The authentication system uses JWT tokens for security.
    Token validation happens at the gateway level.
    As mentioned above, JWT tokens are used for authentication.
    """
    context = DetectionContext(content=content, source_path="test.txt")
    findings = detector.detect(context)

    # Should NOT flag valid self-reference (JWT, tokens, authentication overlap)
    assert len(findings) == 0 or all(
        "jwt" not in f.message.lower() for f in findings
    )


def test_m3_external_dependency_detection():
    """Test M3 detects external dependency claims without validation"""
    detector = M3()
    content = """
    Claude will always return structured JSON output.
    The system guarantees this behavior.
    """
    context = DetectionContext(content=content, source_path="test.txt")
    findings = detector.detect(context)

    assert len(findings) >= 1
    assert findings[0].category == "external-dependency"
    assert findings[0].detector_id == "M3"


def test_m3_with_validation_logic():
    """Test M3 allows external dependency with validation"""
    detector = M3()
    content = """
    Claude will always return structured JSON.
    We validate the output before processing:
    try:
        result = json.loads(output)
    except JSONDecodeError:
        fallback()
    """
    context = DetectionContext(content=content, source_path="test.txt")
    findings = detector.detect(context)

    # Should NOT flag because validation logic is present
    assert len(findings) == 0


def test_m4_temporal_inconsistency():
    """Test M4 detects date reversal"""
    detector = M4()
    content = """
    Version released on 2025-06-01.
    Hotfix applied on 2025-05-15.
    """
    context = DetectionContext(content=content, source_path="test.txt")
    findings = detector.detect(context)

    assert len(findings) >= 1
    assert findings[0].category == "temporal"
    assert findings[0].detector_id == "M4"
    assert "reversal" in findings[0].message.lower()


def test_m4_no_false_positive_chronological():
    """Test M4 allows correct chronological order"""
    detector = M4()
    content = """
    Version released on 2025-05-15.
    Hotfix applied on 2025-06-01.
    """
    context = DetectionContext(content=content, source_path="test.txt")
    findings = detector.detect(context)

    assert len(findings) == 0


def test_m5_placeholder():
    """Test M5 returns empty when no ProjectContext is attached"""
    detector = M5()
    content = "Any content"
    context = DetectionContext(content=content, source_path="test.txt")
    findings = detector.detect(context)

    assert len(findings) == 0  # No ProjectContext → no findings


def test_m5_version_contradiction_detected():
    """M5 Phase 1: README says 3.12+, pyproject.toml requires 3.10 → contradiction"""
    from pathlib import Path
    from phantom_gate.core.models import ProjectContext

    project = ProjectContext(
        root_path=Path("/fake/project"),
        files={
            "README.md": "# My Tool\n\nRequires Python 3.12+.\n",
            "pyproject.toml": '[project]\nname = "mytool"\nrequires-python = ">=3.10"\n',
        },
    )
    detector = M5()
    context = DetectionContext(content="", source_path="<project>", project=project)
    findings = detector.detect(context)

    assert len(findings) == 1
    assert findings[0].category == "cross-axis-version"
    assert findings[0].detector_id == "M5"
    assert "3.12" in findings[0].message
    assert "3.10" in findings[0].message
    # Evidence from both files
    evidence_sources = {e.source for e in findings[0].evidence}
    assert "README.md" in evidence_sources
    assert "pyproject.toml" in evidence_sources


def test_m5_version_consistent_no_finding():
    """M5: matching versions → no finding"""
    from pathlib import Path
    from phantom_gate.core.models import ProjectContext

    project = ProjectContext(
        root_path=Path("/fake/project"),
        files={
            "README.md": "# My Tool\n\nRequires Python 3.10+.\n",
            "pyproject.toml": '[project]\nname = "mytool"\nrequires-python = ">=3.10"\n',
        },
    )
    detector = M5()
    context = DetectionContext(content="", source_path="<project>", project=project)
    findings = detector.detect(context)

    assert len(findings) == 0


def test_m5_single_source_no_finding():
    """M5: only one file has version info → not enough to compare"""
    from pathlib import Path
    from phantom_gate.core.models import ProjectContext

    project = ProjectContext(
        root_path=Path("/fake/project"),
        files={
            "pyproject.toml": '[project]\nrequires-python = ">=3.11"\n',
        },
    )
    detector = M5()
    context = DetectionContext(content="", source_path="<project>", project=project)
    findings = detector.detect(context)

    assert len(findings) == 0


def test_m5_scope_is_project():
    """M5 scope must be 'project' (not 'file')"""
    assert M5.scope == "project"


def test_all_detectors_enabled_by_default():
    """Test all detectors are enabled by default"""
    detectors = [M1(), M2(), M3(), M4(), M5()]
    for detector in detectors:
        assert detector.is_enabled() is True


def test_m5_poetry_version_contradiction():
    """M5 Phase 1: README says 3.12+, Poetry pyproject has python = '^3.10' → contradiction"""
    from pathlib import Path
    from phantom_gate.core.models import ProjectContext

    project = ProjectContext(
        root_path=Path("/fake/project"),
        files={
            "README.md": "# My Tool\n\nRequires Python 3.12+.\n",
            "pyproject.toml": '[tool.poetry.dependencies]\npython = "^3.10"\n',
        },
    )
    detector = M5()
    context = DetectionContext(content="", source_path="<project>", project=project)
    findings = detector.detect(context)

    assert len(findings) == 1
    assert findings[0].category == "cross-axis-version"
    assert "3.12" in findings[0].message
    assert "3.10" in findings[0].message


def test_m5_poetry_version_consistent():
    """M5: Poetry pyproject matches README → no finding"""
    from pathlib import Path
    from phantom_gate.core.models import ProjectContext

    project = ProjectContext(
        root_path=Path("/fake/project"),
        files={
            "README.md": "# My Tool\n\nRequires Python 3.10+.\n",
            "pyproject.toml": '[tool.poetry.dependencies]\npython = "^3.10"\n',
        },
    )
    detector = M5()
    context = DetectionContext(content="", source_path="<project>", project=project)
    findings = detector.detect(context)

    assert len(findings) == 0
