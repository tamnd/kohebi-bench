"""Integer arithmetic in a loop, with no function call anywhere in it.

Collatz, written out inline rather than as a function, because tier zero has
no calls yet. What is left is the part of the interpreter that will still be
on the critical path when everything else is built: fetch an instruction,
read two registers, do the arithmetic, write one register, branch.

The same program is in `micro/int_arithmetic.py` in the shape a person would
actually write it. When kohebi can run that one, this one has done its job and
can go.
"""

longest = 0
argmax = 0
start = 1
while start < 30_000:
    n = start
    steps = 0
    while n != 1:
        if n % 2 == 0:
            n = n // 2
        else:
            n = 3 * n + 1
        steps += 1
    if steps > longest:
        longest = steps
        argmax = start
    start += 1

print(argmax, longest)
