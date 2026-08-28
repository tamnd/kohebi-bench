"""Small integer arithmetic, the case tagged immediates exist for.

Every intermediate here is a heap-allocated object in CPython. In kohebi they
should be immediates that never touch the allocator, and under AOT sealing they
should become native i64 operations with an overflow check.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _harness import checksum  # noqa: E402


def collatz_length(n):
    steps = 0
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        steps += 1
    return steps


longest = 0
argmax = 0
for start in range(1, 150_000):
    length = collatz_length(start)
    if length > longest:
        longest, argmax = length, start

checksum((argmax, longest))
