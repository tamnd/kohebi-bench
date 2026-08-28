"""The startup floor, and the number most Python programs are dominated by.

Most scripts anyone runs finish before a JIT has warmed up. A runtime that is
10x faster after five seconds of warmup is slower than CPython for the majority
of real invocations, so this benchmark is reported prominently rather than
hidden inside a geomean.
"""

print("started")
