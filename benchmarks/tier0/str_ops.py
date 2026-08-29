"""Substring search, comparison and concatenation on text that is not English.

Included partly to keep the string representation decision honest. A runtime
that stores ASCII one way and everything else another should not be able to
look good here while being slow on the half of the world's text that has
accents or is not Latin at all.

There are no method calls yet, so this is the subset of string work that is
spelled with operators: `in`, the comparisons, and `+`.
"""

needle = "café"
haystack = "the quick brown fox café jumps over the lazy dog 日本語"
missing = "🐍🐍"

hits = 0
tail = ""
i = 0
while i < 400_000:
    if needle in haystack:
        hits += 1
    if missing not in haystack:
        hits += 1
    if haystack < "z":
        hits += 1
    tail = "x" + needle + "日本語"
    if tail != needle:
        hits += 1
    i += 1

print(hits, tail)
