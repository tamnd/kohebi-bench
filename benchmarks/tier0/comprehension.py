"""Comprehensions, which is how most Python builds a container.

A comprehension is a function in Python 3, not a loop. `[f(x) for x in xs]`
compiles to a `def` taking one argument, and evaluating it is a call, a frame,
a loop inside that frame and a return. So this measures three things at once
and there is no way to separate them, which is the point: it is what a program
that writes a comprehension actually pays.

The four shapes here cost differently. `squares` is the plain one. `evens` adds
a condition, which is a branch per element and a container that ends up smaller
than the input. `scaled` reads a name from the frame around it, which is the
one that turns a local into a shared cell and so is the shape where an
implementation that inlines comprehensions and one that does not diverge
furthest. `pairs` is two clauses, where the inner iterable is built once per
turn of the outer one.

The set and dict versions are here because they are different instructions and
a regression in one would otherwise hide behind the list.

The element expressions are deliberately trivial. This is not a benchmark about
arithmetic, and real work inside them would dilute what it is measuring.

Written without imports, because tier zero has none yet.
"""

source = [i for i in range(200)]

total = 0
i = 0
while i < 2_000:
    squares = [x * x for x in source]
    total += squares[-1]
    i += 1

filtered = 0
i = 0
while i < 2_000:
    evens = [x for x in source if x % 2 == 0]
    filtered += len(evens)
    i += 1


def scaled(xs, n):
    return [x * n for x in xs]


captured = 0
i = 0
while i < 2_000:
    captured += len(scaled(source, i))
    i += 1

nested = 0
i = 0
while i < 200:
    pairs = [(a, b) for a in source for b in (0, 1)]
    nested += len(pairs)
    i += 1

members = 0
i = 0
while i < 2_000:
    seen = {x % 64 for x in source}
    members += len(seen)
    i += 1

entries = 0
i = 0
while i < 2_000:
    table = {x: x * x for x in source}
    entries += len(table)
    i += 1

print(total, filtered, captured, nested, members, entries)
