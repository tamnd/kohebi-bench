# Benchmark report

Generated 2026-08-29T12:57:06+00:00.
Baseline: `cpython`.

## What was measured

- Suite: `benchmarks/tier0`, 10 benchmark(s), 30 timed runs each after 3 warmup run(s).
- Each benchmark is a whole process, startup included, because that is what a user experiences.

## Environment

| | |
| --- | --- |
| cpu_count | 32 |
| cpu_governor | unknown |
| host | gpc |
| machine | x86_64 |
| platform | Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43 |
| processor | 13th Gen Intel(R) Core(TM) i9-13900K |
| turbo | unknown |
| version.cpython | Python 3.14.4 |
| version.graalpy | GraalPy 3.13.14 (GraalVM CE Native 25.3.4.1) |
| version.kohebi-build | error: unexpected argument '--run' found |
| version.kohebi-run | kohebi-run 0.0.14 |
| version.pypy | Python 3.11.15 (194f9f44b505, May 25 2026, 19:34:11) |
| virtualised | wsl |

> [!NOTE]
> This machine is fine for catching a regression and is not a source of a headline number:
> - running under wsl, where the host schedules other tenants against us

> [!WARNING]
> 1 measurement(s) were too noisy to publish: fewer than 5 samples, or an interquartile range above 5% of the median. Re-run on a quiet machine.

## Where this leaves the goal

kohebi is aiming at 10x the speed of `cpython` on 0.1x its peak memory, both halves on the same run. The rivals are in this table too, because their speed is the bar and their memory is the reason there are two columns.

| Runtime | Speed | Peak memory | Still needed |
| --- | ---: | ---: | --- |
| kohebi-run | 0.40x | 0.56x | 25.2x faster, 5.6x leaner |
| graalpy | 0.50x | 19.41x |  |
| pypy | 3.01x | 5.70x |  |

Speed above 1.00x is faster than the baseline. Peak memory below 1.00x is leaner than it. Both are geometric means, and a geomean alone is not a result: the per-benchmark tables below are the number, and this is a summary of them.

## Per benchmark

| Benchmark | graalpy | kohebi-build | kohebi-run | pypy |
| --- | ---: | ---: | ---: | ---: |
| `branch_dispatch` | 0.59x [0.58, 0.59] | failed | 0.37x [0.37, 0.37] | 4.54x [4.48, 4.57] |
| `call` | 0.24x [0.24, 0.24] | failed | 0.32x [0.32, 0.32] | 1.98x [1.96, 2.00] |
| `comprehension` | 0.29x [0.29, 0.29] | failed | 0.20x [0.20, 0.20] | 0.92x [0.91, 0.93] |
| `exceptions` | 0.36x [0.36, 0.36] | failed | 0.47x [0.47, 0.48] | 1.39x [1.38, 1.40] |
| `float_loop` | 0.64x [0.63, 0.64] | failed | 0.38x [0.38, 0.39] | 3.77x [3.75, 3.80] |
| `int_loop` | 1.00x [0.99, 1.02] (not significant) | failed | 0.36x [0.36, 0.37] | 7.53x [7.44, 7.61] |
| `iterate` | 0.61x [0.60, 0.61] | failed | 0.46x [0.45, 0.46] | 4.63x [4.60, 4.70] |
| `list_grow` | 0.60x [0.59, 0.61] | failed | 0.58x [0.58, 0.59] | 2.36x [2.33, 2.39] |
| `list_index` | 0.54x [0.54, 0.54] | failed | 0.44x [0.44, 0.44] | 4.07x [4.01, 4.11] |
| `str_ops` | 0.49x [0.49, 0.50] | failed | 0.52x [0.52, 0.53] | 4.20x [4.16, 4.24] |

## Peak memory

Speed is never reported without it.

| Benchmark | cpython | graalpy | kohebi-build | kohebi-run | pypy |
| --- | ---: | ---: | ---: | ---: | ---: |
| `branch_dispatch` | 9.6 MiB | 284.9 MiB | n/a | 5.1 MiB | 69.9 MiB |
| `call` | 9.6 MiB | 298.9 MiB | n/a | 5.1 MiB | 78.2 MiB |
| `comprehension` | 9.8 MiB | 280.1 MiB | n/a | 5.4 MiB | 79.1 MiB |
| `exceptions` | 9.8 MiB | 293.8 MiB | n/a | 5.1 MiB | 78.8 MiB |
| `float_loop` | 9.8 MiB | 289.0 MiB | n/a | 5.1 MiB | 78.0 MiB |
| `int_loop` | 9.6 MiB | 283.6 MiB | n/a | 5.1 MiB | 66.6 MiB |
| `iterate` | 51.1 MiB | 303.3 MiB | n/a | 38.8 MiB | 108.2 MiB |
| `list_grow` | 48.0 MiB | 292.7 MiB | n/a | 28.0 MiB | 125.7 MiB |
| `list_index` | 28.9 MiB | 293.4 MiB | n/a | 16.6 MiB | 109.8 MiB |
| `str_ops` | 9.6 MiB | 287.4 MiB | n/a | 5.1 MiB | 77.8 MiB |

## Failures

| Benchmark | Runtime | Error |
| --- | --- | --- |
| every benchmark (10) | kohebi-build | error: unexpected argument '--run' found |
