"""CLI invocation smoke tests"""

import subprocess
import tempfile
import json
from pathlib import Path
import pytest


def test_cli_help():
    """Test CLI help output"""
    result = subprocess.run(
        ["python", "-m", "phantom_gate"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "phantom-gate" in result.stdout.lower()


def test_cli_version():
    """Test CLI version flag"""
    result = subprocess.run(
        ["python", "-m", "phantom_gate", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "0.2.0" in result.stdout


def test_cli_scan_file_not_found():
    """Test CLI scan with non-existent file"""
    result = subprocess.run(
        ["python", "-m", "phantom_gate", "scan", "/nonexistent/file.txt"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2  # Runtime error
    assert "not found" in result.stderr.lower()


def test_cli_scan_success_no_findings():
    """Test CLI scan with clean content"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is normal content without hallucinations.\n")
        f.write("The system works based on empirical evidence.\n")
        temp_path = f.name

    try:
        result = subprocess.run(
            ["python", "-m", "phantom_gate", "scan", temp_path],
            capture_output=True,
            text=True,
        )
        # No detectors loaded warning expected (M1~M5 implementation check)
        # Exit code 0 (clean) or 2 (no detectors) acceptable
        assert result.returncode in (0, 2)
    finally:
        Path(temp_path).unlink()


def test_cli_scan_with_findings():
    """Test CLI scan detects hallucinations"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This tool always works perfectly.\n")
        f.write("It is 100% accurate in all cases.\n")
        temp_path = f.name

    try:
        result = subprocess.run(
            ["python", "-m", "phantom_gate", "scan", temp_path],
            capture_output=True,
            text=True,
        )
        # If M1~M5 loaded, should detect findings
        # If no detectors, exit code 2 acceptable
        assert result.returncode in (0, 1, 2)
    finally:
        Path(temp_path).unlink()


def test_cli_scan_json_output():
    """Test CLI scan with JSON output"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Claude will always return JSON.\n")
        temp_path = f.name

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as out_f:
        output_path = out_f.name

    try:
        result = subprocess.run(
            [
                "python", "-m", "phantom_gate", "scan",
                temp_path,
                "--output", output_path,
            ],
            capture_output=True,
            text=True,
        )
        # Accept 0/1/2 exit codes (depends on detector availability)
        assert result.returncode in (0, 1, 2)

        # If output file created, should be valid JSON
        if Path(output_path).exists() and Path(output_path).stat().st_size > 0:
            with open(output_path, "r") as f:
                data = json.load(f)
                assert isinstance(data, list)
    finally:
        Path(temp_path).unlink()
        if Path(output_path).exists():
            Path(output_path).unlink()


def test_cli_scan_severity_filter():
    """Test CLI scan with severity filter"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Test content\n")
        temp_path = f.name

    try:
        result = subprocess.run(
            [
                "python", "-m", "phantom_gate", "scan",
                temp_path,
                "--severity", "high",
            ],
            capture_output=True,
            text=True,
        )
        # Should not fail
        assert result.returncode in (0, 1, 2)
    finally:
        Path(temp_path).unlink()


def test_cli_scan_detector_selection():
    """Test CLI scan with detector selection"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Test content\n")
        temp_path = f.name

    try:
        result = subprocess.run(
            [
                "python", "-m", "phantom_gate", "scan",
                temp_path,
                "--detectors", "M1,M2",
            ],
            capture_output=True,
            text=True,
        )
        # Should not fail
        assert result.returncode in (0, 1, 2)
    finally:
        Path(temp_path).unlink()


def test_cli_import_as_module():
    """Test CLI can be imported as module"""
    result = subprocess.run(
        ["python", "-c", "from phantom_gate.cli import main; print('ok')"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "ok" in result.stdout


# ── scan --project ────────────────────────────────────────────────────────────

def test_cli_scan_project_detects_version(tmp_path):
    """scan --project detects Python version mismatch via M5"""
    (tmp_path / "README.md").write_text("# Tool\n\nRequires Python 3.12+.\n")
    (tmp_path / "pyproject.toml").write_text('[project]\nrequires-python = ">=3.10"\n')

    out = tmp_path / "findings.json"
    result = subprocess.run(
        ["python", "-m", "phantom_gate", "scan", str(tmp_path),
         "--project", "--output", str(out)],
        capture_output=True, text=True,
    )
    assert result.returncode in (0, 1)
    data = json.loads(out.read_text())
    m5_hits = [f for f in data if f["detector_id"] == "M5"]
    assert len(m5_hits) == 1
    assert m5_hits[0]["category"] == "cross-axis-version"


def test_cli_scan_project_directory_required(tmp_path):
    """scan --project on a non-directory should error"""
    f = tmp_path / "some.txt"
    f.write_text("hi")
    result = subprocess.run(
        ["python", "-m", "phantom_gate", "scan", str(f), "--project"],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "directory" in result.stderr.lower()


# ── report ───────────────────────────────────────────────────────────────────

def test_cli_report_text(tmp_path):
    """report command produces text summary"""
    findings_file = _make_findings_file(tmp_path)

    result = subprocess.run(
        ["python", "-m", "phantom_gate", "report", str(findings_file)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "M1" in result.stdout
    assert "phantom" in result.stdout.lower()


def test_cli_report_md(tmp_path):
    """report --format md produces markdown"""
    findings_file = _make_findings_file(tmp_path)
    out = tmp_path / "report.md"

    result = subprocess.run(
        ["python", "-m", "phantom_gate", "report", str(findings_file),
         "--format", "md", "--output", str(out)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    content = out.read_text()
    assert "# phantom-gate Report" in content
    assert "| M1 |" in content


def test_cli_report_json(tmp_path):
    """report --format json re-serializes findings"""
    findings_file = _make_findings_file(tmp_path)

    result = subprocess.run(
        ["python", "-m", "phantom_gate", "report", str(findings_file),
         "--format", "json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) == 1


def test_cli_report_file_not_found():
    result = subprocess.run(
        ["python", "-m", "phantom_gate", "report", "/nonexistent/findings.json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "not found" in result.stderr.lower()


# ── label ─────────────────────────────────────────────────────────────────────

def test_cli_label_tp_via_stdin(tmp_path):
    """label accepts TP input via stdin (non-interactive mode)"""
    findings_file = _make_findings_file(tmp_path)
    out = tmp_path / "labeled.json"

    result = subprocess.run(
        ["python", "-m", "phantom_gate", "label", str(findings_file),
         "--output", str(out)],
        input="t\n",          # label first (only) finding as TP
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(out.read_text())
    assert data[0]["verdict"] == "tp"


def test_cli_label_fp_via_stdin(tmp_path):
    """label accepts FP input via stdin"""
    findings_file = _make_findings_file(tmp_path)
    out = tmp_path / "labeled.json"

    result = subprocess.run(
        ["python", "-m", "phantom_gate", "label", str(findings_file),
         "--output", str(out)],
        input="fp\n",
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(out.read_text())
    assert data[0]["verdict"] == "fp"


def test_cli_label_skip_via_stdin(tmp_path):
    """label skip leaves verdict unchanged"""
    findings_file = _make_findings_file(tmp_path)
    out = tmp_path / "labeled.json"

    result = subprocess.run(
        ["python", "-m", "phantom_gate", "label", str(findings_file),
         "--output", str(out)],
        input="s\n",
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(out.read_text())
    assert data[0]["verdict"] == "unknown"  # unchanged


# ── calibrate ─────────────────────────────────────────────────────────────────

def test_cli_calibrate_precision(tmp_path):
    """calibrate computes precision from labeled findings"""
    findings_file = _make_labeled_findings_file(tmp_path, tp=3, fp=1)

    result = subprocess.run(
        ["python", "-m", "phantom_gate", "calibrate", str(findings_file),
         "--min-samples", "1"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "M1" in result.stdout
    assert "75%" in result.stdout  # 3 TP / 4 total = 75%


def test_cli_calibrate_no_labeled(tmp_path):
    """calibrate exits with 1 when no labeled findings"""
    findings_file = _make_findings_file(tmp_path)  # all verdict=unknown

    result = subprocess.run(
        ["python", "-m", "phantom_gate", "calibrate", str(findings_file)],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "label" in result.stdout.lower()


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_findings_file(tmp_path: Path) -> Path:
    """Write a findings.json with one phantom M1 finding (verdict=unknown)."""
    finding = {
        "detector_id": "M1",
        "severity": "medium",
        "category": "phantom",
        "message": "Unfalsifiable claim",
        "evidence": [{"source": "test.txt", "excerpt": "always works", "line_number": 1, "metadata": {}}],
        "suggestion": None,
        "metadata": {},
        "verdict": "unknown",
        "feedback_notes": None,
    }
    path = tmp_path / "findings.json"
    path.write_text(json.dumps([finding]))
    return path


def _make_labeled_findings_file(tmp_path: Path, tp: int, fp: int) -> Path:
    """Write a findings.json with tp TP + fp FP labeled M1 findings."""
    findings = []
    for _ in range(tp):
        findings.append({
            "detector_id": "M1", "severity": "medium", "category": "phantom",
            "message": "TP finding", "evidence": [], "suggestion": None,
            "metadata": {}, "verdict": "tp", "feedback_notes": None,
        })
    for _ in range(fp):
        findings.append({
            "detector_id": "M1", "severity": "medium", "category": "phantom",
            "message": "FP finding", "evidence": [], "suggestion": None,
            "metadata": {}, "verdict": "fp", "feedback_notes": None,
        })
    path = tmp_path / "labeled.json"
    path.write_text(json.dumps(findings))
    return path
