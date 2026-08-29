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
from dataclasses import dataclass, replace
from pathlib import Path

from .stats import Distribution


def _harness_bin() -> Path | None:
    """The bin directory of the virtual environment this harness runs from.

    `None` when it is not running from one.
    """
    if sys.prefix == sys.base_prefix:
        return None
    return Path(sys.prefix) / ("Scripts" if os.name == "nt" else "bin")


def which(binary: str) -> str | None:
    """`binary` on PATH, ignoring the virtual environment this harness runs from.

    `uv run kohebi-bench` puts `.venv/bin` at the front of PATH, and there is a
    `python3` in there. Left alone, the lookup finds that one, so the baseline
    quietly stops being the CPython on the machine and becomes whichever
    interpreter uv happened to install for the harness. The first report
    generated this way claimed a 3.13 baseline on a machine whose `python3` is
    3.14, which is the kind of error that survives review because every other
    number in the report is right.

    A name containing a separator is a path the caller chose and is taken as
    given, which is what `--kohebi target/release/kohebi` relies on.
    """
    if os.sep in binary or (os.altsep and os.altsep in binary):
        return binary if os.access(binary, os.X_OK) else None
    skip = _harness_bin()
    entries = [
        entry
        for entry in os.environ.get("PATH", os.defpath).split(os.pathsep)
        if entry and (skip is None or Path(entry) != skip)
    ]
    return shutil.which(binary, path=os.pathsep.join(entries))


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
    #: What `sys.implementation.name` has to say for this to be the runtime it
    #: claims to be. `None` for one that is not a Python interpreter, which is
    #: kohebi until it can import `sys`.
    implementation: str | None = None

    def available(self) -> bool:
        return which(self.argv[0]) is not None

    def resolved(self) -> tuple[str, ...]:
        """`argv` with the binary as a path rather than a name to look up.

        Resolved once, here, so that the version recorded in the report and the
        binary that was actually timed cannot be two different things.
        """
        return (which(self.argv[0]) or self.argv[0], *self.argv[1:])

    def misidentified(self) -> str | None:
        """A complaint when the binary found is not the runtime it is named as.

        Two reports have now been generated from the wrong interpreter. The
        first found uv's CPython under `python3` instead of the machine's. The
        second found PyPy under `python3`, because PyPy ships a `python3` beside
        its `pypy3` and putting that directory on PATH is the obvious way to
        make `pypy3` findable at all. Each produced a full report in which every
        other number was correct, and the second one had CPython and PyPy within
        a millisecond of each other on every benchmark, which is the only reason
        anybody noticed.

        A name on PATH cannot be trusted to say what a binary is. Asking the
        interpreter costs one process and cannot be fooled.
        """
        if self.implementation is None or not self.available():
            return None
        argv = [*self.resolved(), "-c", "import sys; print(sys.implementation.name)"]
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            return f"could not ask {argv[0]} what it is: {error}"
        found = proc.stdout.strip()
        if found == self.implementation:
            return None
        return (
            f"{self.name} resolved to {argv[0]}, which reports itself as "
            f"{found or 'not a Python interpreter at all'} rather than {self.implementation}"
        )

    def version(self) -> str:
        if not self.available():
            return "not installed"
        argv = self.version_argv
        if argv is None:
            argv = (*self.resolved(), "--version")
        else:
            argv = (which(argv[0]) or argv[0], *argv[1:])
        try:
            proc = subprocess.run(
                list(argv),
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
CPYTHON = Runtime(
    "cpython", ("python3",), "baseline: current stable, default build", implementation="cpython"
)
CPYTHON_JIT = Runtime(
    "cpython-jit", ("python3",), "PYTHON_JIT=1, their fastest config", implementation="cpython"
)
CPYTHON_FT = Runtime("cpython-ft", ("python3t",), "free-threaded build", implementation="cpython")
PYPY = Runtime("pypy", ("pypy3",), "the incumbent fast Python", implementation="pypy")
GRAALPY = Runtime(
    "graalpy",
    ("graalpy",),
    "the other incumbent, and the compatibility standard",
    implementation="graalpy",
)
KOHEBI_RUN = Runtime("kohebi-run", ("kohebi", "run"), "JIT mode")
KOHEBI_BUILD = Runtime("kohebi-build", ("kohebi", "build", "--run"), "AOT mode")

ALL: dict[str, Runtime] = {
    r.name: r for r in (CPYTHON, CPYTHON_JIT, CPYTHON_FT, PYPY, GRAALPY, KOHEBI_RUN, KOHEBI_BUILD)
}

DEFAULT_COMPARISON = (CPYTHON, PYPY, GRAALPY, KOHEBI_RUN, KOHEBI_BUILD)

#: The runtimes that are us, and so the ones the goal is measured against.
OURS = frozenset({KOHEBI_RUN.name, KOHEBI_BUILD.name})


def at(runtime: Runtime, binary: str) -> Runtime:
    """The same runtime run from a particular binary rather than from PATH.

    Nobody installs kohebi before benchmarking a change to it. The binary being
    measured is almost always `target/release/kohebi` in a working tree, and
    asking people to put that on PATH first is how you end up with a report
    that quietly measured last week's build.
    """
    if runtime.name not in OURS:
        return runtime
    return replace(runtime, argv=(binary, *runtime.argv[1:]))


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


#: Whether this platform has the `/proc` entry that [`_watch_peak_rss`] reads.
_HAS_PROC_STATUS = sys.platform.startswith("linux")


def _watch_peak_rss(pid: int, seen: list[int], interval_s: float = 0.001) -> None:
    """The kernel's own high-water mark for one process, until it exits.

    On Linux `ru_maxrss` from `wait4` cannot be used for this at all, which took
    a while to believe. A child inherits the parent's page tables across `fork`,
    those pages are charged to the child, and the peak is recorded before `exec`
    replaces them. So the number that comes back is the size of whatever spawned
    the process, not the size of the process. Measured with a parent holding 200
    MiB of ballast, `/bin/true` reports a peak of 213 MiB. `posix_spawn` does not
    help: glibc implements it with `CLONE_VM`, so the child shares the parent's
    address space until `exec` and is charged for it just the same.

    This is why `/usr/bin/time` appears to work. It is a tiny program, so the
    floor it imposes is small enough not to notice, and a harness written in
    Python imposes a floor of twenty-odd megabytes onto a runtime whose whole
    claim is using three.

    `VmHWM` in `/proc/<pid>/status` is the same quantity measured correctly: the
    kernel resets it at `exec`, so it covers the program that was asked for and
    nothing before it. It is itself a high-water mark, so this does not have to
    catch the peak as it happens, only to read once after it. The poll is on its
    own thread and the timing still comes from a blocking wait, so nothing here
    is folded into the elapsed time.

    A process that exits before the first read leaves nothing behind, and that
    is reported as unknown rather than as a plausible-looking zero.
    """
    path = f"/proc/{pid}/status"
    while True:
        try:
            with open(path, encoding="ascii") as handle:
                text = handle.read()
        except OSError:
            return
        marker = "VmHWM:"
        if marker in text:
            seen.append(int(text.split(marker, 1)[1].split(maxsplit=1)[0]))
        time.sleep(interval_s)


@dataclass(frozen=True, slots=True)
class _Run:
    elapsed_s: float
    returncode: int
    stderr: bytes
    peak_rss_bytes: int


def _run_once(argv: list[str], env: dict[str, str], timeout_s: float) -> _Run:
    """Run one child and get that child's own peak RSS.

    Where the peak comes from depends on the platform, and the reason is in
    [`_watch_peak_rss`]. On Linux it is `VmHWM`, because `ru_maxrss` there is the
    size of whatever did the spawning. On macOS it is `ru_maxrss`, which is
    correct because `posix_spawn` is a real system call rather than a fork.

    `getrusage(RUSAGE_CHILDREN)` is tempting and wrong on every platform: it is a
    monotonic high-water mark across every child the process has ever reaped, so
    the memory number for PyPy would silently inherit CPython's peak from the
    previous benchmark. `os.wait4` gives the rusage of one specific child.

    Windows has no `wait4` and no `/proc`, so memory is reported as unknown there
    rather than as a plausible-looking wrong number.

    The wait is blocking rather than a poll loop. Polling would fold the poll
    interval into every measurement, which is invisible on a one-second
    benchmark and ruinous on startup, where the whole quantity being measured
    is a handful of milliseconds. The memory poll is on its own thread for the
    same reason.
    """
    with (
        tempfile.TemporaryFile() as out,
        tempfile.TemporaryFile() as err,
    ):
        started = time.perf_counter()
        proc = subprocess.Popen(argv, stdout=out, stderr=err, env=env)

        seen: list[int] = []
        watcher: threading.Thread | None = None
        if _HAS_PROC_STATUS:
            watcher = threading.Thread(target=_watch_peak_rss, args=(proc.pid, seen), daemon=True)
            watcher.start()

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
            if _HAS_PROC_STATUS:
                if watcher is not None:
                    watcher.join(1.0)
                peak = max(seen) * 1024 if seen else 0
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
    argv = [*runtime.resolved(), str(benchmark)]
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
