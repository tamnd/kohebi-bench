# Results

One directory per machine, each holding the markdown report from the last run on it. The raw `results.json` a run also writes is deliberately not committed, because a number is only worth keeping next to the method that produced it and the method is in the report.

| Directory | Machine | Notes |
| --- | --- | --- |
| `mba-m4` | MacBook Air, Apple M4, macOS 15.8 | Fanless, so a long run heats up and the harness usually flags it as noisy |
| `gpc` | i9-13900K, 32 threads, Linux under WSL2 | Quieter under load, but a hypervisor schedules other tenants against it |

Neither is a source of a headline number and the harness says so in both reports. They are here to catch a regression and to show where the work is.

## Read both, because they do not agree

The same three runtimes on the same fourteen benchmarks put kohebi at 1.37x CPython on the MacBook Air and 0.79x on the i9. That is not measurement noise, it is a factor of about two, and until it is understood the conservative number is the one to work against.

The absolute times say where it comes from. Moving from the Air to the i9 makes CPython between 2.1x and 3.2x faster on every benchmark. It makes kohebi 1.19x to 1.28x faster on the four that are nothing but a loop, and 1.4x to 1.9x faster on the three that allocate. PyPy lands in between. So kohebi's interpreter loop picks up almost exactly the clock ratio between the two chips and nothing else, while CPython picks up well over it.

| Benchmark | CPython, Air to i9 | kohebi, Air to i9 |
| --- | ---: | ---: |
| `branch_dispatch` | 2.89x | 1.28x |
| `int_loop` | 2.74x | 1.19x |
| `float_loop` | 2.11x | 1.21x |
| `iterate` | 2.36x | 1.19x |
| `list_index` | 2.41x | 1.39x |
| `list_grow` | 3.16x | 1.64x |
| `str_ops` | 2.93x | 1.87x |

What that is not: a codegen target. Rebuilding kohebi on the i9 with `-C target-cpu=native` rather than the generic `x86-64` baseline moves nothing, on any of the three loop benchmarks, in either direction beyond run to run variation. So the generic build is not leaving instructions on the table.

What it might be, in rough order of how much would have to be true: the Air throttles, and the harness did flag thirty six of that run's measurements as too noisy to publish. The macOS CPython is a framework build and the Linux one is not, which is a real cost but not usually this large. Or the interpreter's hot loop has a bottleneck that happens to be flat across the two microarchitectures, in which case the loop benchmarks scaling at exactly the clock ratio is the symptom and the answer is in a profile rather than in a table.

Until that is settled, the working number for the goal is 0.79x rather than 1.37x, which means the interpreter is behind CPython rather than level with it, and the next piece of work is a profile on the machine where the gap is visible.
