"""Tokenize a corpus with CPython's `tokenize` module and count what came out.

This is run as a program rather than imported: `python _lex_cpython.py LIST`,
where LIST holds one path per line. It prints `<tokens> <path>` for each file,
which is byte for byte what `kohebi tokenize --format count` prints, so the two
can be compared as text as well as timed against each other.

The reading is deliberately the same shape on both sides. Bytes in, decoded as
UTF-8, tokenized with positions, counted. `tokenize.open` would be the friendly
way to do it, and it also sniffs an encoding declaration, which kohebi does not
do yet. Measuring one implementation doing more work than the other and calling
the difference a speedup is the thing this repository exists to prevent.

The decode is `utf-8-sig` rather than `utf-8` because a byte order mark is part
of the encoding and not part of the program. Decoding a file that has one with
plain `utf-8` leaves it in the string, where `generate_tokens` reports it as an
identifier, which is not what happens to that file when Python runs it.

Nothing here imports `kohebi_bench`. It has to run under whatever interpreter
is being measured, from a path, with no package installed.
"""

from __future__ import annotations

import io
import sys
import tokenize


def count(text: str) -> int:
    n = 0
    for _ in tokenize.generate_tokens(io.StringIO(text).readline):
        n += 1
    return n


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        sys.stderr.write("usage: _lex_cpython.py LIST\n")
        return 2

    with open(argv[0], encoding="utf-8") as handle:
        paths = [line.strip() for line in handle if line.strip()]

    out: list[str] = []
    for path in paths:
        with open(path, "rb") as handle:
            raw = handle.read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            sys.stdout.write("".join(out))
            sys.stderr.write(f"cannot read {path}: {exc}\n")
            return 1
        try:
            n = count(text)
        except (SyntaxError, tokenize.TokenError, IndentationError) as exc:
            # The first failure stops the run, the same way kohebi stops, so a
            # corpus that one side can lex and the other cannot is loud rather
            # than a quiet difference in how much work each side did.
            sys.stdout.write("".join(out))
            sys.stderr.write(f"{path}: {exc}\n")
            return 1
        out.append(f"{n} {path}\n")

    sys.stdout.write("".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
