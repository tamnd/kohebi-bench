"""Tests for measurement and reporting."""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from kohebi_bench import runtimes
from kohebi_bench.__main__ import main
from kohebi_bench.report import Report, cpu_model, describe_environment, publishable
from kohebi_bench.runtimes import (
    CPYTHON,
    KOHEBI_BUILD,
    KOHEBI_RUN,
    Measurement,
    Runtime,
    at,
    collect,
    measure,
)
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

    def test_a_runtime_that_failed_everywhere_says_so_once(self):
        """kohebi-build is a stub, and five copies of that fact is not a report."""
        stub = "error: unexpected argument '--run' found"
        report = Report(
            baseline="cpython",
            measurements=[
                m
                for name in ("a", "b", "c")
                for m in (
                    self._measurement("cpython", name, 1.0),
                    Measurement("kohebi-build", name, Distribution(()), 0, True, stub),
                )
            ],
        )
        rows = [ln for ln in report.to_markdown().splitlines() if stub in ln]
        assert len(rows) == 1
        assert "every benchmark (3)" in rows[0]

    def test_a_runtime_that_failed_on_one_benchmark_names_it(self):
        report = Report(
            baseline="cpython",
            measurements=[
                self._measurement("cpython", "a", 1.0),
                self._measurement("cpython", "b", 1.0),
                self._measurement("kohebi-run", "a", 0.5),
                Measurement("kohebi-run", "b", Distribution(()), 0, True, "NotImplementedError"),
            ],
        )
        row = next(ln for ln in report.to_markdown().splitlines() if "NotImplementedError" in ln)
        assert "`b`" in row
        assert "every benchmark" not in row

    def test_two_runtimes_failing_the_same_way_are_not_merged(self):
        report = Report(
            baseline="cpython",
            measurements=[
                self._measurement("cpython", "a", 1.0),
                Measurement("kohebi-run", "a", Distribution(()), 0, True, "boom"),
                Measurement("pypy", "a", Distribution(()), 0, True, "boom"),
            ],
        )
        rows = [ln for ln in report.to_markdown().splitlines() if "boom" in ln]
        assert len(rows) == 2

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


class TestBinaryOverride:
    """Nobody installs kohebi before benchmarking a change to it."""

    def test_the_kohebi_binary_can_come_from_a_working_tree(self):
        moved = at(KOHEBI_RUN, "target/release/kohebi")
        assert moved.argv == ("target/release/kohebi", "run")
        assert moved.name == KOHEBI_RUN.name

    def test_the_flags_after_the_binary_are_kept(self):
        assert at(KOHEBI_BUILD, "/opt/kohebi").argv == ("/opt/kohebi", "build", "--run")

    def test_someone_elses_runtime_is_left_alone(self):
        """`--kohebi` must not repoint python3 at the kohebi binary."""
        assert at(CPYTHON, "/opt/kohebi") == CPYTHON


class TestLookup:
    """`uv run` puts a second Python in front of the one being benchmarked."""

    def test_the_harness_venv_is_not_where_the_baseline_comes_from(self, tmp_path, monkeypatch):
        venv = tmp_path / "venv"
        real = tmp_path / "usr"
        for d in (venv / "bin", real):
            d.mkdir(parents=True)
        for d in (venv / "bin", real):
            exe = d / "python3"
            exe.write_text("#!/bin/sh\n")
            exe.chmod(0o755)

        monkeypatch.setattr(runtimes.sys, "prefix", str(venv))
        monkeypatch.setattr(runtimes.sys, "base_prefix", str(tmp_path / "base"))
        monkeypatch.setenv("PATH", f"{venv / 'bin'}{os.pathsep}{real}")

        assert runtimes.which("python3") == str(real / "python3")

    def test_outside_a_venv_the_first_match_wins(self, tmp_path, monkeypatch):
        first = tmp_path / "first"
        first.mkdir()
        exe = first / "python3"
        exe.write_text("#!/bin/sh\n")
        exe.chmod(0o755)

        monkeypatch.setattr(runtimes.sys, "prefix", str(tmp_path))
        monkeypatch.setattr(runtimes.sys, "base_prefix", str(tmp_path))
        monkeypatch.setenv("PATH", str(first))

        assert runtimes.which("python3") == str(exe)

    def test_a_path_the_caller_chose_is_taken_as_given(self, tmp_path):
        """`--kohebi target/release/kohebi` must not be searched for on PATH."""
        exe = tmp_path / "kohebi"
        exe.write_text("#!/bin/sh\n")
        exe.chmod(0o755)
        assert runtimes.which(str(exe)) == str(exe)
        assert runtimes.which(str(tmp_path / "absent")) is None

    def test_the_timed_binary_is_the_one_the_version_came_from(self):
        """Two PATH lookups can disagree. One resolution cannot."""
        resolved = CPYTHON.resolved()
        assert os.sep in resolved[0]
        assert os.access(resolved[0], os.X_OK)


