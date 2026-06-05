# hallucinate

**Universal AI output hallucination detection library** — PMH (Pay-Meta-Harness) seed bank

## What is this?

`hallucinate` is a **germination kit** that plants Phase 1 hallucination detection patterns (M1~M5 from PMH) into any AI project in seconds. M1~M4 detect runtime hallucinations; M5 detects cross-file contradictions (Python version mismatch across README + pyproject.toml).

```bash
pip install hallucinate
```

→ **Rapid structuring**: months of hallucination engineering → seconds of `pip install`  
→ **Momentum injection**: continues evolving without PMH dependency after planting

## Metaphor: Seed Bank

```
PMH/FH = Seed Bank (universal patterns repository)
    ↓
hallucinate = Germination Kit (pip install = planting seeds)
    ↓
Your Project = Independent Ecosystem (seeds → unique species evolution)
```

## Quick Start

### 1. Install

```bash
pip install hallucinate
```

### 2. Use PMH Universal Detectors (M1~M5)

```python
from hallucinate import DetectionEngine
from hallucinate.detectors.pmh import M1, M2, M3, M4, M5

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
from hallucinate import DetectionEngine, BaseDetector
from hallucinate.detectors.pmh import M1, M2

class P1_MyDomainDetector(BaseDetector):
    """Your domain-specific hallucination pattern"""
    def detect(self, context):
        # Your detection logic
        return []  # Return list of Finding objects

engine = DetectionEngine([
    M1(), M2(),  # PMH seeds (universal)
    P1_MyDomainDetector()  # Your domain (specialized)
])

# Scan content
findings = engine.scan(content="...", source_path="domain.txt")
```

## Architecture

```
hallucinate/
├── core/                   # Data models (Finding, Evidence, Severity)
├── detectors/
│   ├── pmh/               # M1~M5 universal detectors (PMH seed)
│   └── [your-domain]/     # Your domain-specific detectors
├── pipeline/              # DetectionEngine orchestrator
├── feedback/              # TP/FP labeling API
├── adapters/              # I/O bridges (QASP, PMH, custom)
└── cli.py                 # hallucinate scan|label|report|calibrate
```

## Real-World Examples

### QASP (QA Strategy Platform)
- **Planted**: M1~M5 PMH seeds
- **Evolved**: P1~P8 domain detectors (PRD analysis, TC generation)
- **Result**: 218 tests, 99.99% Phase 1 completion

### mate (Mobile QA Automation)
- **Planted**: M1~M5 PMH seeds + locator patterns
- **Evolved**: Insurance domain mobile automation
- **Result**: PR #280 merged (external validation)

### UXW (UX Writing QA)
- **Planted**: dialogue playbook + deliberation
- **Evolved**: Cascade β (autonomous operation)
- **Result**: 3+ users active without PMH dependency

## CLI Usage

```bash
# Scan AI output for hallucinations
hallucinate scan input.txt --output report.json

# Scan with specific detectors only
hallucinate scan input.txt --detectors M1,M2,M3

# Filter by minimum severity (default: info)
hallucinate scan input.txt --severity high

# Note: CLI currently supports scan command only.
# Label/report/calibrate commands are planned for Phase 1.
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
black hallucinate tests
ruff hallucinate tests
```

## Comparison to Similar Libraries

| Library | Focus | Hallucination Approach | When to Use |
|---|---|---|---|
| **Guardrails AI** | Real-time output validation | Validator functions | Production LLM pipelines |
| **LangCheck** | Metric-based evaluation | Factual consistency scores | Multi-language evaluation |
| **TruLens** | RAG groundedness | Feedback functions | RAG applications |
| **DeepEval** | Unit testing | G-Eval + claims | CI/CD integration |
| **hallucinate** | Baseline pattern detection | M1~M5 detectors (regex) | Quick pip install, domain extension |

**hallucinate positioning**: Lightweight, zero LLM cost (Phase 0), domain-extensible seed bank.

## Related Projects

- **PMH (Pay-Meta-Harness)**: Original seed bank (M1~M5 source)
- **FH (forge-harness)**: steel-quench verification methodology
- **QASP**: QA Strategy Platform (P-series detectors)

## License

MIT

## Citation

If you use this library in academic work, please cite:

```bibtex
@software{hallucinate2026,
  author = {chrono.logy},
  title = {hallucinate: Universal AI Output Hallucination Detection},
  year = {2026},
  url = {https://github.com/chrono-code/hallucinate}
}
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

**Seed Bank Philosophy**: Plant once, evolve independently. The seeds (M1~M5) give you a head start, but your project grows its own unique ecosystem.
