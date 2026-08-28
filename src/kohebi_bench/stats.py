"""Statistics, kept deliberately boring.

The rule this repository exists to enforce: a number without a method is
marketing. That means medians rather than means, an explicit spread, and a
confidence interval on every comparison so that "1.4x faster" can be checked
rather than believed.

Means are avoided throughout. Benchmark timings are right-skewed. A run can be
arbitrarily slow because something else touched the CPU, but it cannot be
arbitrarily fast, so the mean reports the noise and the median reports the
machine.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Distribution:
    """The summary of one benchmark under one runtime."""

    samples: tuple[float, ...]

    @property
    def n(self) -> int:
        return len(self.samples)

    @property
    def median(self) -> float:
        return statistics.median(self.samples)

    @property
    def q1(self) -> float:
        return _quantile(self.samples, 0.25)

    @property
    def q3(self) -> float:
        return _quantile(self.samples, 0.75)

    @property
    def iqr(self) -> float:
        return self.q3 - self.q1

    @property
    def minimum(self) -> float:
        return min(self.samples)

    @property
    def relative_spread(self) -> float:
        """IQR as a fraction of the median.

        Above roughly 0.05 the machine is too noisy to draw conclusions from,
        and the run should be repeated somewhere quieter rather than published.
        """
        median = self.median
        return self.iqr / median if median else math.inf

    @property
    def stable(self) -> bool:
        return self.n >= 5 and self.relative_spread <= 0.05

    def summary(self) -> dict[str, float | int]:
        return {
            "n": self.n,
            "median": self.median,
            "q1": self.q1,
            "q3": self.q3,
            "iqr": self.iqr,
            "min": self.minimum,
            "relative_spread": self.relative_spread,
        }


@dataclass(frozen=True, slots=True)
class Comparison:
    """One runtime against a baseline, with an interval rather than a point."""

    speedup: float
    """Baseline median divided by candidate median. Above 1.0 is faster."""

    low: float
    high: float
    """95% bootstrap confidence interval on the speedup."""

    @property
    def significant(self) -> bool:
        """Whether the interval excludes 'no difference'.

        A comparison whose interval spans 1.0 has not measured anything and
        must not be reported as a win or a loss.
        """
        return not (self.low <= 1.0 <= self.high)

    def format(self) -> str:
        marker = "" if self.significant else " (not significant)"
        return f"{self.speedup:.2f}x [{self.low:.2f}, {self.high:.2f}]{marker}"


def compare(
    baseline: Distribution,
    candidate: Distribution,
    *,
    resamples: int = 10_000,
    seed: int = 0,
) -> Comparison:
    """Bootstrap the ratio of medians.

    A deterministic seed by default, so that re-running the report on the same
    samples produces the same interval. Randomness in a published number is one
    more thing a reader has to take on trust.
    """
    rng = random.Random(seed)
    base = baseline.samples
    cand = candidate.samples
    ratios = []
    for _ in range(resamples):
        b = statistics.median(rng.choices(base, k=len(base)))
        c = statistics.median(rng.choices(cand, k=len(cand)))
        if c:
            ratios.append(b / c)
    ratios.sort()
    point = baseline.median / candidate.median if candidate.median else math.inf
    return Comparison(
        speedup=point,
        low=_quantile(ratios, 0.025),
        high=_quantile(ratios, 0.975),
    )


def geomean(values: list[float]) -> float:
    """Geometric mean, the only correct average for a set of ratios.

    An arithmetic mean of speedups overweights the benchmark you happened to
    win hardest, which is how a runtime ends up claiming a number nobody can
    reproduce.
    """
    usable = [v for v in values if v > 0]
    if not usable:
        return 0.0
    return math.exp(sum(math.log(v) for v in usable) / len(usable))


def _quantile(values: tuple[float, ...] | list[float], q: float) -> float:
    """Linear-interpolation quantile. Works for n = 1, unlike the stdlib's."""
    ordered = sorted(values)
    if not ordered:
        return math.nan
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return ordered[int(pos)]
    return ordered[lower] * (upper - pos) + ordered[upper] * (pos - lower)
