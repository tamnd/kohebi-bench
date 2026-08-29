"""Walking containers with `for`, which is how Python loops are actually written.

Every other program in this directory counts with `while`, because that is all
tier zero could run when they were written. This one is the same work said the
way a person says it, and the two are not the same work for a runtime. A `while`
loop is a comparison and a branch. A `for` loop asks a container for an iterator,
steps it, and asks whether the step found anything, and how much that costs
depends entirely on whether the iterator was built once or is being rebuilt.

`range` is first because it is the loop nearly every Python program is made of,
and because it is the one iterator that has nothing to walk: a runtime that
allocates the numbers is doing work no program asked for, and one that computes
the nth value from n pays a multiply and a division on every step.

The rest walk real containers. The dict and the set are here because their
iterators cannot hold a Rust iterator or a C pointer safely across a step, so
they hold a position instead, and a position into a table with holes in it is
where an off by one silently skips an element rather than crashing.
"""

# Counting, which is the loop most programs are made of.
total = 0
for i in range(2_000_000):
    total += i

# Counting downwards and by more than one, because the direction and the stride
# are separate arms in anything that resolves a range.
back = 0
for i in range(2_000_000, 0, -3):
    back += i

# A list of half a million elements, walked. This is the path that has to hold
# the list rather than copy it: copying would be faster to write and would make
# a list mutated during the walk invisible, which is not what Python does.
values = []
for i in range(500_000):
    values += [i]

walked = 0
for v in values:
    walked += v

# A tuple, which cannot change and so is walked from an immutable slice.
fixed = (1, 2, 3, 4, 5, 6, 7, 8)
tuples = 0
for _ in range(200_000):
    for v in fixed:
        tuples += v

# A string, whose nth code point is only reachable by counting from the front.
# A runtime that steps it that way is quadratic here rather than linear, which
# is the kind of thing that looks fine on a short string in a test.
text = "the quick brown fox jumps over the lazy dog" * 200
points = 0
for _ in range(20):
    for c in text:
        points += len(c)

# A dict and a set, whose iterators hold a position in a table rather than a
# pointer into one.
pairs = {}
for i in range(100_000):
    pairs[i] = i + 1

keys = 0
for _ in range(5):
    for k in pairs:
        keys += k

# Starting from a one element set rather than from `set()`, because there is no
# empty set literal and kohebi has no `set` builtin yet. A type needs classes.
members = {0}
for i in range(1, 100_000):
    members |= {i}

seen = 0
for _ in range(5):
    for m in members:
        seen += m

print(total, back, walked, tuples, points, keys, seen, len(values), len(pairs), len(members))
