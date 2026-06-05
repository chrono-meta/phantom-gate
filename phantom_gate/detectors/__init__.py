"""phantom-gate detector registry.

Built-in detectors (universal):
    from phantom_gate.detectors.pmh import M1, M2, M3, M4, M5

Domain-specific detectors live in each project (B-pattern):
    # In your project:
    from phantom_gate.core.detector import BaseDetector, DetectionContext
    from phantom_gate.core.models import Finding

    class MyDetector(BaseDetector):
        def detect(self, context: DetectionContext) -> list[Finding]: ...
"""
