"""Turning measurements into something a sceptic can check.

Five rules, written down because they are easy to violate by accident:

- Never compare our release build against someone else's debug build.
- Never report a geomean without the per-benchmark table beside it.
- Never quietly drop a benchmark where we regress.
- Never report warm numbers without the warmup cost.
- Never report speed without memory.

The functions here enforce the ones that can be enforced in code. The rest are
enforced by review.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .runtimes import Measurement, Runtime
from .stats import Comparison, compare, geomean


@dataclass(slots=True)
class Report:
    baseline: str
    measurements: list[Measurement]
    environment: dict[str, str] = field(default_factory=dict)
    generated_at: str = ""

    def __post_init__(self) -> None:
        if not self.generated_at:
            self.generated_at = datetime.now(UTC).isoformat(timespec="seconds")
        if not self.environment:
            self.environment = describe_environment()

    def by_benchmark(self) -> dict[str, dict[str, Measurement]]:
        out: dict[str, dict[str, Measurement]] = {}
        for m in self.measurements:
            out.setdefault(m.benchmark, {})[m.runtime] = m
        return out

    def speedups(self) -> dict[str, dict[str, Comparison]]:
        """Every runtime against the baseline, per benchmark."""
        out: dict[str, dict[str, Comparison]] = {}
        for name, runs in self.by_benchmark().items():
            base = runs.get(self.baseline)
            if base is None or base.failed:
                continue
            for runtime, m in runs.items():
                if runtime == self.baseline or m.failed:
                    continue
                out.setdefault(name, {})[runtime] = compare(base.wall, m.wall)
        return out

    def geomeans(self) -> dict[str, float]:
        per_runtime: dict[str, list[float]] = {}
        for comparisons in self.speedups().values():
            for runtime, c in comparisons.items():
                per_runtime.setdefault(runtime, []).append(c.speedup)
        return {r: geomean(v) for r, v in sorted(per_runtime.items())}

    def to_json(self) -> str:
        return (
            json.dumps(
                {
                    "generated_at": self.generated_at,
                    "baseline": self.baseline,
                    "environment": self.environment,
                    "geomean_speedup": self.geomeans(),
                    "measurements": [m.summary() for m in self.measurements],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )

    def to_markdown(self) -> str:
        lines = [
            "# Benchmark report",
            "",
            f"Generated {self.generated_at}.",
            f"Baseline: `{self.baseline}`.",
            "",
            "## Environment",
            "",
            "| | |",
            "| --- | --- |",
        ]
        lines += [f"| {k} | {v} |" for k, v in sorted(self.environment.items())]

        caveats = publishable(self.environment)
        if caveats:
            lines += [
                "",
                "> [!NOTE]",
                "> This machine is fine for catching a regression and is not a source of a "
                "headline number:",
            ]
            lines += [f"> - {c}" for c in caveats]

        noisy = [m for m in self.measurements if not m.failed and not m.wall.stable]
        if noisy:
            lines += [
                "",
                "> [!WARNING]",
                f"> {len(noisy)} measurement(s) were too noisy to publish: fewer than 5 samples, "
                "or an interquartile range above 5% of the median. Re-run on a quiet machine.",
            ]

        geo = self.geomeans()
        if geo:
            lines += ["", "## Geomean speedup", "", "| Runtime | Speedup |", "| --- | ---: |"]
            lines += [f"| {r} | {v:.2f}x |" for r, v in geo.items()]
            lines += [
                "",
                "A geomean alone is not a result. The per-benchmark table below is the "
                "number; the geomean is a summary of it.",
            ]

        speedups = self.speedups()
        runtimes = sorted({m.runtime for m in self.measurements if m.runtime != self.baseline})

        lines += ["", "## Per benchmark", ""]
        if not runtimes:
            lines += [
                f"Only the baseline `{self.baseline}` was measured, so there is nothing to "
                "compare against. Raw timings are in `results.json`.",
            ]
        else:
            header = "| Benchmark | " + " | ".join(runtimes) + " |"
            lines += [header, "| --- |" + " ---: |" * len(runtimes)]
        for name, runs in sorted(self.by_benchmark().items()) if runtimes else []:
            cells = []
            for r in runtimes:
                m = runs.get(r)
                if m is None:
                    cells.append("n/a")
                elif m.failed:
                    cells.append("failed")
                else:
                    c = speedups.get(name, {}).get(r)
                    cells.append(c.format() if c else "n/a")
            lines.append(f"| `{name}` | " + " | ".join(cells) + " |")

        lines += ["", "## Peak memory", "", "Speed is never reported without it.", ""]
        mem_header = "| Benchmark | " + " | ".join([self.baseline, *runtimes]) + " |"
        lines += [mem_header, "| --- |" + " ---: |" * (len(runtimes) + 1)]
        for name, runs in sorted(self.by_benchmark().items()):
            cells = []
            for r in [self.baseline, *runtimes]:
                m = runs.get(r)
                if m is None or m.failed or not m.peak_rss_bytes:
                    cells.append("n/a")
                else:
                    cells.append(f"{m.peak_rss_bytes / 1024 / 1024:.1f} MiB")
            lines.append(f"| `{name}` | " + " | ".join(cells) + " |")

        failures = [m for m in self.measurements if m.failed]
        if failures:
            lines += [
                "",
                "## Failures",
                "",
                "| Benchmark | Runtime | Error |",
                "| --- | --- | --- |",
            ]
            for m in failures:
                first = m.error.splitlines()[0][:120] if m.error else ""
                lines.append(f"| `{m.benchmark}` | {m.runtime} | {first} |")

        return "\n".join(lines) + "\n"

    def write(self, out: Path) -> None:
        out.mkdir(parents=True, exist_ok=True)
        (out / "results.json").write_text(self.to_json())
        (out / "report.md").write_text(self.to_markdown())


def describe_environment(runtimes: list[Runtime] | None = None) -> dict[str, str]:
    """Everything a reader needs to reproduce or discount the numbers."""
    env = {
        "host": os.environ.get("KOHEBI_BENCH_HOST") or platform.node(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": cpu_model(),
        "cpu_count": str(_cpu_count()),
        "cpu_governor": _read_sysfs("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
        "turbo": _turbo_state(),
        "virtualised": _virtualisation(),
    }
    for r in runtimes or []:
        env[f"version.{r.name}"] = r.version()
    return env


def publishable(env: dict[str, str]) -> list[str]:
    """Reasons this machine should not be the source of a headline number.

    None of these stop a run. They go in the report, because the useful thing
    is not preventing a measurement on a noisy box, it is preventing a
    measurement on a noisy box from being quoted as if it came from a quiet one.
    """
    reasons = []
    if env.get("cpu_governor") not in ("performance", "unknown"):
        reasons.append(
            f"CPU governor is {env.get('cpu_governor')}, so clock speed moves during the run"
        )
    if env.get("turbo") == "enabled":
        reasons.append(
            "turbo is enabled, so the first benchmark runs on a colder core than the last"
        )
    virt = env.get("virtualised", "unknown")
    if virt not in ("none", "unknown"):
        reasons.append(f"running under {virt}, where the host schedules other tenants against us")
    return reasons


def cpu_model() -> str:
    """The actual chip, which platform.processor() does not give you on Linux."""
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(errors="replace").splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    if platform.system() == "Darwin":
        out = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
        if out:
            return out
    return platform.processor() or "unknown"


def _turbo_state() -> str:
    """Intel and AMD spell the same switch two different ways."""
    no_turbo = _read_sysfs("/sys/devices/system/cpu/intel_pstate/no_turbo")
    if no_turbo in ("0", "1"):
        return "disabled" if no_turbo == "1" else "enabled"
    boost = _read_sysfs("/sys/devices/system/cpu/cpufreq/boost")
    if boost in ("0", "1"):
        return "disabled" if boost == "0" else "enabled"
    return "unknown"


def _virtualisation() -> str:
    """Whether we are on metal, in a VM, or in WSL.

    A shared VPS can be perfectly good for spotting a 2x regression and is a
    bad place to defend a 5% one, so this belongs in the report rather than in
    a footnote someone writes later from memory.
    """
    detected = _run(["systemd-detect-virt"])
    if detected:
        return detected
    if "microsoft" in platform.release().lower():
        return "wsl"
    return "unknown"


def _read_sysfs(path: str) -> str:
    try:
        return Path(path).read_text().strip()
    except OSError:
        return "unknown"


def _run(argv: list[str]) -> str:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return proc.stdout.strip()


def _cpu_count() -> int:
    """Cores this process may use, which is not always the cores the machine has.

    Inside a container or under taskset the affinity mask is the honest number
    and os.cpu_count() is not. Reached through getattr rather than a
    type: ignore because sched_getaffinity is Linux only, so the ignore is
    required when mypy runs on macOS and flagged as unused when it runs on
    Linux, and CI does one while most of us do the other.
    """
    affinity = getattr(os, "sched_getaffinity", None)
    if affinity is not None:
        return len(affinity(0))
    return os.cpu_count() or 0


def git_revision() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    return out.stdout.strip() or "unknown"
