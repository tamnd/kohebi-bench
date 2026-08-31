# Benchmark report

Generated 2026-08-31T07:32:44+00:00.
Baseline: `cpython`.

## What was measured

- Suite: `benchmarks/tier0`, 11 benchmark(s), 30 timed runs each after 3 warmup run(s).
- Each benchmark is a whole process, startup included, because that is what a user experiences.

## Environment

| | |
| --- | --- |
| cpu_count | 32 |
| cpu_governor | unknown |
| host | GamingPC |
| machine | x86_64 |
| platform | Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43 |
| processor | 13th Gen Intel(R) Core(TM) i9-13900K |
| turbo | unknown |
| version.cpython | Python 3.14.4 |
| version.graalpy | GraalPy 3.13.14 (GraalVM CE Native 25.3.4.1) |
| version.kohebi-build | error: unexpected argument '--run' found |
| version.kohebi-run | kohebi-run 0.0.15 |
| version.pypy | Python 3.11.15 (194f9f44b505, May 25 2026, 19:34:11) |
| virtualised | wsl |

> [!NOTE]
> This machine is fine for catching a regression and is not a source of a headline number:
> - running under wsl, where the host schedules other tenants against us

> [!WARNING]
> 6 measurement(s) were too noisy to publish: fewer than 5 samples, or an interquartile range above 5% of the median. Re-run on a quiet machine.

## Where this leaves the goal

kohebi is aiming at 10x the speed of `cpython` on 0.1x its peak memory, both halves on the same run. The rivals are in this table too, because their speed is the bar and their memory is the reason there are two columns.

| Runtime | Speed | Peak memory | Still needed |
| --- | ---: | ---: | --- |
| kohebi-run | 0.38x | 0.56x | 26.1x faster, 5.6x leaner |
| graalpy | 0.46x | 20.21x |  |
| pypy | 2.91x | 5.84x |  |

Speed above 1.00x is faster than the baseline. Peak memory below 1.00x is leaner than it. Both are geometric means, and a geomean alone is not a result: the per-benchmark tables below are the number, and this is a summary of them.

## Per benchmark

| Benchmark | graalpy | kohebi-build | kohebi-run | pypy |
| --- | ---: | ---: | ---: | ---: |
| `branch_dispatch` | 0.55x [0.55, 0.55] | failed | 0.36x [0.35, 0.36] | 4.62x [4.25, 4.71] |
| `call` | 0.23x [0.23, 0.23] | failed | 0.31x [0.31, 0.31] | 2.10x [1.97, 2.14] |
| `comprehension` | 0.28x [0.28, 0.29] | failed | 0.21x [0.20, 0.21] | 0.99x [0.96, 1.01] (not significant) |
| `exceptions` | 0.35x [0.35, 0.35] | failed | 0.45x [0.45, 0.45] | 1.41x [1.40, 1.42] |
| `float_loop` | 0.60x [0.59, 0.60] | failed | 0.37x [0.37, 0.37] | 3.85x [3.79, 3.90] |
| `generators` | 0.36x [0.36, 0.37] | failed | 0.33x [0.33, 0.33] | 1.51x [1.49, 1.53] |
| `int_loop` | 0.93x [0.92, 0.93] | failed | 0.36x [0.36, 0.36] | 7.57x [7.42, 7.72] |
| `iterate` | 0.58x [0.58, 0.59] | failed | 0.46x [0.46, 0.47] | 4.69x [4.45, 4.75] |
| `list_grow` | 0.61x [0.60, 0.62] | failed | 0.59x [0.58, 0.59] | 2.54x [2.28, 2.60] |
| `list_index` | 0.53x [0.53, 0.53] | failed | 0.42x [0.42, 0.43] | 4.16x [4.09, 4.23] |
| `str_ops` | 0.46x [0.46, 0.46] | failed | 0.51x [0.50, 0.51] | 4.23x [4.17, 4.30] |

## Peak memory

Speed is never reported without it.

| Benchmark | cpython | graalpy | kohebi-build | kohebi-run | pypy |
| --- | ---: | ---: | ---: | ---: | ---: |
| `branch_dispatch` | 9.6 MiB | 284.0 MiB | n/a | 5.2 MiB | 68.7 MiB |
| `call` | 9.6 MiB | 300.0 MiB | n/a | 5.2 MiB | 77.5 MiB |
| `comprehension` | 9.8 MiB | 280.1 MiB | n/a | 5.3 MiB | 78.6 MiB |
| `exceptions` | 9.8 MiB | 294.1 MiB | n/a | 5.2 MiB | 78.3 MiB |
| `float_loop` | 9.8 MiB | 286.8 MiB | n/a | 5.1 MiB | 77.3 MiB |
| `generators` | 9.6 MiB | 291.0 MiB | n/a | 5.2 MiB | 78.1 MiB |
| `int_loop` | 9.6 MiB | 285.4 MiB | n/a | 5.1 MiB | 65.5 MiB |
| `iterate` | 51.0 MiB | 304.1 MiB | n/a | 38.9 MiB | 107.6 MiB |
| `list_grow` | 48.0 MiB | 292.4 MiB | n/a | 28.1 MiB | 125.0 MiB |
| `list_index` | 28.9 MiB | 294.2 MiB | n/a | 16.7 MiB | 109.3 MiB |
| `str_ops` | 9.6 MiB | 284.6 MiB | n/a | 5.1 MiB | 77.0 MiB |

## Failures

| Benchmark | Runtime | Error |
| --- | --- | --- |
| every benchmark (11) | kohebi-build | error: unexpected argument '--run' found |
