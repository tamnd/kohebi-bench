"""Exception handling, which most Python programs pay for without raising.

Two costs live here and they are worth measuring apart, because a runtime can
be good at one and bad at the other and the average hides it.

The first is the `try` that never fires. Almost every `try` in a real program
is one of these: a guard around code that usually works. CPython made this free
in 3.11 by moving the handler table out of the executed code, so `guarded`
below should cost the same as the bare loop, and a runtime that pushes and pops
something per iteration will show up here and nowhere else.

The second is the exception that is actually raised, which real Python uses as
control flow rather than only for errors. `table[k]` inside a `try` is how a
great deal of code asks whether a key is there, so `lookup` is that pattern at
a 50% miss rate rather than a synthetic raise. `caught` and `bound` are the
synthetic ones, and they differ only by the `as`, which is a store and a delete
per catch and is therefore the price of naming the exception you caught.

`unwound` raises three frames below the handler. That is the shape where an
implementation that unwinds frame by frame and one that searches a table
diverge, and it is also the common shape in application code, where the `try`
is at the top of a request and the raise is deep inside it.

`cleaned` is `finally` with no exception in sight, which is what every `with`
statement compiles into once there are any, so it is worth knowing now.

Written without imports or attribute access, because tier zero has neither.
"""

# A `try` that never raises, which is what nearly every `try` in a program is.
guarded = 0
i = 0
while i < 500_000:
    try:
        guarded += i
    except ValueError:
        guarded = 0
    i += 1

# The same loop without the `try`, so the two can be subtracted. If a runtime
# has zero cost exceptions these are the same number.
plain = 0
i = 0
while i < 500_000:
    plain += i
    i += 1

# Raising and catching, which is the cost of the exception itself.
caught = 0
i = 0
while i < 100_000:
    try:
        raise ValueError(i)
    except ValueError:
        caught += 1
    i += 1

# The same, but naming what was caught, which is a store and a delete more.
bound = 0
i = 0
while i < 100_000:
    try:
        raise KeyError(i)
    except KeyError as e:
        bound += 1
    i += 1

# Asking a dict for a key by trying it, which is how a lot of Python asks.
table = {x: x * 2 for x in range(64)}
lookup = 0
i = 0
while i < 100_000:
    try:
        lookup += table[i % 128]
    except KeyError:
        lookup += 1
    i += 1


def raising(n):
    raise ValueError(n)


def middle(n):
    return raising(n)


def outer(n):
    return middle(n)


# Caught three frames above where it was raised.
unwound = 0
i = 0
while i < 50_000:
    try:
        outer(i)
    except ValueError:
        unwound += 1
    i += 1

# `finally` with nothing to clean up after, which is what a `with` becomes.
cleaned = 0
i = 0
while i < 200_000:
    try:
        cleaned += 1
    finally:
        cleaned += 1
    i += 1

print(guarded, plain, caught, bound, lookup, unwound, cleaned)
