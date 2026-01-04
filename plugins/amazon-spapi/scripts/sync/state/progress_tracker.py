"""
Progress Tracker
================

Real-time progress reporting and ETA estimation for sync operations.
"""

import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from ..models import SyncPhase, SyncStatus

logger = logging.getLogger(__name__)


@dataclass
class PhaseProgress:
    """Progress data for a single phase."""
    phase: SyncPhase
    total: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def pending(self) -> int:
        return self.total - self.completed - self.failed - self.skipped

    @property
    def percent_complete(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.completed + self.skipped) / self.total * 100

    @property
    def is_complete(self) -> bool:
        return self.pending == 0 and self.total > 0

    @property
    def duration_seconds(self) -> Optional[float]:
        if not self.started_at:
            return None
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()

    @property
    def items_per_second(self) -> float:
        duration = self.duration_seconds
        if not duration or duration == 0:
            return 0.0
        return self.completed / duration

    @property
    def eta_seconds(self) -> Optional[float]:
        rate = self.items_per_second
        if rate == 0:
            return None
        return self.pending / rate


class ProgressTracker:
    """
    Tracks and reports sync progress across all phases.

    Features:
    - Per-phase progress tracking
    - ETA estimation based on throughput
    - Console progress bar (optional)
    - Callback hooks for UI integration
    """

    def __init__(
        self,
        show_progress_bar: bool = True,
        progress_callback: Optional[Callable[[Dict], None]] = None,
    ):
        """
        Initialize progress tracker.

        Args:
            show_progress_bar: Whether to show console progress bar
            progress_callback: Optional callback for progress updates
        """
        self.show_progress_bar = show_progress_bar
        self.progress_callback = progress_callback

        self._phases: Dict[SyncPhase, PhaseProgress] = {}
        self._current_phase: Optional[SyncPhase] = None
        self._overall_started_at: Optional[datetime] = None
        self._last_progress_time: float = 0
        self._progress_interval: float = 0.5  # Min seconds between updates

    def start_run(self, total_items: int) -> None:
        """Start overall sync run tracking."""
        self._overall_started_at = datetime.now()
        logger.info(f"Starting sync run with {total_items} items")

    def start_phase(self, phase: SyncPhase, total: int) -> None:
        """Start tracking a new phase."""
        self._current_phase = phase
        self._phases[phase] = PhaseProgress(
            phase=phase,
            total=total,
            started_at=datetime.now(),
        )
        logger.info(f"Phase {phase.name}: Starting ({total} items)")
        self._update_progress()

    def complete_phase(self, phase: SyncPhase) -> None:
        """Mark a phase as complete."""
        if phase in self._phases:
            self._phases[phase].completed_at = datetime.now()
            progress = self._phases[phase]
            duration = progress.duration_seconds or 0
            logger.info(
                f"Phase {phase.name}: Complete "
                f"({progress.completed} succeeded, {progress.failed} failed, "
                f"{progress.skipped} skipped) in {duration:.1f}s"
            )
        self._update_progress()

    def increment(
        self,
        phase: Optional[SyncPhase] = None,
        status: SyncStatus = SyncStatus.SUCCESS,
    ) -> None:
        """Increment progress counter for a phase."""
        phase = phase or self._current_phase
        if not phase or phase not in self._phases:
            return

        progress = self._phases[phase]
        if status == SyncStatus.SUCCESS:
            progress.completed += 1
        elif status == SyncStatus.FAILED:
            progress.failed += 1
        elif status == SyncStatus.SKIPPED:
            progress.skipped += 1

        self._update_progress()

    def increment_batch(
        self,
        phase: Optional[SyncPhase] = None,
        success: int = 0,
        failed: int = 0,
        skipped: int = 0,
    ) -> None:
        """Increment progress counters for a batch."""
        phase = phase or self._current_phase
        if not phase or phase not in self._phases:
            return

        progress = self._phases[phase]
        progress.completed += success
        progress.failed += failed
        progress.skipped += skipped

        self._update_progress()

    def _update_progress(self) -> None:
        """Update progress display/callback."""
        now = time.time()
        if now - self._last_progress_time < self._progress_interval:
            return
        self._last_progress_time = now

        if self.show_progress_bar:
            self._print_progress_bar()

        if self.progress_callback:
            self.progress_callback(self.get_progress_summary())

    def _print_progress_bar(self) -> None:
        """Print progress bar to console."""
        if not self._current_phase or self._current_phase not in self._phases:
            return

        progress = self._phases[self._current_phase]
        percent = progress.percent_complete
        completed = progress.completed + progress.skipped
        total = progress.total
        rate = progress.items_per_second
        eta = progress.eta_seconds

        # Build progress bar
        bar_width = 30
        filled = int(bar_width * percent / 100)
        bar = '█' * filled + '░' * (bar_width - filled)

        # Format ETA
        if eta and eta < 3600:
            eta_str = f"ETA: {int(eta // 60)}m {int(eta % 60)}s"
        elif eta:
            eta_str = f"ETA: {eta / 3600:.1f}h"
        else:
            eta_str = "ETA: --"

        # Print progress line (overwrite previous)
        phase_name = self._current_phase.name.replace('_', ' ').title()
        line = f"\r{phase_name}: [{bar}] {percent:5.1f}% ({completed}/{total}) @ {rate:.1f}/s {eta_str}"
        sys.stdout.write(line)
        sys.stdout.flush()

    def finish_progress_bar(self) -> None:
        """Finish progress bar with newline."""
        if self.show_progress_bar:
            print()  # Newline after progress bar

    def get_phase_progress(self, phase: SyncPhase) -> Optional[PhaseProgress]:
        """Get progress for a specific phase."""
        return self._phases.get(phase)

    def get_progress_summary(self) -> Dict:
        """Get summary of all progress."""
        phases = {}
        for phase, progress in self._phases.items():
            phases[phase.name] = {
                "total": progress.total,
                "completed": progress.completed,
                "failed": progress.failed,
                "skipped": progress.skipped,
                "pending": progress.pending,
                "percent": progress.percent_complete,
                "rate": progress.items_per_second,
                "eta_seconds": progress.eta_seconds,
            }

        overall_duration = None
        if self._overall_started_at:
            overall_duration = (datetime.now() - self._overall_started_at).total_seconds()

        return {
            "current_phase": self._current_phase.name if self._current_phase else None,
            "overall_duration_seconds": overall_duration,
            "phases": phases,
        }

    def get_overall_stats(self) -> Dict:
        """Get overall statistics across all phases."""
        total_completed = sum(p.completed for p in self._phases.values())
        total_failed = sum(p.failed for p in self._phases.values())
        total_skipped = sum(p.skipped for p in self._phases.values())

        duration = None
        if self._overall_started_at:
            duration = (datetime.now() - self._overall_started_at).total_seconds()

        return {
            "total_completed": total_completed,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "duration_seconds": duration,
            "phases_completed": sum(1 for p in self._phases.values() if p.is_complete),
            "phases_total": len(self._phases),
        }

    def log_summary(self) -> None:
        """Log final summary of sync run."""
        stats = self.get_overall_stats()
        duration = stats.get('duration_seconds') or 0  # Handle None case

        # Format duration
        if duration < 60:
            duration_str = f"{duration:.1f} seconds"
        elif duration < 3600:
            duration_str = f"{duration / 60:.1f} minutes"
        else:
            duration_str = f"{duration / 3600:.1f} hours"

        logger.info("=" * 50)
        logger.info("SYNC RUN COMPLETE")
        logger.info("=" * 50)
        logger.info(f"Duration: {duration_str}")
        logger.info(f"Completed: {stats['total_completed']}")
        logger.info(f"Failed: {stats['total_failed']}")
        logger.info(f"Skipped: {stats['total_skipped']}")

        # Per-phase breakdown
        logger.info("-" * 50)
        for phase, progress in self._phases.items():
            phase_duration = progress.duration_seconds or 0
            logger.info(
                f"  {phase.name}: {progress.completed}/{progress.total} "
                f"({progress.percent_complete:.1f}%) in {phase_duration:.1f}s"
            )
        logger.info("=" * 50)
