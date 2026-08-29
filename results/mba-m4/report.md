# Benchmark report

Generated 2026-08-29T07:46:13+00:00.
Baseline: `cpython`.

## What was measured

- Suite: `benchmarks/tier0`, 5 benchmark(s), 25 timed runs each after 3 warmup run(s).
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
| version.cpython-jit | Python 3.14.7 |
| version.kohebi-run | kohebi-run 0.0.13 |
| version.pypy | Python 3.11.15 (194f9f44b505, Aug 22 2026, 09:05:17) |
| virtualised | unknown |

> [!WARNING]
> 18 measurement(s) were too noisy to publish: fewer than 5 samples, or an interquartile range above 5% of the median. Re-run on a quiet machine.

## Where this leaves the goal

kohebi is aiming at 10x the speed of `cpython` on 0.1x its peak memory, both halves on the same run. The rivals are in this table too, because their speed is the bar and their memory is the reason there are two columns.

| Runtime | Speed | Peak memory | Still needed |
| --- | ---: | ---: | --- |
| kohebi-run | 0.61x | 0.28x | 16.4x faster, 2.8x leaner |
| cpython-jit | 1.01x | 0.99x |  |
| pypy | 6.68x | 2.26x |  |

Speed above 1.00x is faster than the baseline. Peak memory below 1.00x is leaner than it. Both are geometric means, and a geomean alone is not a result: the per-benchmark tables below are the number, and this is a summary of them.

## Per benchmark

| Benchmark | cpython-jit | kohebi-run | pypy |
| --- | ---: | ---: | ---: |
| `branch_dispatch` | 1.00x [0.99, 1.01] (not significant) | 0.55x [0.49, 0.60] | 6.24x [6.04, 6.56] |
| `float_loop` | 1.04x [0.99, 1.07] (not significant) | 0.60x [0.55, 0.63] | 7.44x [7.04, 7.65] |
| `int_loop` | 1.12x [1.07, 1.24] | 0.83x [0.78, 0.92] | 14.36x [13.46, 15.95] |
| `list_grow` | 0.92x [0.88, 1.00] (not significant) | 0.48x [0.45, 0.53] | 3.27x [3.05, 3.62] |
| `str_ops` | 0.96x [0.83, 1.11] (not significant) | 0.66x [0.60, 0.69] | 6.12x [5.56, 6.67] |

## Peak memory

Speed is never reported without it.

| Benchmark | cpython | cpython-jit | kohebi-run | pypy |
| --- | ---: | ---: | ---: | ---: |
| `branch_dispatch` | 13.4 MiB | 13.4 MiB | 3.0 MiB | 32.8 MiB |
| `float_loop` | 14.2 MiB | 13.1 MiB | 3.0 MiB | 32.9 MiB |
| `int_loop` | 13.9 MiB | 14.2 MiB | 3.2 MiB | 32.9 MiB |
| `list_grow` | 58.4 MiB | 59.4 MiB | 38.6 MiB | 108.7 MiB |
| `str_ops` | 14.1 MiB | 14.0 MiB | 3.1 MiB | 33.2 MiB |
