"""Generators, which are the one call that does not return where it was called.

Everything else in this directory calls a function and gets an answer back. A
generator suspends instead: the frame stops where it is, hands a value out, and
the next `next` puts it back on the machine and carries on from the instruction
after the one that stopped. So the thing being measured here is not arithmetic,
it is how much a runtime pays to leave a frame and come back to it, and how
much of that it pays per element rather than per generator.

Three shapes, and they cost differently. A generator stepped a million times is
one frame entered and left a million times, which is the resume path alone. A
million generators stepped once each is the other end: an object built, a frame
bound, one step, and then it is garbage, which is what a comprehension over a
short sequence looks like in real code. A chain is both at once, and it is
where a runtime that allocates anything per step shows it, because the cost is
multiplied by the depth.

CPython pays for a generator with a heap allocated frame object and a linked
list of them. A register machine can keep the whole state in the frame it
already had, which is the bet this implementation makes, and this benchmark is
where that bet is settled.
"""

# One generator, stepped a great many times. The resume path with nothing else
# in it: no allocation per step, no lookup, one add and one suspension.
def counting(n):
    i = 0
    while i < n:
        yield i
        i = i + 1


total = 0
for v in counting(1_000_000):
    total += v

# The same count with `for` inside the generator rather than `while`, so a
# resume has an iterator to step as well as a frame to restore. This is what
# almost every generator anybody writes actually looks like.
def doubling(n):
    for i in range(n):
        yield i + i


doubled = 0
for v in doubling(1_000_000):
    doubled += v

# Many short generators rather than one long one, which moves the cost from the
# resume to the call. Each of these is an object built, arguments bound into a
# frame, three steps and then nothing, and a runtime that builds a heap frame
# per generator pays for it here rather than above.
short = 0
for _ in range(200_000):
    for v in counting(3):
        short += v

# A chain, where every element crosses four frame boundaries on its way out.
# Cost per step is multiplied by the depth, so anything allocated per resume
# shows up four times as loudly as it does in the first loop.
def add_one(over):
    for v in over:
        yield v + 1


chained = 0
for v in add_one(add_one(add_one(counting(200_000)))):
    chained += v

# A generator that suspends inside a `try`, because the open handler is part of
# the state a resume has to put back. A runtime that keeps its handlers on a
# stack belonging to the call rather than to the frame gets the wrong answer
# here, and one that rebuilds them per resume gets the right answer slowly.
def guarded(n):
    i = 0
    while i < n:
        try:
            yield i
        except ValueError:
            pass
        i = i + 1


held = 0
for v in guarded(500_000):
    held += v

# Ending early, which leaves the generator suspended forever rather than
# running it out. Nothing collects it here, and the point is that stopping is
# free: a `break` should not cost more than the steps it skipped.
stopped = 0
for v in counting(1_000_000):
    if v > 1000:
        break
    stopped += v

print(total, doubled, short, chained, held, stopped)
