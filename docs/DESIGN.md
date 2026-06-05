# phantom-gate Design Document

**Version**: 0.1.0  
**Last Updated**: 2026-06-01

---

## Core Principles

1. **Seed Bank Philosophy**: Provide baseline patterns (M1~M5), users extend in their domain
2. **Zero LLM Cost (Phase 0)**: Regex-based detection → fast, deterministic, accessible
3. **2-Pass Architecture**: Individual detectors → meta-detector conflict resolution
4. **Transparent Limitations**: Stubs/placeholders clearly documented

---

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│           DetectionEngine                   │
│  ┌───────────────────────────────────────┐ │
│  │ Pass 1: Individual Detectors          │ │
│  │  - M1, M2, M3, M4 (parallel-ready)    │ │
│  │  - Returns: List[Finding]             │ │
│  └───────────────────────────────────────┘ │
│              ↓                              │
│  ┌───────────────────────────────────────┐ │
│  │ Pass 2: Meta-Detectors (optional)     │ │
│  │  - Review findings cross-detector     │ │
│  │  - Apply Verdict (ACCEPT/REJECT/...)  │ │
│  └───────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

---

## 2-Pass Design Rationale

### Pass 1: Independent Detection
- Each detector scans content in isolation
- Returns findings with Evidence (line number, excerpt)
- **Parallel-ready**: No inter-detector dependencies

### Pass 2: Meta-Detector Review
- Cross-validator resolves conflicts between detectors
- Example: M1 flags "100% accurate", M2 confirms no prior evidence → strengthen severity
- **Verdict Enum**: `ACCEPT`, `REJECT`, `ADJUST`, `DEFER`

### Why Not Single-Pass?
- Conflict resolution requires full finding set
- Meta-detectors can apply domain-specific logic (e.g., "finance domain allows '100% insured'")

### Closed-Loop Risk
- **Phase 0**: Self-contained (no external ground truth)
- **Accepted Risk**: Meta-detectors may hallucinate → mitigated by explicit rules (regex patterns)
- **Phase 1+**: Integrate source-grounding-audit for ground truth validation

---

## Detector Taxonomy

### M-Series (universal meta-patterns)
- **M1**: Phantom patterns (unfalsifiable claims)
- **M2**: Self-reference loops (backward citation without prior mention)
- **M3**: External dependency assumptions (unchecked API/LLM claims)
- **M4**: Temporal inconsistency (date reversal)
- **M5**: Cross-axis contradiction (multi-file analysis — Phase 1)

### Domain Detectors (project-specific)
- User-defined domain detectors
- Define your own detectors for your project's needs

---

## Verdict Enum Design

Inspired by TruLens "feedback functions" verdict structure.

```python
class Verdict(str, Enum):
    ACCEPT = "accept"      # Finding valid
    REJECT = "reject"      # False positive
    ADJUST = "adjust"      # Severity/category change needed
    DEFER = "defer"        # Needs human review
```

**Usage** (Phase 1):
```python
class ConflictResolver(MetaDetector):
    def review(self, findings: List[Finding], context: DetectionContext) -> List[Finding]:
        # If M1 + M2 both flag same line → ADJUST severity to HIGH
        # If M1 flags but context.metadata["domain"] == "finance" → REJECT
        ...
```

---

## M5 ProjectContext Design (Phase 1)

### Problem
Cross-axis contradictions require multi-file analysis:
- README claims "supports X" but code lacks X implementation
- CHANGELOG date A > B but git log shows B > A

### Solution
```python
@dataclass
class ProjectContext:
    root_path: Path
    files: Dict[str, str]  # path → content
    git_log: Optional[List[GitCommit]]
    metadata: Dict[str, Any]

class M5(BaseDetector):
    def detect(self, context: DetectionContext) -> List[Finding]:
        project = context.project  # ProjectContext
        # Cross-file contradiction detection
        ...
```

**Dependency**: Requires file traversal + git integration → Phase 1

---

## External Validation Integration (Phase 1+)

### Current Limitation
Pass 2 meta-detectors are self-referential (no external ground truth).

### Phase 1 Solution: source-grounding-audit
source-grounding-audit pattern:
1. Extract claims (nouns, numbers, conditions) from Finding.message
2. Trace back to source files (via context.source_path)
3. Mark as "Phantom" if claim not in source
4. Feed back to Verdict → REJECT phantom claims

**Implementation**: New meta-detector `SourceGroundingAuditor(MetaDetector)`

---

## Regex vs. LLM Tradeoff

### Phase 0: Regex-First
- **Pros**: Zero cost, deterministic, fast (<1ms per detector)
- **Cons**: Limited semantic depth (e.g., "never fails in production" vs. "never fails in tests")

