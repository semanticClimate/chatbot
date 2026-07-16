"""TTY progress bars for long encyclopedia pipeline steps (stdlib only)."""

from __future__ import annotations

import sys
import time
from typing import Optional, TextIO


def stderr_is_tty() -> bool:
    return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()


class ProgressBar:
    """Simple ASCII progress bar; falls back to sparse line updates when not a TTY."""

    def __init__(
        self,
        total: int,
        *,
        label: str = "",
        file: TextIO = sys.stderr,
        width: int = 32,
        min_interval_s: float = 0.1,
    ) -> None:
        self.total = max(0, int(total))
        self.label = label.strip()
        self.file = file
        self.width = width
        self.min_interval_s = min_interval_s
        self.n = 0
        self._tty = stderr_is_tty() and self.total > 0
        self._last_draw = 0.0
        if self._tty:
            self._draw(force=True)

    def update(self, n: int = 1) -> None:
        if self.total <= 0:
            return
        self.n = min(self.total, self.n + n)
        now = time.monotonic()
        if self._tty and (now - self._last_draw) < self.min_interval_s and self.n < self.total:
            return
        self._draw()
        self._last_draw = now

    def close(self) -> None:
        if self.total <= 0:
            return
        self.n = self.total
        self._draw(force=True)
        if self._tty:
            self.file.write("\n")
            self.file.flush()

    def _draw(self, force: bool = False) -> None:
        if not self._tty:
            if force or self.n == self.total or self.n % max(1, self.total // 20) == 0:
                pct = (100.0 * self.n / self.total) if self.total else 100.0
                prefix = f"{self.label}: " if self.label else ""
                print(f"  {prefix}{self.n}/{self.total} ({pct:.0f}%)", file=self.file, flush=True)
            return

        frac = self.n / self.total
        filled = int(self.width * frac)
        bar = "=" * filled + "-" * (self.width - filled)
        pct = int(frac * 100)
        prefix = f"{self.label} " if self.label else ""
        line = f"\r  {prefix}[{bar}] {pct:3d}% ({self.n}/{self.total})"
        self.file.write(line)
        self.file.flush()


class PipelineProgress:
    """Five pipeline stages with a bar for the long annotate step."""

    STAGES = (
        "prepare encyclopedia",
        "build term index",
        "annotate book",
        "normalize links + media",
        "write report",
    )

    def __init__(self, file: TextIO = sys.stderr) -> None:
        self.file = file
        self._stage = 0
        self._annotate_bar: Optional[ProgressBar] = None

    def start_stage(self, stage_index: int, detail: str = "") -> None:
        self._stage = stage_index
        name = self.STAGES[stage_index]
        msg = f"{stage_index + 1}/{len(self.STAGES)} {name}"
        if detail:
            msg = f"{msg} — {detail}"
        print(msg, file=self.file, flush=True)

    def start_annotate(self, total_segments: int) -> ProgressBar:
        self._annotate_bar = ProgressBar(
            total_segments,
            label="annotate",
            file=self.file,
        )
        return self._annotate_bar

    def finish_annotate(self, links: int, elapsed_s: float) -> None:
        if self._annotate_bar is not None:
            self._annotate_bar.close()
            self._annotate_bar = None
        print(
            f"    {links:,} links in {elapsed_s:.1f}s",
            file=self.file,
            flush=True,
        )