class TestGoal:
    """Speed and memory as one row, because the claim is both at once."""

    def _pair(self, runtime: str, name: str, seconds: float, mib: float) -> Measurement:
        samples = tuple(seconds + i * 0.0001 for i in range(20))
        return Measurement(runtime, name, Distribution(samples), int(mib * 1024 * 1024))

    def _report(self, speed: float, mib: float) -> Report:
        return Report(
            baseline="cpython",
            measurements=[
                self._pair("cpython", "a", 1.0, 100),
                self._pair("kohebi-run", "a", 1.0 / speed, mib),
            ],
        )

    def test_memory_is_a_ratio_of_the_baseline(self):
        ratios = self._report(1.0, 25).memory_ratios()
        assert ratios["kohebi-run"] == pytest.approx(0.25, rel=0.01)

    def test_a_run_that_hit_the_goal_says_so(self):
        [standing] = self._report(12.0, 8).standings()
        assert standing.met
        assert standing.remaining() == "met"

    def test_a_run_that_missed_says_by_how_much_on_each_axis(self):
        [standing] = self._report(2.0, 50).standings()
        assert not standing.met
        assert "5.0x faster" in standing.remaining()
        assert "5.0x leaner" in standing.remaining()

    def test_winning_one_axis_only_reports_the_other(self):
        [standing] = self._report(20.0, 50).standings()
        assert standing.remaining() == "5.0x leaner"

    def test_a_machine_with_no_memory_numbers_does_not_score_perfectly(self):
        """Windows has no wait4, so every peak is zero there."""
        report = Report(
            baseline="cpython",
            measurements=[
                Measurement("cpython", "a", Distribution((1.0,) * 20), 0),
                Measurement("kohebi-run", "a", Distribution((0.05,) * 20), 0),
            ],
        )
        assert report.memory_ratios() == {}
        [standing] = report.standings()
        assert not standing.met
        assert "n/a" in report.to_markdown()

    def test_the_markdown_puts_the_goal_where_it_cannot_be_missed(self):
        markdown = self._report(2.0, 50).to_markdown()
        assert "Where this leaves the goal" in markdown
        assert "5.0x faster" in markdown

    def test_a_rival_is_measured_but_not_held_to_our_goal(self):
        report = Report(
            baseline="cpython",
            measurements=[
                self._pair("cpython", "a", 1.0, 100),
                self._pair("pypy", "a", 0.1, 300),
            ],
        )
        [standing] = report.standings()
        assert standing.runtime == "pypy"
        assert standing.memory == pytest.approx(3.0, rel=0.01)
        # PyPy's row carries no "still needed", since the goal is not theirs.
        row = next(ln for ln in report.to_markdown().splitlines() if ln.startswith("| pypy "))
        assert row.endswith("|  |")

    def test_ours_are_listed_first(self):
        report = Report(
            baseline="cpython",
            measurements=[
                self._pair("cpython", "a", 1.0, 100),
                self._pair("pypy", "a", 0.1, 300),
                self._pair("kohebi-run", "a", 0.5, 50),
            ],
        )
        assert [s.runtime for s in report.standings()] == ["kohebi-run", "pypy"]


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


class TestIdentity:
    """A binary found on PATH is asked what it is before it is trusted."""

    def test_an_interpreter_that_is_what_it_says_is_accepted(self) -> None:
        # Whichever interpreter is running the tests, asked whether it is
        # itself. Not `CPYTHON` as it stands, because `python3` is not CPython
        # in every job that runs this: CI installs PyPy and GraalPy alongside
        # it and the last one set up owns the name.
        honest = replace(
            runtimes.CPYTHON, argv=(sys.executable,), implementation=sys.implementation.name
        )
        assert honest.misidentified() is None

    def test_a_runtime_that_is_not_a_python_is_not_asked(self) -> None:
        # kohebi cannot import `sys` yet, so there is nothing to ask it.
        assert runtimes.KOHEBI_RUN.implementation is None
        assert runtimes.KOHEBI_RUN.misidentified() is None

    def test_the_wrong_interpreter_under_the_right_name_is_caught(self) -> None:
        # This is the failure it exists for: PyPy ships a `python3` beside its
        # `pypy3`, so putting that directory on PATH makes `python3` PyPy.
        claimed = "cpython" if sys.implementation.name != "cpython" else "pypy"
        impostor = replace(runtimes.PYPY, argv=(sys.executable,), implementation=claimed)
        complaint = impostor.misidentified()
        assert complaint is not None
        assert sys.implementation.name in complaint
        assert claimed in complaint

    def test_something_that_is_not_a_python_at_all_is_caught(self, tmp_path: Path) -> None:
        binary = tmp_path / "python3"
        binary.write_text("#!/bin/sh\nexit 0\n")
        binary.chmod(0o755)
        complaint = replace(runtimes.CPYTHON, argv=(str(binary),)).misidentified()
        assert complaint is not None
        assert "not a Python interpreter at all" in complaint


