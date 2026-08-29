"""Reading and writing a list through a subscript.

Indexing is the most common thing a Python program does to a container after
building it, and it is a different path from growing one: every read bounds
checks, normalizes a negative index and hands back the element, and every write
does the same and then drops whatever was there. A runtime that stores a list
of small integers unboxed pays for the check and nothing else, and one that
stores pointers pays for the check and a refcount on both sides of it.

The slice at the end is here because slicing allocates. `values[i:i + 8]`
builds a new list of eight elements a quarter of a million times, which is a
quarter of a million allocations that a runtime with an escape analysis could
someday not make, and which for now measures how cheaply a small list can be
built and thrown away.
"""

values = []
i = 0
while i < 500_000:
    values += [i]
    i += 1

# Read every element through a subscript, forwards and then backwards, so the
# negative index path is measured rather than assumed to be the same.
total = 0
i = 0
while i < 500_000:
    total += values[i]
    i += 1

i = 1
while i <= 500_000:
    total += values[-i]
    i += 1

# Write every element back, which is the path that also has to release what it
# is overwriting.
i = 0
while i < 500_000:
    values[i] = values[i] + 1
    i += 1

# Small slices, one per iteration, each of them a fresh list.
window = 0
i = 0
while i < 250_000:
    window += values[i : i + 8][0]
    i += 1

print(total, values[0], values[-1], window)
