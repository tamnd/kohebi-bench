"""Attribute access on instances, which is where shapes and inline caches pay off.

CPython stores instance attributes in a per-instance dict. kohebi intends to
store them in typed slots described by a shared shape, so this benchmark is a
direct measurement of that bet.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _harness import checksum  # noqa: E402


class Point:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def norm2(self):
        return self.x * self.x + self.y * self.y + self.z * self.z


points = [Point(i, i + 1, i + 2) for i in range(20_000)]

total = 0
for _ in range(50):
    for p in points:
        total += p.norm2()

checksum(total)
