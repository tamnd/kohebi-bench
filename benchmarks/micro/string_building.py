"""String construction and comparison across scripts.

Included partly to keep the UTF-8 representation decision honest. A runtime
optimised for ASCII should not look good here while being slow on text that is
not English.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _harness import checksum  # noqa: E402

words = ["alpha", "beta", "gamma", "café", "日本語", "\U0001f40d"]

parts = []
for i in range(200_000):
    parts.append(words[i % len(words)])

joined = "-".join(parts)
upper = joined.upper()
counts = {w: joined.count(w) for w in words}

checksum((len(joined), len(upper), sorted(counts.items())))
