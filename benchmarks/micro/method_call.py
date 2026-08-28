"""Polymorphic method dispatch through a class hierarchy.

Deliberately hostile to monomorphic inline caches: the loop sees three receiver
types in rotation, so a runtime that speculates on a single shape has to
deoptimise or widen to a polymorphic cache.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _harness import checksum  # noqa: E402


class Shape:
    def area(self):
        raise NotImplementedError


class Square(Shape):
    def __init__(self, s):
        self.s = s

    def area(self):
        return self.s * self.s


class Rect(Shape):
    def __init__(self, w, h):
        self.w = w
        self.h = h

    def area(self):
        return self.w * self.h


class Tri(Shape):
    def __init__(self, b, h):
        self.b = b
        self.h = h

    def area(self):
        return self.b * self.h // 2


shapes = []
for i in range(30_000):
    shapes.append(Square(i % 50))
    shapes.append(Rect(i % 30, i % 70))
    shapes.append(Tri(i % 40, i % 60))

total = 0
for _ in range(10):
    for s in shapes:
        total += s.area()

checksum(total)
