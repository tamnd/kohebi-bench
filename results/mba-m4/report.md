# Benchmark report

Generated 2026-08-29T08:13:12+00:00.
Baseline: `cpython`.

## What was measured

- Suite: `benchmarks/tier0`, 5 benchmark(s), 15 timed runs each after 3 warmup run(s).
- Each benchmark is a whole process, startup included, because that is what a user experiences.

## Environment

| | |
| --- | --- |
| cpu_count | 10 |
| cpu_governor | unknown |
| host | mba-m4 |
| machine | arm64 |
| platform | macOS-15.8-arm64-arm-64bit-Mach-O |
| processor | Apple M4 |
| turbo | unknown |
| version.cpython | Python 3.14.7 |
| version.kohebi-run | kohebi-run 0.0.13 |
| version.pypy | Python 3.11.15 (194f9f44b505, Aug 22 2026, 09:05:17) |
| virtualised | unknown |

> [!WARNING]
> 5 measurement(s) were too noisy to publish: fewer than 5 samples, or an interquartile range above 5% of the median. Re-run on a quiet machine.

## Where this leaves the goal

kohebi is aiming at 10x the speed of `cpython` on 0.1x its peak memory, both halves on the same run. The rivals are in this table too, because their speed is the bar and their memory is the reason there are two columns.

| Runtime | Speed | Peak memory | Still needed |
| --- | ---: | ---: | --- |
| kohebi-run | 1.01x | 0.28x | 9.9x faster, 2.8x leaner |
| pypy | 7.39x | 2.21x |  |

Speed above 1.00x is faster than the baseline. Peak memory below 1.00x is leaner than it. Both are geometric means, and a geomean alone is not a result: the per-benchmark tables below are the number, and this is a summary of them.

## Per benchmark

| Benchmark | kohebi-run | pypy |
| --- | ---: | ---: |
| `branch_dispatch` | 0.90x [0.88, 0.92] | 7.02x [6.79, 7.14] |
| `float_loop` | 1.07x [0.96, 1.28] (not significant) | 7.19x [6.93, 8.54] |
| `int_loop` | 0.95x [0.94, 0.96] | 10.11x [9.42, 10.52] |
| `list_grow` | 1.21x [1.16, 1.24] | 5.93x [5.57, 6.23] |
| `str_ops` | 0.95x [0.93, 0.97] | 7.26x [7.06, 7.59] |

## Peak memory

Speed is never reported without it.

| Benchmark | cpython | kohebi-run | pypy |
| --- | ---: | ---: | ---: |
| `branch_dispatch` | 13.7 MiB | 3.2 MiB | 32.8 MiB |
| `float_loop` | 14.5 MiB | 3.6 MiB | 32.9 MiB |
| `int_loop` | 13.7 MiB | 3.0 MiB | 33.2 MiB |
| `list_grow` | 59.2 MiB | 38.1 MiB | 102.2 MiB |
| `str_ops` | 14.3 MiB | 3.3 MiB | 33.0 MiB |
