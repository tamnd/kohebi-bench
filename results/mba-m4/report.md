# Benchmark report

Generated 2026-08-29T09:40:28+00:00.
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
> 36 measurement(s) were too noisy to publish: fewer than 5 samples, or an interquartile range above 5% of the median. Re-run on a quiet machine.

## Where this leaves the goal

kohebi is aiming at 10x the speed of `cpython` on 0.1x its peak memory, both halves on the same run. The rivals are in this table too, because their speed is the bar and their memory is the reason there are two columns.

| Runtime | Speed | Peak memory | Still needed |
| --- | ---: | ---: | --- |
| kohebi-run | 1.37x | 0.37x | 7.3x faster, 3.7x leaner |
| pypy | 4.44x | 2.03x |  |

Speed above 1.00x is faster than the baseline. Peak memory below 1.00x is leaner than it. Both are geometric means, and a geomean alone is not a result: the per-benchmark tables below are the number, and this is a summary of them.

## Per benchmark

| Benchmark | kohebi-run | pypy |
| --- | ---: | ---: |
| `attribute_dispatch` | failed | 4.84x [4.35, 5.27] |
| `branch_dispatch` | 1.03x [0.97, 1.10] (not significant) | 8.24x [7.61, 8.92] |
| `float_loop` | 0.81x [0.73, 0.88] | 6.27x [5.82, 6.93] |
| `int_arithmetic` | failed | 12.36x [9.88, 14.40] |
| `int_loop` | 1.07x [0.96, 1.21] (not significant) | 10.64x [10.10, 11.49] |
| `iterate` | 1.18x [1.06, 1.37] | 9.89x [8.94, 11.45] |
| `json_roundtrip` | failed | 1.61x [1.27, 4.97] |
| `list_grow` | 1.47x [1.22, 1.75] | 4.36x [3.89, 5.46] |
| `list_index` | 1.03x [0.99, 1.17] (not significant) | 8.15x [7.53, 8.87] |
| `list_of_scalars` | failed | 2.96x [2.25, 3.26] |
| `method_call` | failed | 2.81x [2.04, 3.52] |
| `startup` | 8.15x [7.09, 8.59] | 1.15x [1.00, 1.23] (not significant) |
| `str_ops` | 0.95x [0.84, 1.03] (not significant) | 6.87x [6.02, 7.59] |
| `string_building` | failed | 0.95x [0.83, 1.06] (not significant) |

## Peak memory

Speed is never reported without it.

| Benchmark | cpython | kohebi-run | pypy |
| --- | ---: | ---: | ---: |
| `attribute_dispatch` | 18.4 MiB | n/a | 38.0 MiB |
| `branch_dispatch` | 14.6 MiB | 3.3 MiB | 33.5 MiB |
| `float_loop` | 14.0 MiB | 3.7 MiB | 32.9 MiB |
| `int_arithmetic` | 14.3 MiB | n/a | 36.9 MiB |
| `int_loop` | 14.4 MiB | 3.7 MiB | 33.2 MiB |
| `iterate` | 60.6 MiB | 49.7 MiB | 84.2 MiB |
| `json_roundtrip` | 34.9 MiB | n/a | 77.3 MiB |
| `list_grow` | 60.2 MiB | 39.0 MiB | 108.2 MiB |
| `list_index` | 33.4 MiB | 22.0 MiB | 70.3 MiB |
| `list_of_scalars` | 148.8 MiB | n/a | 158.8 MiB |
| `method_call` | 23.0 MiB | n/a | 50.7 MiB |
| `startup` | 14.3 MiB | 3.2 MiB | 31.0 MiB |
| `str_ops` | 14.5 MiB | 3.8 MiB | 33.0 MiB |
| `string_building` | 26.8 MiB | n/a | 58.2 MiB |

## Failures

| Benchmark | Runtime | Error |
| --- | --- | --- |
| `json_roundtrip` | kohebi-run | kohebi: benchmarks/apps/json_roundtrip.py: line 8: an import is not lowered yet |
| `attribute_dispatch` | kohebi-run | kohebi: benchmarks/micro/attribute_dispatch.py: line 8: an import is not lowered yet |
| `int_arithmetic` | kohebi-run | kohebi: benchmarks/micro/int_arithmetic.py: line 8: an import is not lowered yet |
| `list_of_scalars` | kohebi-run | kohebi: benchmarks/micro/list_of_scalars.py: line 8: an import is not lowered yet |
| `method_call` | kohebi-run | kohebi: benchmarks/micro/method_call.py: line 8: an import is not lowered yet |
| `string_building` | kohebi-run | kohebi: benchmarks/micro/string_building.py: line 8: an import is not lowered yet |
