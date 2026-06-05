# phantom-gate Development Roadmap

## Phase 0 (v0.1.0 — Released 2026-06-01)

Status: **Released**

### Features
- ✅ M1~M4 baseline detectors (regex-based, zero LLM cost)
- ✅ M5 stub (multi-file analysis placeholder)
- ✅ DetectionEngine with 2-pass architecture
- ✅ CLI: `phantom-gate scan`
- ✅ Pydantic data models (Finding, Evidence, Severity)
- ✅ Rich console output

### Limitations
- M5 (cross-axis contradiction) required ProjectContext — Phase 1
- CLI commands `label`/`report`/`calibrate` not implemented
- No CI/CD pipeline (Python 3.13+ untested)
- No LLM-based detection (cost optimization)

---

## Phase 1 (v0.2.0 — In Progress)

Status: **In Progress**

### Done
- ✅ **M5 implementation**: Python version contradiction across project files
- ✅ **ProjectContext**: `load_project()` + `scan_project()` API
- ✅ **Scope-aware DetectionEngine**: file vs. project detector routing

### Remaining
- [ ] **CLI expansion**: `label`, `report`, `calibrate` commands
- [ ] **CI/CD**: GitHub Actions with Python 3.10~3.13 matrix
- [ ] **Pytest fixtures**: Expand test coverage to 90%+
- [ ] **Feedback loop**: TP/FP labeling API for detector tuning

---

## Phase 2 (Target: Q4 2026+)

### Advanced Detection
- **LLM-based detectors**: Optional GPT/Claude integration for semantic analysis
  - Cost vs. accuracy tradeoff documented
  - User-configurable (fallback to regex)
- **Domain adapters**: Pre-built detector packs (finance, healthcare, legal)

### Performance
- **Caching**: Detector result caching for repeated scans
- **Parallel execution**: Multi-core detector orchestration

### Ecosystem
- **Pre-commit hooks**: Auto-scan before commit
- **CI integrations**: GitHub Actions, GitLab CI templates
- **IDE plugins**: VSCode extension for inline detection

---

## Backlog (Phase 3+)

- Multi-language support (Korean, Japanese, French)
- Web UI for batch scanning
- Cloud API deployment (serverless)
- Academic paper publication (hallucination taxonomy)

---

## Version History

| Version | Date | Highlights |
|---|---|---|
| 0.2.0 | 2026-06-05 | Phase 1 — M5 Python version contradiction + ProjectContext + scan_project() |
| 0.1.0 | 2026-06-01 | Phase 0 baseline — M1~M4 + CLI scan |

---

## Decision Log

### Why regex-first (Phase 0)?
- **Zero LLM cost**: Accessible to all users
- **Deterministic**: Reproducible results
- **Fast**: Millisecond latency
- **Phase 1+ LLM**: Optional for semantic depth

### Why M5 stub in v0.1?
- **Transparent limitation**: README clearly states stub status
- **Seed bank metaphor**: Users extend M5 in their domain
- **External validation**: forge-harness maintainer review confirmed stub is standard practice (2026-06-01)

### Why 2-pass architecture?
- **Pass 1**: Independent detector execution (parallel-ready)
- **Pass 2**: Meta-detector conflict resolution (Verdict enum)
- **Closed-loop risk accepted**: Phase 0 self-contained, Phase 1+ integrates external ground truth
