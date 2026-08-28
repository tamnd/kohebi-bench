"""The runtimes under comparison, and how to measure one.

Speed and memory are measured together, always. Reporting a speedup without the
memory it cost is how PyPy's real trade-off stayed invisible to people choosing
a runtime, and it is a rule this repository does not bend.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .stats import Distribution


@dataclass(frozen=True, slots=True)
class Runtime:
    """One interpreter or compiler under test."""

    name: str
    argv: tuple[str, ...]
    note: str = ""
    #: How to ask this one what version it is, when appending `--version` to
    #: `argv` would not work. A runtime whose argv ends in a flag that takes a
    #: value would otherwise be asked to tokenize a file called `--version`.
    version_argv: tuple[str, ...] | None = None

    def available(self) -> bool:
        return shutil.which(self.argv[0]) is not None

    def version(self) -> str:
        if not self.available():
            return "not installed"
        try:
            proc = subprocess.run(
                list(self.version_argv or (*self.argv, "--version")),
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return "unknown"
        out = (proc.stdout or proc.stderr).strip()
        return out.splitlines()[0] if out else "unknown"


# The baseline is always CPython as shipped: current stable, default build,
# release, no flags chosen to flatter us.
CPYTHON = Runtime("cpython", ("python3",), "baseline: current stable, default build")
CPYTHON_JIT = Runtime("cpython-jit", ("python3",), "PYTHON_JIT=1, their fastest config")
CPYTHON_FT = Runtime("cpython-ft", ("python3t",), "free-threaded build")
PYPY = Runtime("pypy", ("pypy3",), "the incumbent fast Python")
GRAALPY = Runtime("graalpy", ("graalpy",), "the other incumbent, and the compatibility standard")
KOHEBI_RUN = Runtime("kohebi-run", ("kohebi", "run"), "JIT mode")
KOHEBI_BUILD = Runtime("kohebi-build", ("kohebi", "build", "--run"), "AOT mode")

ALL: dict[str, Runtime] = {
    r.name: r for r in (CPYTHON, CPYTHON_JIT, CPYTHON_FT, PYPY, GRAALPY, KOHEBI_RUN, KOHEBI_BUILD)
}

DEFAULT_COMPARISON = (CPYTHON, PYPY, GRAALPY, KOHEBI_RUN, KOHEBI_BUILD)


@dataclass(frozen=True, slots=True)
class Measurement:
    """What one runtime did with one benchmark, over many runs."""

    runtime: str
    benchmark: str
    wall: Distribution
    peak_rss_bytes: int
    failed: bool = False
    error: str = ""

    def summary(self) -> dict[str, object]:
        return {
            "runtime": self.runtime,
            "benchmark": self.benchmark,
            "wall": self.wall.summary() if not self.failed else None,
            "peak_rss_bytes": self.peak_rss_bytes,
            "peak_rss_mib": round(self.peak_rss_bytes / 1024 / 1024, 2),
            "failed": self.failed,
            "error": self.error,
        }


def _rss_to_bytes(ru_maxrss: int) -> int:
    """`ru_maxrss` is kilobytes on Linux and bytes on macOS.

    A portability trap that silently produces numbers off by 1024, which is
    exactly the size of error that gets published and then quoted.
    """
    return ru_maxrss if sys.platform == "darwin" else ru_maxrss * 1024


@dataclass(frozen=True, slots=True)
class _Run:
    elapsed_s: float
    returncode: int
    stderr: bytes
    peak_rss_bytes: int


def _run_once(argv: list[str], env: dict[str, str], timeout_s: float) -> _Run:
    """Run one child and get that child's own peak RSS.

    `getrusage(RUSAGE_CHILDREN)` is tempting and wrong: it is a monotonic
    high-water mark across every child the process has ever reaped, so the
    memory number for PyPy would silently inherit CPython's peak from the
    previous benchmark. `os.wait4` gives the rusage of one specific child.

    Windows has no `wait4`, so memory is reported as unknown there rather than
    as a plausible-looking wrong number.

    The wait is blocking rather than a poll loop. Polling would fold the poll
    interval into every measurement, which is invisible on a one-second
    benchmark and ruinous on startup, where the whole quantity being measured
    is a handful of milliseconds.
    """
    with (
        tempfile.TemporaryFile() as out,
        tempfile.TemporaryFile() as err,
    ):
        started = time.perf_counter()
        proc = subprocess.Popen(argv, stdout=out, stderr=err, env=env)

        # Enforce the timeout out of band so the happy path stays a blocking wait.
        timed_out = False

        def kill_it() -> None:
            nonlocal timed_out
            timed_out = True
            proc.kill()

        killer = threading.Timer(timeout_s, kill_it)
        killer.start()
        try:
            if hasattr(os, "wait4"):
                _, status, usage = os.wait4(proc.pid, 0)
                elapsed = time.perf_counter() - started
                returncode = os.waitstatus_to_exitcode(status)
                peak = _rss_to_bytes(usage.ru_maxrss)
            else:
                proc.wait()
                elapsed = time.perf_counter() - started
                returncode = proc.returncode or 0
                peak = 0
        finally:
            killer.cancel()

        if timed_out:
            raise subprocess.TimeoutExpired(argv, timeout_s)

        proc.returncode = returncode
        err.seek(0)
        return _Run(elapsed, returncode, err.read(), peak)


def measure(
    runtime: Runtime,
    benchmark: Path,
    *,
    runs: int = 30,
    warmup: int = 3,
    timeout_s: float = 600.0,
    env: dict[str, str] | None = None,
) -> Measurement:
    """Run one benchmark under one runtime and summarise it.

    Thirty runs by default. That is more than most projects do, and it is the
    reason the confidence intervals mean anything.
    """
    full_env = {**os.environ, "PYTHONHASHSEED": "0", **(env or {})}
    argv = [*runtime.argv, str(benchmark)]
    samples: list[float] = []
    peak = 0

    def failure(error: str) -> Measurement:
        return Measurement(
            runtime.name, benchmark.stem, Distribution(()), 0, failed=True, error=error
        )

    for i in range(warmup + runs):
        try:
            run = _run_once(argv, full_env, timeout_s)
        except subprocess.TimeoutExpired:
            return failure(f"timed out after {timeout_s}s")
        except OSError as exc:
            return failure(str(exc))

        if run.returncode != 0:
            return failure(run.stderr.decode(errors="replace").strip()[-500:])

        # Warmup runs are excluded from timing but still count toward peak
        # memory: a runtime does not get to hide an allocation spike by having
        # it happen on the first run.
        peak = max(peak, run.peak_rss_bytes)
        if i >= warmup:
            samples.append(run.elapsed_s)

    return Measurement(
        runtime=runtime.name,
        benchmark=benchmark.stem,
        wall=Distribution(tuple(samples)),
        peak_rss_bytes=peak,
    )


def collect(root: Path) -> list[Path]:
    """Every benchmark under `root`, in a stable order.

    Leading underscore means a helper rather than a benchmark. Leading dot
    means someone's tooling left a file here: copying this tree from macOS with
    tar produces an AppleDouble `._name.py` beside every file, and the first
    remote run measured eight of them, failed all eight, and put them in the
    report as benchmark results.
    """
    return sorted(p for p in root.rglob("*.py") if not p.name.startswith(("_", ".")))
