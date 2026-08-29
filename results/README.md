# Results

One directory per machine, each holding the markdown report from the last run on it. The raw `results.json` a run also writes is deliberately not committed, because a number is only worth keeping next to the method that produced it and the method is in the report.

| Directory | Machine | Notes |
| --- | --- | --- |
| `mba-m4` | MacBook Air, Apple M4, macOS 15.8 | Fanless, so a long run heats up and the harness usually flags it as noisy |
| `gpc` | i9-13900K, 32 threads, Linux under WSL2 | Quieter under load, but a hypervisor schedules other tenants against it |

Neither is a source of a headline number and the harness says so in both reports. They are here to catch a regression and to show where the work is.

## Every earlier report from this machine was measured against a crippled CPython

The two machines disagreed. kohebi came out at 1.37x CPython on the Air and 0.79x on the i9, on the same fourteen benchmarks in the same afternoon, and a factor of two is not a gap between two chips.

It was the baseline. Homebrew builds CPython with `--with-dtrace`, and macOS always has DTrace, so those probes are real code in the eval loop rather than the nothing they compile to on a Linux box without the systemtap headers. Five million times around a `while i < n: i = i + 1`, on the same Mac, both of them CPython 3.14.7:

| Build | Wall |
| --- | ---: |
| Homebrew `python3.14`, `WITH_DTRACE=1` | 0.80s |
| `uv python install 3.14`, `WITH_DTRACE=0` | 0.24s |
| Apple's own `/usr/bin/python3`, version 3.9.6 | 0.45s |

A five year old Python beat the current one by nearly a factor of two, which is the tell. Everything ever published from this directory against that baseline made kohebi look about three times better than it is.

The harness refuses to run against it now. `Runtime.crippled` asks CPython how it was built and stops before anything is timed, the same way `Runtime.misidentified` asks it what it is. That is two classes of dishonest baseline caught by asking the interpreter a question rather than trusting a name on PATH, and both were found by a number that was too good rather than by a test.

## Where it actually stands

Re-run against a build without the probes, the two machines now say roughly the same thing. Speed as a multiple of CPython, higher is better:

| Benchmark | Air | i9 |
| --- | ---: | ---: |
| `branch_dispatch` | 0.86x | 0.46x |
| `float_loop` | 0.66x | 0.46x |
| `int_loop` | 0.82x | 0.46x |
| `iterate` | 1.12x | 0.60x |
| `list_grow` | 1.07x | 0.77x |
| `list_index` | 0.81x | 0.60x |
| `str_ops` | 0.42x | 0.61x |
| `startup` | 5.01x | 9.75x |

So kohebi is somewhere between a half and level with CPython on work, well ahead of it on starting, and at about a third of its memory. Against a goal of 10x on 0.1x memory, memory is the half that is going well without anyone working on it and speed is the half that has not started: this is a tier zero interpreter with no quickening, no inline caches and no assumption about what a register held last time, and it is deliberately the slowest thing the project will ever ship.

The remaining spread between the two machines is the interesting part of what is left. Moving from the Air to the i9 makes CPython 2.1x to 3.2x faster and makes kohebi 1.19x to 1.28x faster on the benchmarks that are nothing but a loop, which is about the clock ratio between the two chips and nothing more. It is not a codegen target: rebuilding on the i9 with `-C target-cpu=native` rather than the generic `x86-64` baseline moves nothing beyond run to run variation. A profile on the i9 puts about a fifth of the time in the register file and about a tenth in cloning and dropping an `Object`, which is the object representation and the dispatch loop rather than any one operator, and both of those are what tier one exists to fix.
