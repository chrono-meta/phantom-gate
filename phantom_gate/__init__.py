"""phantom-gate - Universal AI output hallucination detection library

Universal meta-harness seed bank for rapid structuring + momentum injection.
"""

__version__ = "0.2.0"

from phantom_gate.core.detector import BaseDetector
from phantom_gate.core.models import Evidence, Finding, ProjectContext, Severity
from phantom_gate.pipeline.engine import DetectionEngine, load_project

__all__ = [
    "Finding",
    "Evidence",
    "Severity",
    "ProjectContext",
    "BaseDetector",
    "DetectionEngine",
    "load_project",
]
