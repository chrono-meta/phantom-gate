"""Targeted tests to close coverage gaps in core modules."""
from __future__ import annotations

from pathlib import Path


# ── DetectionContext.get_line ─────────────────────────────────────────────────

def test_detection_context_get_line_valid():
    from phantom_gate.core.detector import DetectionContext
    ctx = DetectionContext(content="line1\nline2\nline3")
    assert ctx.get_line(1) == "line1"
    assert ctx.get_line(3) == "line3"


def test_detection_context_get_line_out_of_bounds():
    from phantom_gate.core.detector import DetectionContext
    ctx = DetectionContext(content="line1\nline2")
    assert ctx.get_line(0) == ""   # below 1
    assert ctx.get_line(99) == ""  # above length


# ── BaseDetector repr + enable/disable ───────────────────────────────────────

def test_base_detector_repr(tmp_path):
    from phantom_gate.detectors.universal import M1
    d = M1()
    r = repr(d)
    assert "M1" in r
    assert "enabled" in r

    d.disable()
    assert "disabled" in repr(d)

    d.enable()
    assert "enabled" in repr(d)


# ── ProjectContext.abs_path ───────────────────────────────────────────────────

def test_project_context_abs_path(tmp_path):
    from phantom_gate.core.models import ProjectContext
    project = ProjectContext(root_path=tmp_path, files={})
    resolved = project.abs_path("pyproject.toml")
    assert resolved == tmp_path / "pyproject.toml"


# ── Finding.is_true_positive setter with None ─────────────────────────────────

def test_finding_is_true_positive_setter_none():
    from phantom_gate.core.models import Finding, Severity, Verdict
    f = Finding(detector_id="M1", severity=Severity.MEDIUM, category="phantom", message="test")
    f.is_true_positive = True
    assert f.verdict == Verdict.TRUE_POSITIVE
    f.is_true_positive = False
    assert f.verdict == Verdict.FALSE_POSITIVE
    f.is_true_positive = None
    assert f.verdict == Verdict.UNKNOWN


def test_finding_str():
    from phantom_gate.core.models import Finding, Severity
    f = Finding(detector_id="M1", severity=Severity.HIGH, category="phantom", message="Test msg")
    s = str(f)
    assert "HIGH" in s
    assert "M1" in s


def test_finding_to_dict_from_dict():
    from phantom_gate.core.models import Finding, Severity
    f = Finding(detector_id="M2", severity=Severity.LOW, category="self-reference", message="hi")
    d = f.to_dict()
    assert d["detector_id"] == "M2"
    f2 = Finding.from_dict(d)
    assert f2.detector_id == "M2"


# ── DetectionEngine verbose mode ─────────────────────────────────────────────

def test_engine_verbose_mode():
    from phantom_gate.core.detector import BaseDetector, DetectionContext
    from phantom_gate.core.models import Finding, Severity
    from phantom_gate.pipeline.engine import DetectionEngine

    class AlwaysFinding(BaseDetector):
        def detect(self, ctx: DetectionContext):
            return [Finding(
                detector_id=self.detector_id,
                severity=Severity.MEDIUM,
                category="test",
                message="verbose test",
            )]

    engine = DetectionEngine([AlwaysFinding()], verbose=True)
    findings = engine.scan("some content", source_path="test.txt")
    assert len(findings) == 1


def test_engine_verbose_mode_no_findings():
    from phantom_gate.core.detector import BaseDetector, DetectionContext
    from phantom_gate.pipeline.engine import DetectionEngine

    class NullDetector(BaseDetector):
        def detect(self, ctx):
            return []

    engine = DetectionEngine([NullDetector()], verbose=True)
    findings = engine.scan("content")
    assert findings == []


# ── load_project extra_files + OSError ───────────────────────────────────────

def test_load_project_extra_files(tmp_path):
    from phantom_gate.pipeline.engine import load_project
    (tmp_path / "custom.txt").write_text("custom content")
    project = load_project(tmp_path, extra_files=["custom.txt"])
    assert "custom.txt" in project.files
    assert "custom content" in project.files["custom.txt"]


def test_load_project_missing_files_silently_skipped(tmp_path):
    from phantom_gate.pipeline.engine import load_project
    project = load_project(tmp_path)  # no files exist
    assert project.files == {}
    assert project.root_path == tmp_path.resolve()


# ── scan_project with meta-detectors ─────────────────────────────────────────

def test_scan_project_meta_detector_applied(tmp_path):
    from phantom_gate.core.detector import MetaDetector, DetectionContext
    from phantom_gate.core.models import Verdict
    from phantom_gate.detectors.universal import M5
    from phantom_gate.pipeline.engine import DetectionEngine

    (tmp_path / "README.md").write_text("# Tool\n\nRequires Python 3.12+.\n")
    (tmp_path / "pyproject.toml").write_text('[project]\nrequires-python = ">=3.10"\n')

    class MarkTP(MetaDetector):
        def review(self, findings, context):
            for f in findings:
                f.verdict = Verdict.TRUE_POSITIVE
            return findings

    engine = DetectionEngine([M5()], meta_detectors=[MarkTP()])
    findings = engine.scan_project(tmp_path)

    assert all(f.verdict == Verdict.TRUE_POSITIVE for f in findings)


# ── M5 _extract fallback (no version found) ──────────────────────────────────

def test_m5_extract_readme_no_version():
    from phantom_gate.detectors.universal import M5
    m5 = M5()
    ver, line_no = m5._extract_readme_version("# No version here\n\nJust text.\n")
    assert ver is None
    assert line_no == 0


def test_m5_extract_pyproject_no_version():
    from phantom_gate.detectors.universal import M5
    m5 = M5()
    ver, line_no = m5._extract_pyproject_version("[project]\nname = 'tool'\n")
    assert ver is None
    assert line_no == 0


# ── DetectionEngine.__repr__ ──────────────────────────────────────────────────

def test_engine_repr():
    from phantom_gate.detectors.universal import M1, M2
    from phantom_gate.pipeline.engine import DetectionEngine
    engine = DetectionEngine([M1(), M2()])
    r = repr(engine)
    assert "2/2" in r


def test_load_project_skips_oversized_file(tmp_path):
    """load_project silently skips files exceeding max_file_bytes"""
    from phantom_gate.pipeline.engine import load_project
    big = tmp_path / "README.md"
    big.write_text("x" * 100)
    project = load_project(tmp_path, max_file_bytes=50)  # limit 50 bytes
    assert "README.md" not in project.files  # skipped


def test_base_detector_invalid_scope():
    """BaseDetector.__init__ raises ValueError for unknown scope"""
    from phantom_gate.core.detector import BaseDetector, DetectionContext
    import pytest

    class BadDetector(BaseDetector):
        scope = "galaxy"
        def detect(self, ctx):
            return []

    with pytest.raises(ValueError, match="scope"):
        BadDetector()
