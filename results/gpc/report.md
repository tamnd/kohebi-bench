# Benchmark report

Generated 2026-08-28T08:51:17+00:00.
Baseline: `cpython`.

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
| version.graalpy | GraalPy 3.12.8 (Oracle GraalVM Native 25.2.4) |
| version.pypy | Python 3.11.15 (194f9f44b505, May 25 2026, 19:34:11) |
| virtualised | wsl |

> [!NOTE]
> This machine is fine for catching a regression and is not a source of a headline number:
> - running under wsl, where the host schedules other tenants against us

> [!WARNING]
> 4 measurement(s) were too noisy to publish: fewer than 5 samples, or an interquartile range above 5% of the median. Re-run on a quiet machine.

## Geomean speedup

| Runtime | Speedup |
| --- | ---: |
| graalpy | 0.46x |
| pypy | 1.52x |

A geomean alone is not a result. The per-benchmark table below is the number; the geomean is a summary of it.

## Per benchmark

| Benchmark | graalpy | pypy |
| --- | ---: | ---: |
| `attribute_dispatch` | 0.35x [0.34, 0.35] | 2.55x [2.51, 2.62] |
| `int_arithmetic` | 1.92x [1.87, 1.94] | 8.54x [8.32, 8.61] |
| `json_roundtrip` | 0.30x [0.30, 0.31] | 0.74x [0.73, 0.74] |
| `list_of_scalars` | 1.05x [1.03, 1.06] | 2.03x [1.98, 2.05] |
| `method_call` | 0.29x [0.28, 0.31] | 2.05x [2.02, 2.09] |
| `startup` | 0.28x [0.27, 0.29] | 0.47x [0.46, 0.48] |
| `string_building` | 0.25x [0.25, 0.26] | 0.61x [0.58, 0.63] |

## Peak memory

Speed is never reported without it.

| Benchmark | cpython | graalpy | pypy |
| --- | ---: | ---: | ---: |
| `attribute_dispatch` | 17.9 MiB | 283.3 MiB | 76.8 MiB |
| `int_arithmetic` | 17.9 MiB | 259.5 MiB | 76.7 MiB |
| `json_roundtrip` | 32.1 MiB | 286.5 MiB | 104.5 MiB |
| `list_of_scalars` | 137.9 MiB | 258.9 MiB | 204.2 MiB |
| `method_call` | 20.1 MiB | 288.3 MiB | 82.2 MiB |
| `startup` | 17.9 MiB | 160.7 MiB | 59.5 MiB |
| `string_building` | 23.9 MiB | 251.2 MiB | 96.0 MiB |
