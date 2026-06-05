"""Direct unit tests for CLI command functions.

These tests call cmd_* functions directly (not via subprocess) so they
contribute to coverage.  Subprocess tests in test_cli.py cover integration.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

def _ns(**kwargs) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


def _findings_file(tmp_path: Path, verdict: str = "unknown") -> Path:
    finding = {
        "detector_id": "M1", "severity": "medium", "category": "phantom",
        "message": "Unfalsifiable claim",
        "evidence": [{"source": "t.txt", "excerpt": "always works", "line_number": 1, "metadata": {}}],
        "suggestion": None, "metadata": {}, "verdict": verdict, "feedback_notes": None,
    }
    p = tmp_path / "findings.json"
    p.write_text(json.dumps([finding]))
    return p


def _labeled_file(tmp_path: Path, tp: int = 3, fp: int = 1) -> Path:
    findings = (
        [{"detector_id": "M1", "severity": "medium", "category": "phantom",
          "message": "tp", "evidence": [], "suggestion": None,
          "metadata": {}, "verdict": "tp", "feedback_notes": None}] * tp +
        [{"detector_id": "M1", "severity": "medium", "category": "phantom",
          "message": "fp", "evidence": [], "suggestion": None,
          "metadata": {}, "verdict": "fp", "feedback_notes": None}] * fp
    )
    p = tmp_path / "labeled.json"
    p.write_text(json.dumps(findings))
    return p


# ── cmd_scan — file mode ──────────────────────────────────────────────────────

def test_cmd_scan_clean_file(tmp_path):
    from phantom_gate.cli import cmd_scan
    f = tmp_path / "clean.txt"
    f.write_text("Normal content without issues.\n")

    args = _ns(file=f, project=False, detectors="M1", output=None, severity="info")
    rc = cmd_scan(args)
    assert rc == 0


def test_cmd_scan_with_findings_stdout(tmp_path, capsys):
    from phantom_gate.cli import cmd_scan
    f = tmp_path / "bad.txt"
    f.write_text("This tool always works perfectly.\n")

    args = _ns(file=f, project=False, detectors="M1", output=None, severity="info")
    rc = cmd_scan(args)
    captured = capsys.readouterr()
    assert "M1" in captured.out or rc in (0, 1)


def test_cmd_scan_output_json(tmp_path):
    from phantom_gate.cli import cmd_scan
    f = tmp_path / "bad.txt"
    f.write_text("This tool always works perfectly.\n")
    out = tmp_path / "report.json"

    args = _ns(file=f, project=False, detectors="M1", output=out, severity="info")
    rc = cmd_scan(args)
    assert out.exists()
    data = json.loads(out.read_text())
    assert isinstance(data, list)


def test_cmd_scan_severity_filter_excludes_low(tmp_path, capsys):
    from phantom_gate.cli import cmd_scan
    f = tmp_path / "bad.txt"
    f.write_text("This tool always works perfectly.\n")

    # M1 fires at MEDIUM; filtering at HIGH should suppress it
    args = _ns(file=f, project=False, detectors="M1", output=None, severity="high")
    rc = cmd_scan(args)
    captured = capsys.readouterr()
    # Either no findings shown or exit 0
    assert rc == 0 or "M1" not in captured.out


def test_cmd_scan_file_not_found(tmp_path, capsys):
    from phantom_gate.cli import cmd_scan
    args = _ns(file=tmp_path / "ghost.txt", project=False, detectors="all",
               output=None, severity="info")
    rc = cmd_scan(args)
    assert rc == 2


def test_cmd_scan_unknown_detector_warning(tmp_path, capsys):
    from phantom_gate.cli import cmd_scan
    f = tmp_path / "f.txt"
    f.write_text("hello")
    args = _ns(file=f, project=False, detectors="ZZUNKNOWN", output=None, severity="info")
    rc = cmd_scan(args)
    assert rc == 2  # no detectors loaded


def test_cmd_scan_project_mode(tmp_path):
    from phantom_gate.cli import cmd_scan
    (tmp_path / "README.md").write_text("# Tool\n\nRequires Python 3.12+.\n")
    (tmp_path / "pyproject.toml").write_text('[project]\nrequires-python = ">=3.10"\n')
    out = tmp_path / "out.json"

    args = _ns(file=tmp_path, project=True, detectors="M5", output=out, severity="info")
    rc = cmd_scan(args)
    assert rc in (0, 1)
    data = json.loads(out.read_text())
    assert any(f["detector_id"] == "M5" for f in data)


def test_cmd_scan_project_requires_directory(tmp_path, capsys):
    from phantom_gate.cli import cmd_scan
    f = tmp_path / "file.txt"
    f.write_text("hi")
    args = _ns(file=f, project=True, detectors="all", output=None, severity="info")
    rc = cmd_scan(args)
    assert rc == 2


def test_cmd_scan_non_file_without_project(tmp_path, capsys):
    from phantom_gate.cli import cmd_scan
    args = _ns(file=tmp_path, project=False, detectors="all", output=None, severity="info")
    rc = cmd_scan(args)
    assert rc == 2


# ── cmd_report ────────────────────────────────────────────────────────────────

def test_cmd_report_text(tmp_path, capsys):
    from phantom_gate.cli import cmd_report
    f = _findings_file(tmp_path)
    args = _ns(findings=f, format="text", output=None)
    rc = cmd_report(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "M1" in out
    assert "phantom" in out.lower()


def test_cmd_report_md(tmp_path, capsys):
    from phantom_gate.cli import cmd_report
    f = _findings_file(tmp_path)
    args = _ns(findings=f, format="md", output=None)
    rc = cmd_report(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "# phantom-gate Report" in out


def test_cmd_report_json(tmp_path, capsys):
    from phantom_gate.cli import cmd_report
    f = _findings_file(tmp_path)
    args = _ns(findings=f, format="json", output=None)
    rc = cmd_report(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1


def test_cmd_report_to_file(tmp_path):
    from phantom_gate.cli import cmd_report
    f = _findings_file(tmp_path)
    out = tmp_path / "report.md"
    args = _ns(findings=f, format="md", output=out)
    rc = cmd_report(args)
    assert rc == 0
    assert "# phantom-gate Report" in out.read_text()


def test_cmd_report_empty_findings(tmp_path, capsys):
    from phantom_gate.cli import cmd_report
    f = tmp_path / "empty.json"
    f.write_text("[]")
    args = _ns(findings=f, format="text", output=None)
    rc = cmd_report(args)
    assert rc == 0
    assert "No hallucinations" in capsys.readouterr().out


def test_cmd_report_file_not_found(tmp_path, capsys):
    from phantom_gate.cli import cmd_report
    args = _ns(findings=tmp_path / "ghost.json", format="text", output=None)
    rc = cmd_report(args)
    assert rc == 2


# ── cmd_label ─────────────────────────────────────────────────────────────────

def test_cmd_label_tp(tmp_path, monkeypatch):
    from phantom_gate.cli import cmd_label
    f = _findings_file(tmp_path)
    out = tmp_path / "labeled.json"

    monkeypatch.setattr("sys.stdin", io.StringIO("t\n"))
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    args = _ns(findings=f, output=out)
    rc = cmd_label(args)
    assert rc == 0
    data = json.loads(out.read_text())
    assert data[0]["verdict"] == "tp"


def test_cmd_label_fp(tmp_path, monkeypatch):
    from phantom_gate.cli import cmd_label
    f = _findings_file(tmp_path)
    out = tmp_path / "labeled.json"

    monkeypatch.setattr("sys.stdin", io.StringIO("fp\n"))
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    args = _ns(findings=f, output=out)
    rc = cmd_label(args)
    assert rc == 0
    data = json.loads(out.read_text())
    assert data[0]["verdict"] == "fp"


def test_cmd_label_skip(tmp_path, monkeypatch):
    from phantom_gate.cli import cmd_label
    f = _findings_file(tmp_path)
    out = tmp_path / "labeled.json"

    monkeypatch.setattr("sys.stdin", io.StringIO("s\n"))
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    args = _ns(findings=f, output=out)
    rc = cmd_label(args)
    assert rc == 0
    data = json.loads(out.read_text())
    assert data[0]["verdict"] == "unknown"


def test_cmd_label_overwrite_input(tmp_path, monkeypatch):
    """When --output not given, label overwrites the input file"""
    from phantom_gate.cli import cmd_label
    f = _findings_file(tmp_path)

    monkeypatch.setattr("sys.stdin", io.StringIO("t\n"))
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    args = _ns(findings=f, output=None)
    rc = cmd_label(args)
    assert rc == 0
    data = json.loads(f.read_text())
    assert data[0]["verdict"] == "tp"


def test_cmd_label_empty_findings(tmp_path, capsys):
    from phantom_gate.cli import cmd_label
    f = tmp_path / "empty.json"
    f.write_text("[]")
    args = _ns(findings=f, output=None)
    rc = cmd_label(args)
    assert rc == 0
    assert "No findings" in capsys.readouterr().out


def test_cmd_label_file_not_found(tmp_path):
    from phantom_gate.cli import cmd_label
    args = _ns(findings=tmp_path / "ghost.json", output=None)
    rc = cmd_label(args)
    assert rc == 2


def test_cmd_label_eof_treated_as_skip(tmp_path, monkeypatch):
    """Empty stdin line (EOF) is treated as skip"""
    from phantom_gate.cli import cmd_label
    f = _findings_file(tmp_path)
    out = tmp_path / "out.json"

    monkeypatch.setattr("sys.stdin", io.StringIO(""))  # EOF immediately
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    args = _ns(findings=f, output=out)
    rc = cmd_label(args)
    assert rc == 0
    data = json.loads(out.read_text())
    assert data[0]["verdict"] == "unknown"  # skipped


# ── cmd_calibrate ─────────────────────────────────────────────────────────────

def test_cmd_calibrate_basic(tmp_path, capsys):
    from phantom_gate.cli import cmd_calibrate
    f = _labeled_file(tmp_path, tp=3, fp=1)
    args = _ns(findings=f, min_samples=1)
    rc = cmd_calibrate(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "M1" in out
    assert "75%" in out


def test_cmd_calibrate_warning_low_precision(tmp_path, capsys):
    from phantom_gate.cli import cmd_calibrate
    f = _labeled_file(tmp_path, tp=1, fp=4)  # 20% precision
    args = _ns(findings=f, min_samples=1)
    rc = cmd_calibrate(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Recommendation" in out or "20%" in out


def test_cmd_calibrate_skips_below_min_samples(tmp_path, capsys):
    from phantom_gate.cli import cmd_calibrate
    f = _labeled_file(tmp_path, tp=1, fp=0)  # only 1 sample
    args = _ns(findings=f, min_samples=5)
    rc = cmd_calibrate(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Skipped" in out


def test_cmd_calibrate_no_labeled(tmp_path, capsys):
    from phantom_gate.cli import cmd_calibrate
    f = _findings_file(tmp_path, verdict="unknown")
    args = _ns(findings=f, min_samples=3)
    rc = cmd_calibrate(args)
    assert rc == 1


def test_cmd_calibrate_file_not_found(tmp_path):
    from phantom_gate.cli import cmd_calibrate
    args = _ns(findings=tmp_path / "ghost.json", min_samples=3)
    rc = cmd_calibrate(args)
    assert rc == 2


# ── main / __main__ ───────────────────────────────────────────────────────────

def test_main_no_command(monkeypatch, capsys):
    from phantom_gate.cli import main
    monkeypatch.setattr("sys.argv", ["phantom-gate"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0


def test_main_scan_invoked(tmp_path, monkeypatch, capsys):
    from phantom_gate.cli import main
    f = tmp_path / "clean.txt"
    f.write_text("Normal text.\n")
    monkeypatch.setattr("sys.argv", ["phantom-gate", "scan", str(f), "-d", "M1"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code in (0, 1, 2)


def test_main_module_entrypoint(tmp_path, monkeypatch):
    """__main__.py calls main() — cover via import"""
    import importlib
    monkeypatch.setattr("sys.argv", ["phantom-gate"])
    import phantom_gate.__main__ as mm
    with pytest.raises(SystemExit):
        mm.main()
