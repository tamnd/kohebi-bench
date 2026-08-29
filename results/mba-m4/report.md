# Benchmark report

Generated 2026-08-29T10:00:32+00:00.
Baseline: `cpython`.

## What was measured

- Suite: `benchmarks`, 14 benchmark(s), 15 timed runs each after 3 warmup run(s).
- Each benchmark is a whole process, startup included, because that is what a user experiences.

## Environment

| | |
| --- | --- |
| cpu_count | 10 |
| cpu_governor | unknown |
| host | USERnoMacBook-Air.local |
| machine | arm64 |
| platform | macOS-15.8-arm64-arm-64bit-Mach-O |
| processor | Apple M4 |
| turbo | unknown |
| version.cpython | Python 3.14.7 |
| version.kohebi-run | kohebi-run 0.0.13 |
| version.pypy | Python 3.11.15 (194f9f44b505, Aug 22 2026, 09:05:17) |
| virtualised | unknown |

> [!WARNING]
> 35 measurement(s) were too noisy to publish: fewer than 5 samples, or an interquartile range above 5% of the median. Re-run on a quiet machine.

## Where this leaves the goal

kohebi is aiming at 10x the speed of `cpython` on 0.1x its peak memory, both halves on the same run. The rivals are in this table too, because their speed is the bar and their memory is the reason there are two columns.

| Runtime | Speed | Peak memory | Still needed |
| --- | ---: | ---: | --- |
| kohebi-run | 0.99x | 0.36x | 10.1x faster, 3.6x leaner |
| pypy | 2.96x | 1.89x |  |

Speed above 1.00x is faster than the baseline. Peak memory below 1.00x is leaner than it. Both are geometric means, and a geomean alone is not a result: the per-benchmark tables below are the number, and this is a summary of them.

## Per benchmark

| Benchmark | kohebi-run | pypy |
| --- | ---: | ---: |
| `attribute_dispatch` | failed | 2.27x [1.37, 3.49] |
| `branch_dispatch` | 0.86x [0.56, 1.13] (not significant) | 6.21x [4.59, 7.88] |
| `float_loop` | 0.66x [0.57, 0.71] | 4.87x [4.39, 5.40] |
| `int_arithmetic` | failed | 12.26x [10.75, 12.72] |
| `int_loop` | 0.82x [0.74, 1.00] (not significant) | 8.06x [6.81, 10.36] |
| `iterate` | 1.12x [0.99, 1.21] (not significant) | 6.51x [5.43, 7.15] |
| `json_roundtrip` | failed | 0.81x [0.75, 0.85] |
| `list_grow` | 1.07x [0.96, 1.26] (not significant) | 4.23x [3.59, 5.05] |
| `list_index` | 0.81x [0.73, 0.93] | 4.67x [4.11, 5.61] |
| `list_of_scalars` | failed | 1.45x [0.99, 1.63] (not significant) |
| `method_call` | failed | 2.21x [1.94, 2.79] |
| `startup` | 5.01x [4.69, 5.46] | 0.69x [0.66, 0.74] |
| `str_ops` | 0.42x [0.31, 0.53] | 4.30x [3.31, 4.56] |
| `string_building` | failed | 0.60x [0.48, 0.85] |

## Peak memory

Speed is never reported without it.

| Benchmark | cpython | kohebi-run | pypy |
| --- | ---: | ---: | ---: |
| `attribute_dispatch` | 20.0 MiB | n/a | 38.6 MiB |
| `branch_dispatch` | 14.4 MiB | 3.5 MiB | 33.6 MiB |
| `float_loop` | 14.7 MiB | 3.4 MiB | 33.0 MiB |
| `int_arithmetic` | 17.0 MiB | n/a | 36.8 MiB |
| `int_loop` | 14.8 MiB | 3.5 MiB | 33.2 MiB |
| `iterate` | 61.0 MiB | 50.2 MiB | 90.2 MiB |
| `json_roundtrip` | 41.0 MiB | n/a | 53.8 MiB |
| `list_grow` | 60.3 MiB | 38.5 MiB | 104.7 MiB |
| `list_index` | 33.8 MiB | 21.4 MiB | 70.4 MiB |
| `list_of_scalars` | 149.5 MiB | n/a | 165.3 MiB |
| `method_call` | 26.0 MiB | n/a | 50.8 MiB |
| `startup` | 13.6 MiB | 3.0 MiB | 29.9 MiB |
| `str_ops` | 14.8 MiB | 4.0 MiB | 33.4 MiB |
| `string_building` | 29.7 MiB | n/a | 58.3 MiB |

## Failures

| Benchmark | Runtime | Error |
| --- | --- | --- |
| `json_roundtrip` | kohebi-run | kohebi: benchmarks/apps/json_roundtrip.py: line 8: an import is not lowered yet |
| `attribute_dispatch` | kohebi-run | kohebi: benchmarks/micro/attribute_dispatch.py: line 8: an import is not lowered yet |
| `int_arithmetic` | kohebi-run | kohebi: benchmarks/micro/int_arithmetic.py: line 8: an import is not lowered yet |
| `list_of_scalars` | kohebi-run | kohebi: benchmarks/micro/list_of_scalars.py: line 8: an import is not lowered yet |
| `method_call` | kohebi-run | kohebi: benchmarks/micro/method_call.py: line 8: an import is not lowered yet |
| `string_building` | kohebi-run | kohebi: benchmarks/micro/string_building.py: line 8: an import is not lowered yet |
