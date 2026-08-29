# Benchmark report

Generated 2026-08-29T09:03:35+00:00.
Baseline: `cpython`.

## What was measured

- Suite: `benchmarks/tier0`, 6 benchmark(s), 40 timed runs each after 3 warmup run(s).
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
| version.kohebi-run | kohebi-run 0.0.13 |
| version.pypy | Python 3.11.15 (194f9f44b505, May 25 2026, 19:34:11) |
| virtualised | wsl |

> [!NOTE]
> This machine is fine for catching a regression and is not a source of a headline number:
> - running under wsl, where the host schedules other tenants against us

> [!WARNING]
> 17 measurement(s) were too noisy to publish: fewer than 5 samples, or an interquartile range above 5% of the median. Re-run on a quiet machine.

## Where this leaves the goal

kohebi is aiming at 10x the speed of `cpython` on 0.1x its peak memory, both halves on the same run. The rivals are in this table too, because their speed is the bar and their memory is the reason there are two columns.

| Runtime | Speed | Peak memory | Still needed |
| --- | ---: | ---: | --- |
| kohebi-run | 0.52x | 0.50x | 19.3x faster, 5.0x leaner |
| pypy | 3.81x | 5.38x |  |

Speed above 1.00x is faster than the baseline. Peak memory below 1.00x is leaner than it. Both are geometric means, and a geomean alone is not a result: the per-benchmark tables below are the number, and this is a summary of them.

## Per benchmark

| Benchmark | kohebi-run | pypy |
| --- | ---: | ---: |
| `branch_dispatch` | 0.47x [0.44, 0.55] | 3.73x [3.44, 4.08] |
| `float_loop` | 0.60x [0.54, 0.64] | 4.72x [4.02, 5.01] |
| `int_loop` | 0.37x [0.37, 0.42] | 6.96x [6.53, 8.27] |
| `list_grow` | 0.68x [0.65, 0.79] | 2.28x [2.07, 2.70] |
| `list_index` | 0.40x [0.38, 0.42] | 2.88x [2.56, 3.00] |
| `str_ops` | 0.65x [0.59, 0.71] | 3.82x [3.55, 4.59] |

## Peak memory

Speed is never reported without it.

| Benchmark | cpython | kohebi-run | pypy |
| --- | ---: | ---: | ---: |
| `branch_dispatch` | 9.7 MiB | 4.5 MiB | 65.7 MiB |
| `float_loop` | 9.8 MiB | 4.5 MiB | 74.4 MiB |
| `int_loop` | 9.6 MiB | 4.5 MiB | 62.4 MiB |
| `list_grow` | 48.0 MiB | 27.5 MiB | 122.2 MiB |
| `list_index` | 28.9 MiB | 16.1 MiB | 106.3 MiB |
| `str_ops` | 9.6 MiB | 4.5 MiB | 74.1 MiB |

