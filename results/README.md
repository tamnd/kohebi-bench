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

The whole tier0 suite on the i9, every runtime in the same run, speed as a multiple of CPython 3.14.4, higher is better. The Air is not in this table because its last run predates half of these benchmarks and the harness marked most of what it did measure as not significant.

| Benchmark | kohebi | pypy | graalpy |
| --- | ---: | ---: | ---: |
| `branch_dispatch` | 0.36x | 4.62x | 0.55x |
| `call` | 0.31x | 2.10x | 0.23x |
| `comprehension` | 0.21x | 0.99x | 0.28x |
| `exceptions` | 0.45x | 1.41x | 0.35x |
| `float_loop` | 0.37x | 3.85x | 0.60x |
| `generators` | 0.33x | 1.51x | 0.36x |
| `int_loop` | 0.36x | 7.57x | 0.93x |
| `iterate` | 0.46x | 4.69x | 0.58x |
| `list_grow` | 0.59x | 2.54x | 0.61x |
| `list_index` | 0.42x | 4.16x | 0.53x |
| `str_ops` | 0.51x | 4.23x | 0.46x |
| **geomean** | **0.38x** | **2.91x** | **0.46x** |

And the other half of the goal, peak memory as a multiple of CPython, lower is better:

| Runtime | Peak memory |
| --- | ---: |
| kohebi | 0.56x |
| pypy | 5.84x |
| graalpy | 20.21x |

Read those two tables together, because separately each of them is an advertisement. kohebi is the leanest of the four including CPython, and it is the slowest of the four. PyPy is the one to beat on speed and is nearly six times CPython's memory to get there. GraalPy is slower than CPython on nine of eleven and carries twenty times its memory. Nobody in this table has both halves, which is the whole reason the project has two columns rather than one.

Against 10x on 0.1x, that leaves 26.1x faster and 5.6x leaner to find. The speed half has not started: this is a tier zero interpreter with no quickening, no inline caches and no assumption about what a register held last time, and it is deliberately the slowest thing the project will ever ship. What it does say is where the floor is, and the floor is uneven. kohebi is already ahead of GraalPy on calls, exceptions and string operations, and behind it by nearly three to one on an integer loop, which is the one thing a JIT compiles first and the one place a tier zero interpreter has nothing to offer.

The two worst numbers are the interesting ones. `comprehension` at 0.21x is the lowest in the table and a comprehension here is lowered to a function and a loop, so it pays a call that CPython does not. `int_loop` at 0.36x against GraalPy's 0.93x is the dispatch loop and the object representation and nothing else. A profile on this machine puts about a fifth of the time in the register file and about a tenth in cloning and dropping an `Object`, which agrees with that reading, and both are what tier one exists to fix. It is not a codegen target: rebuilding with `-C target-cpu=native` rather than the generic `x86-64` baseline moves nothing beyond run to run variation.

`kohebi build` fails on all eleven, because it has no way to run what it produced yet. Until it does, the AOT column is a row of failures rather than a missing column, which is the honest way to show it.
