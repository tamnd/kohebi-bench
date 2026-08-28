"""Tests for the statistics, which are the part that makes the numbers claims.

A benchmark harness with wrong statistics does not produce a slightly wrong
answer. It produces a confident wrong answer, which is worse than no answer.
"""

from __future__ import annotations

import math

import pytest

from kohebi_bench.stats import Distribution, compare, geomean


class TestDistribution:
    def test_median_and_quartiles(self):
        d = Distribution(tuple(float(x) for x in range(1, 10)))
        assert d.median == 5.0
        assert d.q1 == 3.0
        assert d.q3 == 7.0
        assert d.iqr == 4.0

    def test_single_sample_does_not_explode(self):
        d = Distribution((1.5,))
        assert d.median == d.q1 == d.q3 == 1.5
        assert d.iqr == 0.0

    def test_median_ignores_a_slow_outlier(self):
        """The reason medians are used rather than means.

        One run interrupted by something else on the machine must not move the
        reported number.
        """
        clean = Distribution((1.0,) * 30)
        interrupted = Distribution((1.0,) * 29 + (50.0,))
        assert interrupted.median == clean.median
        assert sum(interrupted.samples) / 30 > 2.0  # the mean would have moved

    def test_stability_gate(self):
        tight = Distribution((1.0, 1.01, 1.0, 0.99, 1.0))
        assert tight.stable
        noisy = Distribution((1.0, 2.0, 0.5, 3.0, 1.0))
        assert not noisy.stable

    def test_too_few_samples_is_never_stable(self):
        assert not Distribution((1.0, 1.0)).stable


class TestCompare:
    def test_detects_a_real_speedup(self):
        base = Distribution(tuple(2.0 + i * 0.001 for i in range(30)))
        fast = Distribution(tuple(1.0 + i * 0.001 for i in range(30)))
        c = compare(base, fast)
        assert c.speedup == pytest.approx(2.0, rel=0.02)
        assert c.significant
        assert c.low < c.speedup < c.high

    def test_identical_distributions_are_not_significant(self):
        """The guard against publishing noise as a result."""
        samples = tuple(1.0 + (i % 7) * 0.01 for i in range(30))
        c = compare(Distribution(samples), Distribution(samples))
        assert c.speedup == pytest.approx(1.0)
        assert not c.significant
        assert "not significant" in c.format()

    def test_overlapping_noisy_distributions_are_not_significant(self):
        a = Distribution((1.0, 1.5, 0.6, 1.3, 0.8, 1.2, 0.9, 1.4))
        b = Distribution((1.1, 0.7, 1.4, 0.9, 1.2, 1.0, 1.3, 0.8))
        assert not compare(a, b).significant

    def test_is_deterministic(self):
        a = Distribution(tuple(1.0 + i * 0.01 for i in range(20)))
        b = Distribution(tuple(0.5 + i * 0.01 for i in range(20)))
        assert compare(a, b) == compare(a, b)


class TestGeomean:
    def test_matches_the_definition(self):
        assert geomean([1.0, 4.0]) == pytest.approx(2.0)

    def test_is_not_the_arithmetic_mean(self):
        """A 10x win and a 1x draw is not a 5.5x runtime."""
        values = [10.0, 1.0]
        assert geomean(values) == pytest.approx(math.sqrt(10))
        assert geomean(values) < sum(values) / len(values)

    def test_empty_is_zero_not_an_error(self):
        assert geomean([]) == 0.0

    def test_ignores_non_positive_values(self):
        assert geomean([0.0, 4.0, 1.0]) == pytest.approx(2.0)
