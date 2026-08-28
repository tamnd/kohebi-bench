# kohebi-bench

Benchmarks for [kohebi](https://github.com/tamnd/kohebi), a Python runtime written in Rust, measured against CPython, PyPy, and GraalPy.

[![Benchmarks](https://github.com/tamnd/kohebi-bench/actions/workflows/bench.yml/badge.svg)](https://github.com/tamnd/kohebi-bench/actions/workflows/bench.yml)
[![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue.svg)](#license)

> [!NOTE]
> kohebi is not implemented yet, so nothing here has measured it. What the harness currently produces is a baseline: what CPython, PyPy, and GraalPy do on this machine, on these programs, so that the first kohebi number has something honest to be compared against. The harness is built first on purpose, because a benchmark suite written after the runtime tends to be a suite the runtime happens to win.

## The rule

A number without a method is marketing. kohebi's headline claim is 10x faster and 10x less memory than CPython, which is a large enough claim that it should be disbelieved until someone can reproduce it. This repository exists to make that possible, including in the case where the answer is bad.

Four decisions follow from that, and none of them are negotiable:

**Medians, not means.** Benchmark timings are right-skewed. A run can be arbitrarily slow because something else touched the CPU, but it cannot be arbitrarily fast. The mean reports the noise and the median reports the machine.

**Confidence intervals on every comparison.** A speedup is reported as `2.10x [1.98, 2.23]`, from a bootstrap over the resampled ratio of medians. If the interval contains 1.0 the comparison is marked not significant, and it must not be quoted as a win. The bootstrap is seeded, so re-running the report on the same samples gives the same interval.

**Geometric mean across benchmarks.** An arithmetic mean of ratios overweights whichever benchmark you won hardest, which is how a runtime ends up publishing a number nobody else can get.

**Memory is never optional.** Every table reports peak RSS next to wall time. Reporting speed alone is how PyPy's real trade-off, roughly two to three times CPython's memory, stayed invisible to people choosing a runtime.

## Usage

```console
$ pip install -e '.[dev]'
$ kohebi-bench                                    # every installed runtime, 30 runs
$ kohebi-bench --runtime cpython --runtime pypy   # just these two
$ kohebi-bench benchmarks/micro --runs 50 --out results/local
```

Runtimes that are not installed are skipped with a note rather than silently omitted. A benchmark that fails or times out is recorded as a failure and appears in the report, because a runtime that cannot run a benchmark has not won it.

By default the run fails if the machine is too noisy to draw conclusions from, meaning fewer than 5 samples or an interquartile range above 5% of the median. `--allow-noisy` downgrades that to a warning, and is for local iteration rather than for anything published.

## What is measured

| Directory | Contents |
| --- | --- |
| `benchmarks/micro/` | Attribute dispatch, integer arithmetic, method calls, homogeneous lists, string building |
| `benchmarks/apps/` | JSON round-tripping, interpreter startup |

The micro benchmarks are chosen to isolate the specific bets in kohebi's design: shape-based attribute lookup, unboxed integers, inline caches on call sites, and PyPy-style list storage strategies. If those bets are wrong, these are the programs that say so first.

`benchmarks/apps/startup.py` is there because startup time is a real cost that steady-state benchmarks hide entirely, and because it is the number an AOT-compiled binary should win by the largest margin.

Two things are deliberately absent so far. There is no large application benchmark, and there is nothing multi-threaded. Both matter more than anything in `micro/`, and both need the runtime to exist before the benchmark can be shaped honestly.

`benchmarks/` is excluded from the formatter. Reformatting measured code changes what is being measured.

## How a measurement is taken

Each benchmark runs in a fresh child process. Warmup runs are discarded, then `--runs` timed runs are recorded, and peak RSS comes from `os.wait4` on that specific child.

That last detail is the one worth stating, because the obvious approach is wrong. `getrusage(RUSAGE_CHILDREN)` returns a monotonic high-water mark across every child the process has ever reaped, so the memory figure for PyPy would quietly inherit CPython's peak from the benchmark before it. The unit differs by platform too: kilobytes on Linux, bytes on macOS. Both traps are handled in `src/kohebi_bench/runtimes.py` and both are covered by a test.

Every benchmark computes a checksum and prints it. Without that, a sufficiently good compiler deletes the loop and the runtime that optimises hardest posts the fastest time by doing nothing.

## Runtimes compared

| Runtime | Version | Role |
| --- | --- | --- |
| CPython | 3.14 stable, default build | The baseline, unmodified and without flags chosen to flatter us |
| CPython with the JIT | 3.14, `PYTHON_JIT=1` | Their fastest configuration, so the comparison stays fair |
| CPython free-threaded | 3.14t | The relevant baseline for anything concurrent |
| PyPy | 7.3.23, targeting Python 3.11 | The incumbent fast Python |
| GraalPy | 25.2, targeting Python 3.12 | The other incumbent, and the compatibility standard |

PyPy and GraalPy both stopped at roughly 4x on general workloads, from completely different technology. That is the strongest available evidence about how hard the 10x target is, which is why both are in the default comparison rather than left out.

## Output

`--out DIR` writes `results.json` and `report.md`. The JSON records every sample, the resolved version string of every runtime, the git revision, and the machine description, so that a result can be argued with rather than only accepted.

Results published from CI are stored in `results/`, including the ones that are unflattering. Publishing only the good runs is the failure mode this whole repository is built to avoid.

CI results come from GitHub-hosted runners, which are shared machines and are noisy. They are useful for catching a large regression and useless for a 5% claim. Anything published as a headline number needs a quiet machine with frequency scaling and turbo disabled, and the report says which one it came from.

## Related

| Repository | Purpose |
| --- | --- |
| [tamnd/kohebi](https://github.com/tamnd/kohebi) | The runtime |
| [tamnd/kohebi-compat](https://github.com/tamnd/kohebi-compat) | Compatibility suite against CPython, and the published pass rates |

Benchmarks live outside the runtime repository on purpose. A performance claim should be reproducible by someone who does not trust us, and keeping the measurement next to the thing being measured makes that harder to believe.

## License

MIT or Apache-2.0, at your option.
