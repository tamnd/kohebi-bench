"""Growing a list, and then walking it to find things.

`items += [i]` is a roundabout way to write `items.append(i)`, and it is the
only way available while there are no method calls. It builds a one element
list and merges it, so both sides do a little more work than they would
otherwise, and they do the same little more.

The tail is a linear scan, which is what `in` on a list is in every runtime.
It is here because list storage is one of the bets in kohebi's design: a list
of small integers should not be a list of pointers to boxed integers, and a
scan over one is where that shows up.
"""

items = []
i = 0
while i < 1_000_000:
    items += [i]
    i += 1

found = 0
probe = 0
while probe < 4:
    if probe * 250_000 in items:
        found += 1
    if -1 in items:
        found += 100
    probe += 1

print(found, items != [])
