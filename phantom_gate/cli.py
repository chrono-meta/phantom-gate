"""hallucinate CLI — AI output hallucination detector."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SEVERITY_ORDER = ["info", "low", "medium", "high", "critical"]


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phantom-gate",
        description="Detect hallucinations in AI-generated outputs",
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s 0.2.0"
    )

    sub = parser.add_subparsers(dest="command")

    # ── scan ────────────────────────────────────────────────────────────────
    scan_p = sub.add_parser("scan", help="Scan a file (or project directory) for hallucinations")
    scan_p.add_argument("file", type=Path, help="File to scan, or project root when --project is set")
    scan_p.add_argument(
        "--project", action="store_true",
        help="Treat FILE as a project directory and run project-scoped detectors (M5+)",
    )
    scan_p.add_argument(
        "--detectors", "-d",
        default="all",
        help="Comma-separated detector names (default: all)",
    )
    scan_p.add_argument(
        "--output", "-o",
        type=Path,
        help="Output JSON report path",
    )
    scan_p.add_argument(
        "--severity", "-s",
        choices=_SEVERITY_ORDER,
        default="info",
        help="Minimum severity to report (default: info)",
    )

    # ── report ───────────────────────────────────────────────────────────────
    report_p = sub.add_parser("report", help="Display a summary report from a findings JSON file")
    report_p.add_argument("findings", type=Path, help="Findings JSON file (from scan --output)")
    report_p.add_argument(
        "--format", "-f",
        choices=["text", "json", "md"],
        default="text",
        help="Output format (default: text)",
    )
    report_p.add_argument("--output", "-o", type=Path, help="Write report to file instead of stdout")

    # ── label ────────────────────────────────────────────────────────────────
    label_p = sub.add_parser(
        "label",
        help="Interactively label findings as TP/FP and save updated report",
    )
    label_p.add_argument("findings", type=Path, help="Findings JSON file to label")
    label_p.add_argument(
        "--output", "-o",
        type=Path,
        help="Save labeled findings to this path (default: overwrite input)",
    )

    # ── calibrate ────────────────────────────────────────────────────────────
    calibrate_p = sub.add_parser(
        "calibrate",
        help="Compute detector precision/recall from labeled findings",
    )
    calibrate_p.add_argument("findings", type=Path, help="Labeled findings JSON file")
    calibrate_p.add_argument(
        "--min-samples", type=int, default=3,
        help="Minimum labeled samples per detector to report (default: 3)",
    )

    return parser


# ──────────────────────────────────────────────────────────────────────────────
# scan
# ──────────────────────────────────────────────────────────────────────────────

def cmd_scan(args: argparse.Namespace) -> int:
    """Execute scan command."""
    from phantom_gate.core.models import Severity
    from phantom_gate.pipeline.engine import DetectionEngine

    if not args.file.exists():
        print(f"Error: path not found: {args.file}", file=sys.stderr)
        return 2

    try:
        detectors = _load_detectors(args.detectors)
    except Exception as e:
        print(f"Error loading detectors: {e}", file=sys.stderr)
        return 2

    if not detectors:
        print("Error: no detectors loaded", file=sys.stderr)
        return 2

    engine = DetectionEngine(detectors)

    try:
        if args.project:
            if not args.file.is_dir():
                print(f"Error: --project requires a directory path, got: {args.file}", file=sys.stderr)
                return 2
            findings = engine.scan_project(args.file)
        else:
            if not args.file.is_file():
                print(f"Error: not a file: {args.file}  (use --project to scan a directory)", file=sys.stderr)
                return 2
            content = args.file.read_text(encoding="utf-8")
            findings = engine.scan(content, source_path=str(args.file))
    except Exception as e:
        print(f"Error during scan: {e}", file=sys.stderr)
        return 2

    # severity filter
    min_sev = Severity(args.severity.lower())
    min_idx = _SEVERITY_ORDER.index(min_sev.value)
    findings = [f for f in findings if _SEVERITY_ORDER.index(f.severity.value) >= min_idx]

    if args.output:
        try:
            report = [f.model_dump(mode="json") for f in findings]
            args.output.write_text(json.dumps(report, indent=2))
            print(f"Report written to {args.output} ({len(findings)} findings)")
        except Exception as e:
            print(f"Error writing report: {e}", file=sys.stderr)
            return 2
    else:
        _print_findings(findings)

    has_high = any(f.severity.value in ("high", "critical") for f in findings)
    return 1 if has_high else 0


# ──────────────────────────────────────────────────────────────────────────────
# report
# ──────────────────────────────────────────────────────────────────────────────

def cmd_report(args: argparse.Namespace) -> int:
    """Display a summary report from a findings JSON file."""

    findings, err = _load_findings_file(args.findings)
    if err:
        return err

    if args.format == "json":
        text = json.dumps([f.model_dump(mode="json") for f in findings], indent=2)
    elif args.format == "md":
        text = _render_report_md(findings)
    else:
        text = _render_report_text(findings)

    if args.output:
        try:
            args.output.write_text(text, encoding="utf-8")
            print(f"Report written to {args.output}")
        except Exception as e:
            print(f"Error writing report: {e}", file=sys.stderr)
            return 2
    else:
        print(text)

    return 0


def _render_report_text(findings) -> str:
    from collections import Counter

    lines = []
    total = len(findings)
    lines.append(f"{'─' * 50}")
    lines.append(f"  phantom-gate report — {total} finding(s)")
    lines.append(f"{'─' * 50}")

    if not findings:
        lines.append("  ✅ No hallucinations found.")
        return "\n".join(lines)

    sev_counts = Counter(f.severity.value for f in findings)
    det_counts = Counter(f.detector_id for f in findings)
    cat_counts = Counter(f.category for f in findings)
    verdict_counts = Counter(f.verdict.value for f in findings)

    lines.append("\nBy Severity:")
    for sev in reversed(_SEVERITY_ORDER):
        if sev in sev_counts:
            lines.append(f"  {sev.upper():10s} {sev_counts[sev]:>4}")

    lines.append("\nBy Detector:")
    for det, cnt in sorted(det_counts.items()):
        lines.append(f"  {det:12s} {cnt:>4}")

    lines.append("\nBy Category:")
    for cat, cnt in sorted(cat_counts.items()):
        lines.append(f"  {cat:30s} {cnt:>4}")

    lines.append("\nVerdict Breakdown:")
    for verdict, cnt in sorted(verdict_counts.items()):
        lines.append(f"  {verdict:12s} {cnt:>4}")

    lines.append(f"\n{'─' * 50}")
    return "\n".join(lines)


def _render_report_md(findings) -> str:
    from collections import Counter

    total = len(findings)
    lines = [f"# phantom-gate Report\n\n**Total findings:** {total}\n"]

    if not findings:
        lines.append("✅ No hallucinations found.")
        return "\n".join(lines)

    sev_counts = Counter(f.severity.value for f in findings)
    det_counts = Counter(f.detector_id for f in findings)

    lines.append("## By Severity\n")
    lines.append("| Severity | Count |")
    lines.append("|---|---|")
    for sev in reversed(_SEVERITY_ORDER):
        if sev in sev_counts:
            lines.append(f"| {sev.upper()} | {sev_counts[sev]} |")

    lines.append("\n## By Detector\n")
    lines.append("| Detector | Count |")
    lines.append("|---|---|")
    for det, cnt in sorted(det_counts.items()):
        lines.append(f"| {det} | {cnt} |")

    lines.append("\n## Findings\n")
    for i, f in enumerate(findings, 1):
        lines.append(f"### {i}. [{f.severity.value.upper()}] {f.detector_id} — {f.category}\n")
        lines.append(f"**Message:** {f.message}\n")
        if f.evidence:
            for e in f.evidence:
                loc = f" L{e.line_number}" if e.line_number else ""
                lines.append(f"- `{e.source}{loc}`: {e.excerpt[:100]}")
        if f.suggestion:
            lines.append(f"\n**Suggestion:** {f.suggestion}")
        lines.append("")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# label
# ──────────────────────────────────────────────────────────────────────────────

def cmd_label(args: argparse.Namespace) -> int:
    """Interactively label findings as TP/FP."""
    from phantom_gate.core.models import Verdict

    findings, err = _load_findings_file(args.findings)
    if err:
        return err

    if not findings:
        print("No findings to label.")
        return 0

    is_interactive = sys.stdin.isatty() and sys.stdout.isatty()
    labeled_count = 0

    print(f"Labeling {len(findings)} finding(s). Press Ctrl+C to stop.\n")

    try:
        for i, finding in enumerate(findings, 1):
            print(f"[{i}/{len(findings)}] [{finding.severity.value.upper()}] "
                  f"{finding.detector_id} — {finding.category}")
            print(f"  {finding.message}")
            for e in finding.evidence:
                loc = f" L{e.line_number}" if e.line_number else ""
                print(f"  → {e.source}{loc}: {e.excerpt[:80]}")
            print(f"  Current verdict: {finding.verdict.value}")

            if is_interactive:
                try:
                    raw = input("  Label [t]p / [f]p / [s]kip: ").strip().lower()
                except EOFError:
                    raw = "s"
            else:
                # Non-interactive: read one line from stdin per finding
                raw_line = sys.stdin.readline().strip().lower()
                raw = raw_line if raw_line else "s"

            if raw in ("t", "tp", "true_positive"):
                finding.verdict = Verdict.TRUE_POSITIVE
                labeled_count += 1
            elif raw in ("f", "fp", "false_positive"):
                finding.verdict = Verdict.FALSE_POSITIVE
                labeled_count += 1
            else:
                print("  (skipped)")
            print()
    except KeyboardInterrupt:
        print("\n\nLabeling interrupted.")

    out_path = args.output or args.findings
    try:
        data = [f.model_dump(mode="json") for f in findings]
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Labeled {labeled_count}/{len(findings)} finding(s). Saved to {out_path}")
    except Exception as e:
        print(f"Error saving: {e}", file=sys.stderr)
        return 2

    return 0


# ──────────────────────────────────────────────────────────────────────────────
# calibrate
# ──────────────────────────────────────────────────────────────────────────────

def cmd_calibrate(args: argparse.Namespace) -> int:
    """Compute detector precision from labeled findings."""
    from collections import defaultdict

    from phantom_gate.core.models import Verdict

    findings, err = _load_findings_file(args.findings)
    if err:
        return err

    labeled = [f for f in findings if f.verdict in (Verdict.TRUE_POSITIVE, Verdict.FALSE_POSITIVE)]
    if not labeled:
        print("No labeled findings found. Run 'phantom-gate label' first.")
        return 1

    # Aggregate per detector
    stats: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0})
    for f in labeled:
        if f.verdict == Verdict.TRUE_POSITIVE:
            stats[f.detector_id]["tp"] += 1
        else:
            stats[f.detector_id]["fp"] += 1

    print(f"{'─' * 60}")
    print(f"  Calibration Report — {len(labeled)} labeled finding(s)")
    print(f"{'─' * 60}")
    print(f"  {'Detector':<12} {'Labeled':>8} {'TP':>6} {'FP':>6} {'Precision':>10}")
    print(f"  {'─' * 10:<12} {'─' * 7:>8} {'─' * 4:>6} {'─' * 4:>6} {'─' * 9:>10}")

    recommendations = []
    for det_id, s in sorted(stats.items()):
        total = s["tp"] + s["fp"]
        if total < args.min_samples:
            continue
        precision = s["tp"] / total * 100
        flag = "⚠️ " if precision < 70 else "  "
        print(f"  {flag}{det_id:<10} {total:>8} {s['tp']:>6} {s['fp']:>6} {precision:>9.0f}%")
        if precision < 70:
            recommendations.append(
                f"  • {det_id}: precision {precision:.0f}% — consider stricter regex patterns"
            )

    skipped = sum(1 for d, s in stats.items() if s["tp"] + s["fp"] < args.min_samples)
    if skipped:
        print(f"\n  (Skipped {skipped} detector(s) with < {args.min_samples} labeled samples)")

    if recommendations:
        print(f"\n{'─' * 60}")
        print("  Recommendations:")
        for r in recommendations:
            print(r)

    print(f"{'─' * 60}")
    return 0


# ──────────────────────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────────────────────

def _load_detectors(spec: str):
    """Load detectors by comma-separated names or 'all'."""
    from phantom_gate.detectors.pmh import M1, M2, M3, M4, M5

    available = {"M1": M1, "M2": M2, "M3": M3, "M4": M4, "M5": M5}

    if spec == "all":
        return [cls() for cls in available.values()]

    names = [n.strip() for n in spec.split(",")]
    detectors = []
    for name in names:
        if name not in available:
            print(f"Warning: unknown detector '{name}', skipping", file=sys.stderr)
            continue
        detectors.append(available[name]())
    return detectors


def _load_findings_file(path: Path):
    """Load findings from a JSON file. Returns (findings, error_code)."""
    from phantom_gate.core.models import Finding

    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        return None, 2
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        findings = [Finding.model_validate(item) for item in raw]
        return findings, None
    except Exception as e:
        print(f"Error reading findings: {e}", file=sys.stderr)
        return None, 2


def _print_findings(findings):
    """Pretty-print findings to stdout."""
    if not findings:
        print("✅ No hallucinations detected.")
        return

    print(f"⚠️  {len(findings)} finding(s) detected:\n")
    for i, f in enumerate(findings, 1):
        print(f"  [{f.severity.value.upper()}] {f.detector_id}: {f.message}")
        for e in f.evidence:
            loc = f"  L{e.line_number}" if e.line_number else ""
            print(f"    → {e.source}{loc}: {e.excerpt[:80]}")
        print()


# ──────────────────────────────────────────────────────────────────────────────
# entrypoint
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """CLI entry point.

    Exit codes:
      0: No findings (or only INFO/LOW/MEDIUM)
      1: HIGH or CRITICAL findings detected
      2: Error during execution
    """
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "scan": cmd_scan,
        "report": cmd_report,
        "label": cmd_label,
        "calibrate": cmd_calibrate,
    }
    handler = dispatch.get(args.command)
    if handler:
        sys.exit(handler(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