### Phase 1+: LLM-Optional
- **Semantic M1**: GPT/Claude judges context ("never fails" in test doc → OK, in user guide → flag)
- **User-configurable**: `M1(use_llm=True, model="gpt-4")`
- **Cost ceiling**: Max $X per 10K lines (configurable)

**Default**: Regex (backward compatible)

---

## Test Strategy

### Phase 0
- Smoke tests: M1~M4 basic patterns
- Regression: Known false positives/negatives
- **Limitation**: Self-generated test cases → AI circular validation

### Phase 1
- **Independent fixtures**: Real-world docs (GitHub issue comments, StackOverflow)
- **External validation**: forge-harness maintainer manual review
- **Coverage**: 90%+ target

---

## Comparison to Similar Libraries

| Library | Focus | Hallucination Approach | Phase 0 Equivalent |
|---|---|---|---|
| **Guardrails AI** | Real-time output validation | Validator functions | M1~M4 = validators |
| **LangCheck** | Metric-based evaluation | Factual consistency scores | M1~M4 = metrics |
| **TruLens** | RAG groundedness | Feedback functions | Pass 2 meta-detectors |
| **DeepEval** | Unit testing | G-Eval + claims | M1~M4 = test assertions |

**phantom-gate positioning**: Lightweight, pip-installable, domain-extensible baseline

### Why not just use X?

**Q: "Can't I just write validators in Guardrails for M1~M4?"**  
A: Yes, technically. But:
- Each validator = separate class boilerplate (`@register_validator`, validation schema, error messages)
- M1~M4 would require 4 validator classes + registry setup (~150 lines)
- phantom-gate: 4 detectors already implemented, single `pip install`

**Q: "Can't LangCheck metrics replace M1~M4?"**  
A: Partially:
- LangCheck focuses on semantic metrics (factual consistency, toxicity) — M1 phantom patterns are regex, not semantic
- No built-in "self-reference loop" detector (M2)
- Metric scores (0.0~1.0) require threshold tuning — phantom-gate = binary detection

**Q: "Can't I combine TruLens + DeepEval?"**  
A: Composition overhead:
- TruLens = RAG feedback functions (requires RAG architecture)
- DeepEval = test assertions (requires pytest integration)
- Combining both for M1~M5 = 2 dependency trees + integration glue
- phantom-gate: zero LLM cost, stdlib-only core (Phase 0)

**Bottom line**: You *can* replicate M1~M5 with existing tools. phantom-gate is for when you want those patterns in 1 `pip install` without boilerplate.

---

## Decision Log

### Why BaseDetector abstract class?
- Enforces `detect(context) -> List[Finding]` contract
- `is_enabled()` / `enable()` / `disable()` for runtime control
- Easy subclassing for domain-specific detectors

### Why DetectionContext dataclass?
- Single object passed to all detectors
- Future-proof: Add `project`, `git_log` without breaking API
- Keyword-only `scan()` args → explicit

### Why Rich over plain print?
- Progress bars for multi-file scans
- Colored severity output (HIGH=red, MEDIUM=yellow)
- Future: Tree view for nested findings

---

## References

### External Patterns
- TruLens feedback functions: [truera/trulens](https://github.com/truera/trulens)
- Guardrails validators: [guardrails-ai/guardrails](https://github.com/guardrails-ai/guardrails)
- LangCheck metrics: [citadel-ai/langcheck](https://github.com/citadel-ai/langcheck)

---

## Future Directions

### Phase 2+
- **Multi-language**: Korean regex patterns (M1 "항상", M2 "위에서 언급한")
- **Domain packs**: `phantom_gate.detectors.finance`, `.healthcare`, `.legal`
- **Web UI**: Batch scan interface (Streamlit or Gradio)
- **Academic**: Publish hallucination taxonomy paper

### Phase 3+
- **Cloud API**: Serverless deployment (AWS Lambda, GCP Functions)
- **IDE integration**: VSCode extension for inline detection
- **Pre-commit hooks**: Auto-scan before commit

---

## Appendix: Verdict Enum Rationale

Verdict design influenced by TruLens feedback functions:

```python
# TruLens example
feedback = Feedback(groundedness_provider.groundedness_measure)
result = feedback(output=llm_output)  # 0.0~1.0 score

# phantom-gate analogy
verdict = meta_detector.review(findings, context)  # Verdict enum
```

**Key difference**:
- TruLens: Continuous score (0.0~1.0)
- phantom-gate: Discrete verdict (ACCEPT/REJECT/ADJUST/DEFER)

**Rationale**: Discrete verdicts map cleanly to CI/CD pass/fail gates.
