"""Detection engine - orchestrates multiple detectors with 2-pass architecture"""

from pathlib import Path
from typing import Dict, List, Optional, Union

from rich.console import Console
from rich.progress import Progress

from phantom_gate.core.detector import BaseDetector, DetectionContext, MetaDetector
from phantom_gate.core.models import Finding, ProjectContext

# Files loaded by default for project-scoped scanning (Phase 1)
_DEFAULT_PROJECT_FILES = [
    "README.md",
    "README.rst",
    "README.txt",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    ".python-version",
]


_MAX_FILE_BYTES = 1 * 1024 * 1024  # 1 MB per file — prevent memory exhaustion on large repos


def load_project(
    root_path: Union[str, Path],
    extra_files: Optional[List[str]] = None,
    max_file_bytes: int = _MAX_FILE_BYTES,
) -> ProjectContext:
    """Load project files into a ProjectContext for M5 scanning.

    Loads a curated set of project metadata files (README, pyproject.toml, etc.).
    Missing or unreadable files are silently skipped.
    Files exceeding ``max_file_bytes`` are skipped to prevent memory exhaustion.

    Scanned files (default): README.md, README.rst, README.txt,
    pyproject.toml, setup.cfg, setup.py, .python-version

    Args:
        root_path: Absolute path to the project root directory.
        extra_files: Additional relative paths to include beyond the defaults.
        max_file_bytes: Maximum file size to load in bytes (default: 1 MB).

    Returns:
        ProjectContext with loaded files.
    """
    root = Path(root_path).resolve()
    target_files = list(_DEFAULT_PROJECT_FILES)
    if extra_files:
        target_files.extend(extra_files)

    files: Dict[str, str] = {}
    for rel_path in target_files:
        abs_path = root / rel_path
        if abs_path.is_file():
            try:
                if abs_path.stat().st_size > max_file_bytes:
                    continue  # Skip oversized files silently
                files[rel_path] = abs_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass  # Silently skip unreadable files

    return ProjectContext(root_path=root, files=files)

class DetectionEngine:
    """Orchestrates multiple hallucination detectors with 2-pass architecture

    Pass 1: Individual detectors scan content independently
    Pass 2: Meta-detectors review and adjust findings cross-detector

    Detectors with ``scope = "file"`` (default) are invoked per file.
    Detectors with ``scope = "project"`` are invoked once per project scan
    (only from ``scan_project()``).

    Example:
        >>> from phantom_gate import DetectionEngine
        >>> from phantom_gate.detectors.pmh import M1, M2
        >>> engine = DetectionEngine([M1(), M2()])
        >>> findings = engine.scan("AI output text...")
    """

    def __init__(
        self,
        detectors: List[BaseDetector],
        meta_detectors: Optional[List[MetaDetector]] = None,
        verbose: bool = False,
    ):
        self.detectors = detectors
        self.meta_detectors = meta_detectors or []
        self.verbose = verbose
        self.console = Console() if verbose else None

    def scan(
        self,
        content: str,
        *,
        source_path: Optional[str] = None,
        metadata: Optional[dict] = None,
        show_progress: bool = False,
    ) -> List[Finding]:
        """Scan content with 2-pass architecture

        Args:
            content: Text to scan for hallucinations
            source_path: Source identifier (file path, URL, etc.)
            metadata: Additional context metadata
            show_progress: Show progress bar

        Returns:
            List of findings after both passes
        """
        # Pass 1: Individual detector execution
        context = DetectionContext(
            content=content,
            source_path=source_path or "<stdin>",
            metadata=metadata or {},
        )
        findings: List[Finding] = []

        enabled_file_detectors = [
            d for d in self.detectors if d.is_enabled() and d.scope == "file"
        ]

        if show_progress and self.console:
            with Progress() as progress:
                task = progress.add_task(
                    "[cyan]Pass 1: Running detectors...",
                    total=len(enabled_file_detectors),
                )
                for detector in enabled_file_detectors:
                    detected = detector.detect(context)
                    findings.extend(detected)
                    progress.update(task, advance=1)
        else:
            for detector in enabled_file_detectors:
                if self.verbose:
                    self.console.print(f"Running {detector.detector_id}...")
                detected = detector.detect(context)
                findings.extend(detected)
                if self.verbose and detected:
                    self.console.print(f"  → {len(detected)} finding(s)")

        # Pass 2: Meta-detector cross-validation
        if self.meta_detectors:
            if self.verbose:
                self.console.print(
                    f"[yellow]Pass 2: Running {len(self.meta_detectors)} meta-detectors..."
                )
            for meta in self.meta_detectors:
                findings = meta.review(findings, context)

        return findings

    def scan_project(
        self,
        root_path: Union[str, Path],
        *,
        extra_files: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
    ) -> List[Finding]:
        """Scan a project directory for cross-file contradictions (M5+).

        File-scoped detectors run on each loaded file.
        Project-scoped detectors (e.g. M5) run once with full ProjectContext.
        Meta-detectors are applied to the combined finding list.

        Args:
            root_path: Path to the project root directory.
            extra_files: Additional relative file paths to include.
            metadata: Extra metadata injected into each DetectionContext.

        Returns:
            Combined findings from all file and project detectors.
        """
        project = load_project(root_path, extra_files=extra_files)
        all_findings: List[Finding] = []
        extra_meta = metadata or {}

        file_detectors = [d for d in self.detectors if d.is_enabled() and d.scope == "file"]
        project_detectors = [d for d in self.detectors if d.is_enabled() and d.scope == "project"]

        # Run file-scoped detectors on each loaded file
        for rel_path, content in project.files.items():
            ctx = DetectionContext(
                content=content,
                source_path=rel_path,
                metadata={"project_root": str(project.root_path), **extra_meta},
                project=project,
            )
            for detector in file_detectors:
                all_findings.extend(detector.detect(ctx))

        # Run project-scoped detectors once with a synthetic context
        if project_detectors:
            project_ctx = DetectionContext(
                content="",
                source_path="<project>",
                metadata={"project_root": str(project.root_path), **extra_meta},
                project=project,
            )
            for detector in project_detectors:
                all_findings.extend(detector.detect(project_ctx))

        # Pass 2: Meta-detectors on combined findings
        if self.meta_detectors and all_findings:
            combined_ctx = DetectionContext(
                content="",
                source_path="<project>",
                metadata=extra_meta,
                project=project,
            )
            for meta in self.meta_detectors:
                all_findings = meta.review(all_findings, combined_ctx)

        return all_findings

    def get_enabled_detectors(self) -> List[BaseDetector]:
        """Get list of currently enabled detectors"""
        return [d for d in self.detectors if d.is_enabled()]

    def enable_detector(self, detector_id: str):
        """Enable a specific detector by ID"""
        for detector in self.detectors:
            if detector.detector_id == detector_id:
                detector.enable()
                return
        raise ValueError(f"Detector {detector_id} not found")

    def disable_detector(self, detector_id: str):
        """Disable a specific detector by ID"""
        for detector in self.detectors:
            if detector.detector_id == detector_id:
                detector.disable()
                return
        raise ValueError(f"Detector {detector_id} not found")

    def __repr__(self) -> str:
        enabled = sum(1 for d in self.detectors if d.is_enabled())
        return f"<DetectionEngine: {enabled}/{len(self.detectors)} detectors enabled>"
