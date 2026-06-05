# phantom-gate

**Universal AI output hallucination detection library** — a portable seed bank of baseline detectors

## What is this?

`phantom-gate` is a **germination kit** that plants baseline hallucination detection patterns (M1~M5) into any AI project in seconds. M1~M4 detect runtime hallucinations; M5 detects cross-file contradictions (Python version mismatch across README + pyproject.toml).

```bash
pip install git+https://github.com/chrono-meta/phantom-gate.git
```

→ **Rapid structuring**: months of hallucination engineering → seconds of install
→ **Momentum injection**: continues evolving independently after planting

## Metaphor: Seed Bank

```
Universal patterns = Seed Bank (reusable detector repository)
    ↓
phantom-gate = Germination Kit (install = planting seeds)
    ↓
Your Project = Independent Ecosystem (seeds → unique species evolution)
```

## Quick Start

### 1. Install

```bash
pip install git+https://github.com/chrono-meta/phantom-gate.git
```

### 2. Use Universal Detectors (M1~M5)

```python
from phantom_gate import DetectionEngine
from phantom_gate.detectors.universal import M1, M2, M3, M4, M5

engine = DetectionEngine([
    M1(),  # Phantom patterns (unfalsifiable claims)
    M2(),  # Self-reference loops
    M3(),  # External dependency assumptions
    M4(),  # Temporal inconsistency
    M5(),  # Cross-axis contradictions (Python version mismatch across files)
])

# Note: scan() uses keyword-only arguments
findings = engine.scan(content="Your AI output text...", source_path="output.txt")
for finding in findings:
    print(f"{finding.severity}: {finding.message}")
```

### 3. Extend with Domain-Specific Detectors

```python
# Your project: add domain detectors
from phantom_gate import DetectionEngine, BaseDetector
from phantom_gate.detectors.universal import M1, M2

class MyDomainDetector(BaseDetector):
    """Your domain-specific hallucination pattern"""
    def detect(self, context):
        # Your detection logic
        return []  # Return list of Finding objects

engine = DetectionEngine([
    M1(), M2(),  # universal seeds
    MyDomainDetector()  # Your domain (specialized)
])

# Scan content
findings = engine.scan(content="...", source_path="domain.txt")
```

## Architecture

```
phantom_gate/
├── core/                   # Data models (Finding, Evidence, Severity)
├── detectors/
│   ├── universal/         # M1~M5 universal detectors
│   └── [your-domain]/     # Your domain-specific detectors
├── pipeline/              # DetectionEngine orchestrator
└── cli.py                 # phantom-gate scan|label|report|calibrate
```

## CLI Usage

```bash
# Scan AI output for hallucinations
phantom-gate scan input.txt --output report.json

# Scan with specific detectors only
phantom-gate scan input.txt --detectors M1,M2,M3

# Filter by minimum severity (default: info)
phantom-gate scan input.txt --severity high
```

### Exit Codes
- `0`: No hallucinations or only INFO/LOW/MEDIUM findings
- `1`: HIGH or CRITICAL findings detected
- `2`: Error during execution (file not found, scan failure, etc.)

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black phantom_gate tests
ruff phantom_gate tests
```

## Comparison to Similar Libraries

| Library | Focus | Hallucination Approach | When to Use |
|---|---|---|---|
| **Guardrails AI** | Real-time output validation | Validator functions | Production LLM pipelines |
| **LangCheck** | Metric-based evaluation | Factual consistency scores | Multi-language evaluation |
| **TruLens** | RAG groundedness | Feedback functions | RAG applications |
| **DeepEval** | Unit testing | G-Eval + claims | CI/CD integration |
| **phantom-gate** | Baseline pattern detection | M1~M5 detectors (regex) | Quick install, domain extension |

**phantom-gate positioning**: Lightweight, zero LLM cost (Phase 0), domain-extensible seed bank.

## License

MIT

## Citation

If you use this library in academic work, please cite:

```bibtex
@software{phantomgate2026,
  author = {chrono-meta},
  title = {phantom-gate: Universal AI Output Hallucination Detection},
  year = {2026},
  url = {https://github.com/chrono-meta/phantom-gate}
}
```

---

**Seed Bank Philosophy**: Plant once, evolve independently. The seeds (M1~M5) give you a head start, but your project grows its own unique ecosystem.
