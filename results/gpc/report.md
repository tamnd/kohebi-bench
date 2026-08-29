# Benchmark report

Generated 2026-08-29T09:46:05+00:00.
Baseline: `cpython`.

## What was measured

- Suite: `benchmarks`, 14 benchmark(s), 15 timed runs each after 3 warmup run(s).
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
| version.kohebi-run | kohebi-run 0.0.13 |
| version.pypy | Python 3.11.15 (194f9f44b505, May 25 2026, 19:34:11) |
| virtualised | wsl |

> [!NOTE]
> This machine is fine for catching a regression and is not a source of a headline number:
> - running under wsl, where the host schedules other tenants against us

> [!WARNING]
> 47 measurement(s) were too noisy to publish: fewer than 5 samples, or an interquartile range above 5% of the median. Re-run on a quiet machine.

## Where this leaves the goal

kohebi is aiming at 10x the speed of `cpython` on 0.1x its peak memory, both halves on the same run. The rivals are in this table too, because their speed is the bar and their memory is the reason there are two columns.

| Runtime | Speed | Peak memory | Still needed |
| --- | ---: | ---: | --- |
| kohebi-run | 0.79x | 0.53x | 12.6x faster, 5.3x leaner |
| graalpy | 0.46x | 14.30x |  |
| pypy | 2.64x | 4.27x |  |

Speed above 1.00x is faster than the baseline. Peak memory below 1.00x is leaner than it. Both are geometric means, and a geomean alone is not a result: the per-benchmark tables below are the number, and this is a summary of them.

## Per benchmark

| Benchmark | graalpy | kohebi-run | pypy |
| --- | ---: | ---: | ---: |
| `attribute_dispatch` | 0.25x [0.21, 0.27] | failed | 2.90x [2.37, 3.09] |
| `branch_dispatch` | 0.48x [0.41, 0.50] | 0.46x [0.41, 0.47] | 4.98x [4.39, 5.08] |
| `float_loop` | 0.50x [0.48, 0.55] | 0.46x [0.43, 0.50] | 3.50x [3.38, 3.80] |
| `int_arithmetic` | 1.75x [1.42, 1.91] | failed | 11.54x [10.78, 12.31] |
| `int_loop` | 0.83x [0.81, 0.86] | 0.46x [0.41, 0.50] | 6.96x [6.46, 7.48] |
| `iterate` | 0.55x [0.52, 0.74] | 0.60x [0.53, 0.69] | 4.61x [4.33, 4.88] |
| `json_roundtrip` | 0.25x [0.23, 0.27] | failed | 0.67x [0.62, 0.72] |
| `list_grow` | 0.57x [0.54, 0.61] | 0.77x [0.72, 0.80] | 2.98x [2.80, 3.55] |
| `list_index` | 0.53x [0.49, 0.60] | 0.60x [0.53, 0.66] | 3.86x [3.61, 4.34] |
| `list_of_scalars` | 0.96x [0.87, 1.01] (not significant) | failed | 1.93x [1.76, 2.05] |
| `method_call` | 0.23x [0.21, 0.30] | failed | 2.09x [1.92, 2.22] |
| `startup` | 0.23x [0.20, 0.26] | 9.75x [8.60, 11.33] | 0.57x [0.50, 0.65] |
| `str_ops` | 0.44x [0.40, 0.45] | 0.61x [0.56, 0.68] | 3.41x [3.10, 3.62] |
| `string_building` | 0.23x [0.20, 0.27] | failed | 0.72x [0.63, 0.85] |

## Peak memory

Speed is never reported without it.

| Benchmark | cpython | graalpy | kohebi-run | pypy |
| --- | ---: | ---: | ---: | ---: |
| `attribute_dispatch` | 15.4 MiB | 319.2 MiB | n/a | 77.5 MiB |
| `branch_dispatch` | 9.6 MiB | 287.7 MiB | 4.8 MiB | 65.6 MiB |
| `float_loop` | 9.8 MiB | 287.9 MiB | 4.8 MiB | 74.3 MiB |
| `int_arithmetic` | 11.6 MiB | 314.8 MiB | n/a | 77.2 MiB |
| `int_loop` | 9.6 MiB | 285.8 MiB | 4.8 MiB | 62.4 MiB |
| `iterate` | 51.0 MiB | 306.8 MiB | 37.8 MiB | 104.6 MiB |
| `json_roundtrip` | 32.0 MiB | 310.4 MiB | n/a | 91.5 MiB |
| `list_grow` | 48.0 MiB | 292.3 MiB | 27.8 MiB | 122.0 MiB |
| `list_index` | 28.9 MiB | 295.9 MiB | 16.3 MiB | 106.2 MiB |
| `list_of_scalars` | 137.9 MiB | 314.0 MiB | n/a | 204.9 MiB |
| `method_call` | 20.3 MiB | 326.7 MiB | n/a | 82.9 MiB |
| `startup` | 9.5 MiB | 197.2 MiB | 4.1 MiB | 55.4 MiB |
| `str_ops` | 9.6 MiB | 286.9 MiB | 4.8 MiB | 74.0 MiB |
| `string_building` | 24.1 MiB | 297.2 MiB | n/a | 96.6 MiB |

## Failures

| Benchmark | Runtime | Error |
| --- | --- | --- |
| `json_roundtrip` | kohebi-run | kohebi: benchmarks/apps/json_roundtrip.py: line 8: an import is not lowered yet |
| `attribute_dispatch` | kohebi-run | kohebi: benchmarks/micro/attribute_dispatch.py: line 8: an import is not lowered yet |
| `int_arithmetic` | kohebi-run | kohebi: benchmarks/micro/int_arithmetic.py: line 8: an import is not lowered yet |
| `list_of_scalars` | kohebi-run | kohebi: benchmarks/micro/list_of_scalars.py: line 8: an import is not lowered yet |
| `method_call` | kohebi-run | kohebi: benchmarks/micro/method_call.py: line 8: an import is not lowered yet |
| `string_building` | kohebi-run | kohebi: benchmarks/micro/string_building.py: line 8: an import is not lowered yet |
