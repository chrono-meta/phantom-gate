"""Smoke test: import all main modules"""


def test_import_core_models():
    from phantom_gate.core.models import Verdict, Severity, Evidence, Finding
    assert Verdict.TRUE_POSITIVE == "tp"
    assert Severity.CRITICAL == "critical"


def test_import_detectors():
    from phantom_gate.core.detector import BaseDetector, MetaDetector, ConflictResolver
    assert issubclass(ConflictResolver, MetaDetector)


def test_import_engine():
    from phantom_gate.pipeline.engine import DetectionEngine
    assert DetectionEngine is not None


def test_import_pmh_detectors():
    from phantom_gate.detectors.pmh import M1, M2, M3, M4, M5
    assert M1 is not None
    assert M2 is not None
    assert M3 is not None
    assert M4 is not None
    assert M5 is not None


def test_import_cli():
    from phantom_gate.cli import main, create_parser
    assert main is not None
    assert create_parser is not None
