"""Calling a function, which is the operation everything else is built on.

A call is a frame, an argument list bound to parameters, a body, and a return
value handed back. Methods, comprehensions, generators and every dunder in the
object model are that same sequence with something wrapped around it, so
whatever a call costs is a floor under all of them.

The three shapes here are the three that cost differently. `add` is the cheap
one: two positional arguments straight into two registers, nothing to search.
`described` is what a keyword argument costs, which is a name matched against
the parameter list before anything can be bound. `sum_of` is a call whose
arguments have to be collected into a tuple first. Splitting them apart means a
regression in one does not hide behind the other two.

The bodies are deliberately trivial. This is not a benchmark about arithmetic
and any real work inside them would only dilute what it is measuring.

Written without imports, because tier zero has none yet.
"""


def add(a, b):
    return a + b


def described(value, scale=1, offset=0):
    return value * scale + offset


def sum_of(*values):
    total = 0
    for value in values:
        total += value
    return total


plain = 0
i = 0
while i < 400_000:
    plain = add(plain, 1)
    i += 1

keyword = 0
i = 0
while i < 200_000:
    keyword = described(keyword, offset=1)
    i += 1

collected = 0
i = 0
while i < 100_000:
    collected += sum_of(1, 2, 3)
    i += 1

print(plain, keyword, collected)
