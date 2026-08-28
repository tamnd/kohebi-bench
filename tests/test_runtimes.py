"""Tests for measurement and reporting."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from kohebi_bench.report import Report, cpu_model, describe_environment, publishable
from kohebi_bench.runtimes import CPYTHON, Measurement, Runtime, collect, measure
from kohebi_bench.stats import Distribution

HERE = Path(__file__).resolve().parent
BENCHMARKS = HERE.parent / "benchmarks"


@pytest.fixture
def bench(tmp_path: Path):
    def make(body: str) -> Path:
        path = tmp_path / "bench.py"
        path.write_text(body)
        return path

    return make


class TestMeasure:
    def test_records_samples_excluding_warmup(self, bench):
        path = bench("x = sum(range(1000))")
        m = measure(CPYTHON, path, runs=4, warmup=2)
        assert not m.failed
        assert m.wall.n == 4

    def test_reports_peak_memory(self, bench):
        path = bench("data = [0] * 5_000_000\nprint(len(data))")
        m = measure(CPYTHON, path, runs=2, warmup=0)
        assert not m.failed
        if hasattr(__import__("os"), "wait4"):
            # 5M pointers is at least tens of megabytes anywhere.
            assert m.peak_rss_bytes > 20 * 1024 * 1024

    def test_memory_does_not_leak_between_runtimes(self, bench):
        """The bug that RUSAGE_CHILDREN would have introduced.

        A heavy run must not inflate the peak reported for a later light one.
        """
        heavy = bench("data = [0] * 5_000_000\nprint(len(data))")
        big = measure(CPYTHON, heavy, runs=1, warmup=0)

        light = heavy.parent / "light.py"
        light.write_text("print(1)")
        small = measure(CPYTHON, light, runs=1, warmup=0)

        if hasattr(__import__("os"), "wait4"):
            assert small.peak_rss_bytes < big.peak_rss_bytes

    def test_a_failing_benchmark_is_recorded_not_raised(self, bench):
        path = bench("raise SystemExit(1)")
        m = measure(CPYTHON, path, runs=1, warmup=0)
        assert m.failed

    def test_a_crashing_benchmark_reports_its_error(self, bench):
        path = bench("raise ValueError('deliberate')")
        m = measure(CPYTHON, path, runs=1, warmup=0)
        assert m.failed
        assert "deliberate" in m.error

    def test_timeout_is_recorded_not_raised(self, bench):
        path = bench("import time; time.sleep(30)")
        m = measure(CPYTHON, path, runs=1, warmup=0, timeout_s=0.5)
        assert m.failed
        assert "timed out" in m.error

    def test_missing_runtime_is_reported_as_a_failure(self, bench):
        path = bench("print(1)")
        absent = Runtime("absent", ("definitely-not-a-real-binary-xyz",))
        assert not absent.available()
        m = measure(absent, path, runs=1, warmup=0)
        assert m.failed


class TestReport:
    def _measurement(self, runtime: str, name: str, base: float) -> Measurement:
        samples = tuple(base + i * 0.0001 for i in range(20))
        return Measurement(runtime, name, Distribution(samples), 100 * 1024 * 1024)

    def test_speedups_are_relative_to_the_baseline(self):
        report = Report(
            baseline="cpython",
            measurements=[
                self._measurement("cpython", "a", 2.0),
                self._measurement("kohebi-run", "a", 0.5),
            ],
        )
        speedups = report.speedups()
        assert speedups["a"]["kohebi-run"].speedup == pytest.approx(4.0, rel=0.01)

    def test_geomean_covers_every_benchmark(self):
        report = Report(
            baseline="cpython",
            measurements=[
                self._measurement("cpython", "a", 1.0),
                self._measurement("kohebi-run", "a", 0.25),
                self._measurement("cpython", "b", 1.0),
                self._measurement("kohebi-run", "b", 1.0),
            ],
        )
        # 4x on one, 1x on the other, so 2x geomean rather than 2.5x.
        assert report.geomeans()["kohebi-run"] == pytest.approx(2.0, rel=0.02)

    def test_a_failed_run_is_not_silently_dropped(self):
        failed = Measurement("kohebi-run", "a", Distribution(()), 0, failed=True, error="boom")
        report = Report(
            baseline="cpython",
            measurements=[self._measurement("cpython", "a", 1.0), failed],
        )
        markdown = report.to_markdown()
        assert "Failures" in markdown
        assert "failed" in markdown

    def test_markdown_always_reports_memory(self):
        report = Report(
            baseline="cpython",
            measurements=[
                self._measurement("cpython", "a", 1.0),
                self._measurement("kohebi-run", "a", 0.5),
            ],
        )
        assert "Peak memory" in report.to_markdown()

    def test_json_is_valid_and_records_the_environment(self):
        import json

        report = Report(baseline="cpython", measurements=[self._measurement("cpython", "a", 1.0)])
        data = json.loads(report.to_json())
        assert data["baseline"] == "cpython"
        assert data["environment"]["platform"]
        assert data["generated_at"]


class TestCollect:
    def test_finds_the_shipped_benchmarks_and_skips_the_harness(self):
        found = [p.name for p in collect(BENCHMARKS)]
        assert "_harness.py" not in found
        assert "attribute_dispatch.py" in found
        assert "startup.py" in found

    @pytest.mark.parametrize("path", collect(BENCHMARKS), ids=lambda p: p.stem)
    def test_every_benchmark_runs_under_cpython(self, path: Path):
        """A benchmark that does not run is not a benchmark."""
        m = measure(CPYTHON, path, runs=1, warmup=0, timeout_s=300)
        assert not m.failed, f"{path.name} failed:\n{m.error}"

    def test_dotfiles_are_not_benchmarks(self, tmp_path: Path):
        """Copying this tree from macOS leaves an AppleDouble beside every file.

        The first run on real hardware measured eight of them, failed all
        eight, and listed them in the report as benchmarks.
        """
        (tmp_path / "real.py").touch()
        (tmp_path / "._real.py").touch()
        assert [p.name for p in collect(tmp_path)] == ["real.py"]


def test_the_harness_runs_on_this_interpreter():
    assert Runtime("self", (sys.executable,)).available()


class TestEnvironment:
    """The machine description is what makes a number from a real host checkable."""

    def test_a_clean_machine_has_nothing_against_it(self):
        env = {"cpu_governor": "performance", "turbo": "disabled", "virtualised": "none"}
        assert publishable(env) == []

    def test_a_shared_vps_is_flagged(self):
        """server1 and server3 are KVM guests, so the report has to say so.

        A number measured next to somebody else's workload is fine for
        noticing a 2x regression and cannot defend a 5% one.
        """
        env = {"cpu_governor": "performance", "turbo": "disabled", "virtualised": "kvm"}
        reasons = publishable(env)
        assert len(reasons) == 1
        assert "kvm" in reasons[0]

    def test_a_moving_clock_is_flagged(self):
        env = {"cpu_governor": "powersave", "turbo": "enabled", "virtualised": "none"}
        assert len(publishable(env)) == 2

    def test_the_host_can_be_named_for_the_report(self, monkeypatch):
        monkeypatch.setenv("KOHEBI_BENCH_HOST", "gpc")
        assert describe_environment()["host"] == "gpc"

    def test_the_cpu_model_is_the_chip_not_the_architecture(self):
        """platform.processor() answers x86_64 on Linux, which names nothing."""
        assert cpu_model() != "x86_64"
