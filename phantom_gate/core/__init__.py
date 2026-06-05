"""Core data models and abstractions"""

from phantom_gate.core.detector import BaseDetector
from phantom_gate.core.models import Evidence, Finding, Severity

__all__ = ["Finding", "Evidence", "Severity", "BaseDetector"]
