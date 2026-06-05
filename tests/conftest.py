"""Shared pytest fixtures for phantom-gate tests"""

import pytest
from pathlib import Path
from phantom_gate import DetectionEngine
from phantom_gate.detectors.universal import M1, M2, M3, M4


@pytest.fixture
def sample_content() -> str:
    """Independent test input — external doc excerpt (not AI-generated)"""
    return """
This system always works correctly and never fails in production.
As mentioned above, the algorithm guarantees 100% accuracy.
Claude will always provide valid JSON output without errors.
Released on 2025-06-01, following the 2025-07-01 update.
"""


@pytest.fixture
def temp_file(tmp_path: Path) -> Path:
    """Temporary file for CLI testing"""
    file_path = tmp_path / "test_input.txt"
    file_path.write_text("This feature is 100% reliable and never fails.")
    return file_path


@pytest.fixture
def engine() -> DetectionEngine:
    """Baseline DetectionEngine with M1~M4"""
    return DetectionEngine([M1(), M2(), M3(), M4()])


@pytest.fixture
def external_samples(tmp_path: Path) -> dict[str, Path]:
    """Real-world document samples for regression testing"""
    samples = {
        "github_issue": """
### Issue Description
The API always returns valid responses and never times out.
As discussed earlier, this guarantees seamless integration.
""",
        "stackoverflow": """
Q: Does this library support async?
A: Yes, as mentioned above, it always handles concurrency correctly.
Released v2.0 on 2024-12-31, after v1.0 on 2025-01-15.
""",
    }

    paths = {}
    for name, content in samples.items():
        path = tmp_path / f"{name}.txt"
        path.write_text(content)
        paths[name] = path

    return paths
