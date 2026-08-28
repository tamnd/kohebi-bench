"""A large homogeneous list, which is the 10x memory claim in one file.

CPython stores this as an array of pointers to boxed integers, roughly 36 bytes
per element. Storage strategies should make it a native array of i64, or of i32
where the range is provable.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _harness import checksum  # noqa: E402

values = list(range(3_000_000))

total = 0
for _ in range(5):
    total += sum(values)

evens = [v for v in values if v % 2 == 0]
checksum((total, len(evens), evens[-1]))
