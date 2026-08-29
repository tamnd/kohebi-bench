# kohebi-bench

Benchmarks for [kohebi](https://github.com/tamnd/kohebi), a Python runtime written in Rust, measured against CPython, PyPy, and GraalPy.

[![Benchmarks](https://github.com/tamnd/kohebi-bench/actions/workflows/bench.yml/badge.svg)](https://github.com/tamnd/kohebi-bench/actions/workflows/bench.yml)
[![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue.svg)](#license)

> [!NOTE]
> kohebi runs its first Python programs as of the tier zero interpreter, so `kohebi-bench run benchmarks/tier0` is the first end to end comparison in here. Everything in `micro/` and `apps/` still needs functions, `for` loops, attributes or subscripting, none of which the runtime has yet, so those directories measure CPython, PyPy, and GraalPy alone for now. The harness was built before the runtime on purpose, because a benchmark suite written afterwards tends to be one the runtime happens to win.

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
$ kohebi-bench run                                    # every installed runtime, 30 runs
$ kohebi-bench run --runtime cpython --runtime pypy   # just these two
$ kohebi-bench run benchmarks/micro --runs 50 --out results/local
$ kohebi-bench run benchmarks/tier0 --kohebi ../kohebi/target/release/kohebi
$ kohebi-bench lex --kohebi ../kohebi/target/release/kohebi
```

`--kohebi` points the `kohebi-run` and `kohebi-build` rows at a particular binary. Nobody installs kohebi before benchmarking a change to it, and without the flag the report quietly measures whichever build happens to be on PATH.

Runtimes that are not installed are skipped with a note rather than silently omitted. A benchmark that fails or times out is recorded as a failure and appears in the report, because a runtime that cannot run a benchmark has not won it.

By default the run fails if the machine is too noisy to draw conclusions from, meaning fewer than 5 samples or an interquartile range above 5% of the median. `--allow-noisy` downgrades that to a warning, and is for local iteration rather than for anything published.

## The lexer, which is the part that exists

`kohebi-bench lex` tokenizes a corpus with both kohebi and CPython's `tokenize` module and times them against each other. The corpus defaults to the standard library of the interpreter running the harness, which is around 1900 files and 35 MiB of Python written by many hands over thirty years, and is on every machine that can run this.

Both sides print `<tokens> <path>` for every file, and those outputs are compared before anything is timed. If they disagree the run stops and prints the file and the two counts. A speed number from an implementation that produced the wrong answer is worse than no number at all.

Both sides read bytes, decode them as UTF-8, and produce tokens with line and column positions, because timing one implementation doing less work than the other is the exact mistake this repository exists to prevent. The process startup cost of each side is measured separately on an empty corpus and reported next to the throughput, so a reader can take it back out.

A file that CPython's own tokenizer refuses is left out, and so is one that kohebi refuses. There is at least one of the second kind in every standard library: `tokenize` reports `€ = 2` as a name while the compiler rejects the character, and kohebi follows the compiler because that is what a user sees. Each exclusion is printed with its reason and counted in the report. More than 25 of them stops the run, because at that point it is a regression rather than a known corner, and a benchmark that shrinks its own corpus until it passes is worthless.

Agreement itself is decided in [tamnd/kohebi-compat](https://github.com/tamnd/kohebi-compat), which compares token by token including positions and text. The check here is only that both sides did the same job before either was timed.

## What is measured

| Directory | Contents |
| --- | --- |
| `benchmarks/tier0/` | Integer and float loops, branch dispatch, string operators, list growth |
| `benchmarks/micro/` | Attribute dispatch, integer arithmetic, method calls, homogeneous lists, string building |
| `benchmarks/apps/` | JSON round-tripping, interpreter startup |

The micro benchmarks are chosen to isolate the specific bets in kohebi's design: shape-based attribute lookup, unboxed integers, inline caches on call sites, and PyPy-style list storage strategies. If those bets are wrong, these are the programs that say so first.

`benchmarks/apps/startup.py` is there because startup time is a real cost that steady-state benchmarks hide entirely, and because it is the number an AOT-compiled binary should win by the largest margin.

## The tier zero suite, which is the part kohebi can run today

`benchmarks/tier0/` exists because a comparison you cannot run is not a comparison. The tier zero interpreter has assignment, arithmetic, comparison, the boolean operators, `if`, `while`, `break`, `continue`, container displays, `in`, and `print`. It does not have functions, `for` loops, attributes, subscripting, iteration or imports yet, so the five programs in there are written entirely with what exists.

That makes them a little strange to read. Collatz is inlined rather than called, buckets are five separate names rather than a list, and a list is grown with `items += [i]` because there are no method calls. Every one of them was diffed against CPython 3.14 and PyPy before it went in, so all three runtimes print the same bytes, and none of them is doing less work than the others.

These are temporary. When kohebi can run `micro/int_arithmetic.py` as a person would write it, `tier0/int_loop.py` has done its job and comes out. What it buys in the meantime is a real number every week instead of a promise, and the first one already said something useful, which is in `results/`.

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

Results published from real machines are stored in `results/<host>/report.md`, including the unflattering ones. Publishing only the good runs is the failure mode this whole repository is built to avoid. The raw `results.json` is not committed: it is a few hundred kilobytes of samples per run, it changes completely every time, and a repository whose history is mostly regenerated JSON is one nobody can read. Pass `--out` and keep it locally, or take it from the CI artifact.

CI results come from GitHub-hosted runners, which are shared machines and are noisy. They are useful for catching a large regression and useless for a 5% claim. Anything published as a headline number needs a quiet machine with frequency scaling and turbo disabled, and the report says which one it came from.

## Running on real hardware

```console
$ scripts/bench-on.sh gpc run --runs 30
$ scripts/bench-on.sh server3 run benchmarks/micro
$ scripts/bench-on.sh gpc lex
```

The script copies the tracked files over ssh, runs the harness there, and pulls the results back into `results/<host>/`. Nothing is installed on the remote side: the harness is standard library only and runs from `PYTHONPATH`, so the machine is left as it was found apart from one directory under `/tmp`.

Every report names the machine it came from and says what is wrong with it. The environment table records the CPU model, the governor, whether turbo is on, and whether the kernel thinks it is running under a hypervisor, and a report from a machine that fails any of those tests carries a note saying it is fit for catching regressions rather than for publishing a number.

| Host | What it is | Fit for |
| --- | --- | --- |
| `gpc` | i9-13900K, 32 threads, 31 GiB, Ubuntu under WSL2 | The reference machine, and the only one with all four runtimes installed |
| `server1`, `server2`, `server3` | Shared KVM guests, 4 to 8 vCPUs of EPYC | Regressions and smoke runs, not headline numbers |
| `mba-m4` | Apple M4 MacBook Air, fanless, 10 cores | The development laptop. It throttles under a long run and the report says so |

`gpc` is a desktop running WSL2, which is honest about what it is: good enough that the intervals in `results/gpc/` are tight, not good enough to defend a few percent. The published 10x claim, when there is something to claim, needs a machine with nothing else on it, the governor pinned to performance, and turbo off.

## Related

| Repository | Purpose |
| --- | --- |
| [tamnd/kohebi](https://github.com/tamnd/kohebi) | The runtime |
| [tamnd/kohebi-compat](https://github.com/tamnd/kohebi-compat) | Compatibility suite against CPython, and the published pass rates |

Benchmarks live outside the runtime repository on purpose. A performance claim should be reproducible by someone who does not trust us, and keeping the measurement next to the thing being measured makes that harder to believe.

## License

MIT or Apache-2.0, at your option.