class TestBuildQuality:
    """The right interpreter, built in a way that makes it a dishonest baseline."""

    def _cpython(self) -> runtimes.Runtime:
        return replace(runtimes.CPYTHON, argv=(sys.executable,), implementation="cpython")

    def test_a_runtime_that_is_not_cpython_is_not_asked(self) -> None:
        # Only CPython is the baseline, and only CPython has these build
        # variables to look at. PyPy and GraalPy answer `None` to both and would
        # look fine, but asking them means one process per run for nothing.
        assert runtimes.PYPY.crippled() is None
        assert runtimes.KOHEBI_RUN.crippled() is None

    def test_the_interpreter_running_these_tests_is_judged_on_its_own_build(self) -> None:
        import sysconfig

        if sys.implementation.name != "cpython":
            pytest.skip("only CPython has these build variables")
        complaint = self._cpython().crippled()
        dtrace = bool(sysconfig.get_config_var("WITH_DTRACE"))
        debug = bool(sysconfig.get_config_var("Py_DEBUG"))
        # Whichever CPython is running this, the answer has to follow from how
        # it was built rather than from what would be convenient here. CI runs a
        # standalone build with neither of these, and a developer on macOS with
        # Homebrew's Python has the one this check was written for.
        if debug or (dtrace and sys.platform == "darwin"):
            assert complaint is not None
            assert sys.executable in complaint
        else:
            assert complaint is None

    def test_a_binary_that_will_not_answer_is_not_a_complaint(self, tmp_path: Path) -> None:
        # It has already been caught by `misidentified`, and refusing twice for
        # one problem buries the message that says what the problem is.
        binary = tmp_path / "python3"
        binary.write_text("#!/bin/sh\nexit 0\n")
        binary.chmod(0o755)
        assert replace(runtimes.CPYTHON, argv=(str(binary),)).crippled() is None


class TestNamingABinary:
    """`--at NAME=PATH`, for a machine where PATH cannot reach what you meant."""

    def test_a_named_runtime_moves_to_the_binary_given(self) -> None:
        moved = runtimes.located(runtimes.CPYTHON, {"cpython": "python3.14"})
        assert moved.argv == ("python3.14",)
        assert moved.implementation == "cpython"

    def test_the_arguments_after_the_binary_survive(self) -> None:
        # kohebi-run is `kohebi run`, and only the first word is the binary.
        moved = runtimes.located(runtimes.KOHEBI_RUN, {"kohebi-run": "target/release/kohebi"})
        assert moved.argv == ("target/release/kohebi", "run")

    def test_a_runtime_nobody_named_is_left_alone(self) -> None:
        assert runtimes.located(runtimes.PYPY, {"cpython": "python3.14"}) is runtimes.PYPY

    def test_a_malformed_pair_is_rejected_before_anything_is_timed(self) -> None:
        with pytest.raises(SystemExit):
            main(["run", "--at", "python3.14", "benchmarks"])

    def test_a_name_that_is_not_a_runtime_is_rejected(self) -> None:
        with pytest.raises(SystemExit):
            main(["run", "--at", "cython=cython", "benchmarks"])


class TestPeakMemory:
    """Where the peak comes from, and why it is not `ru_maxrss` on Linux."""

    def test_a_child_is_not_charged_for_the_harness(self, tmp_path: Path) -> None:
        # The bug this guards: on Linux the child inherits the parent's pages
        # across `fork` and is charged for them, so a `/bin/true` spawned from a
        # fat process reports the fat process's size.
        #
        # The same trivial program twice, once from a lean harness and once from
        # a fat one, rather than one run against a fixed ceiling. An empty
        # program does not cost the same under every interpreter that runs these
        # tests: CPython starts in about 10 MiB, PyPy in 56 and GraalPy in 177,
        # so any threshold that means something under one of them means nothing
        # under another. What has to hold is that the ballast does not show up.
        program = tmp_path / "small.py"
        program.write_text("pass\n")
        env = dict(os.environ)
        lean = runtimes._run_once([sys.executable, str(program)], env, 60.0)
        ballast = bytearray(64 * 1024 * 1024)
        ballast[::4096] = b"x" * (len(ballast) // 4096)
        try:
            fat = runtimes._run_once([sys.executable, str(program)], env, 60.0)
        finally:
            del ballast
        if lean.peak_rss_bytes == 0 or fat.peak_rss_bytes == 0:
            pytest.skip("this platform does not report peak memory")
        assert abs(fat.peak_rss_bytes - lean.peak_rss_bytes) < 16 * 1024 * 1024

    def test_a_bigger_program_reports_a_bigger_peak(self, tmp_path: Path) -> None:
        small = tmp_path / "small.py"
        small.write_text("pass\n")
        large = tmp_path / "large.py"
        large.write_text("x = bytearray(64 * 1024 * 1024)\nx[::4096] = b'y' * (len(x) // 4096)\n")
        env = dict(os.environ)
        lean = runtimes._run_once([sys.executable, str(small)], env, 60.0)
        fat = runtimes._run_once([sys.executable, str(large)], env, 60.0)
        if lean.peak_rss_bytes == 0 or fat.peak_rss_bytes == 0:
            pytest.skip("this platform does not report peak memory")
        assert fat.peak_rss_bytes - lean.peak_rss_bytes > 32 * 1024 * 1024
