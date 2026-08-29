"""Floating point in a loop, and the boxing that comes with it.

Every intermediate float in CPython is a heap object. In kohebi a float is a
word inside the value and never touches the allocator, so this is the clearest
statement of what unboxing is worth before any of the later machinery exists.

The result is printed as a float rather than rounded, because there is no
`round` builtin yet, and because printing it also checks that all three
runtimes agree on the shortest representation that round-trips.
"""

total = 0.0
drift = 1.0
i = 0
while i < 1_500_000:
    total += (i * 0.5 - 1.25) / 3.0
    if total > 1e12:
        total = total / 2.0
        drift = drift + 0.5
    i += 1

print(total, drift, total > 0.0)
