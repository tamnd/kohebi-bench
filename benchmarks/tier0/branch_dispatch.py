"""Comparison and branching, which is where a register machine should show.

Every arm here is a comparison followed by a conditional jump. CPython pushes
the result of the comparison and then pops it again to branch on it; kohebi
compares into a register and branches on that register, and the difference
between those two is exactly what this program measures.

The buckets are separate names rather than a list because tier zero has no
subscripting yet.
"""

zero = 0
one = 0
two = 0
three = 0
rest = 0

i = 0
while i < 1_000_000:
    r = i % 7
    if r == 0:
        zero += 1
    elif r == 1:
        one += 1
    elif r == 2:
        two += 1
    elif r == 3:
        three += 1
    elif r < 6 and i % 2 == 0:
        rest += 2
    else:
        rest += 1
    i += 1

print(zero, one, two, three, rest)
