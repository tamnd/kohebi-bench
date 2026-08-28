"""JSON encode and decode, a realistic and extension-dominated workload.

Interesting precisely because CPython's json module has a C accelerator. A
runtime that has not reimplemented it falls back to the pure-Python path and
loses badly, which is exactly the situation kohebi-std exists to fix.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _harness import checksum  # noqa: E402

record = {
    "id": 0,
    "name": "example",
    "tags": ["a", "b", "c"],
    "nested": {"x": 1.5, "y": [1, 2, 3], "ok": True, "missing": None},
}

documents = []
for i in range(20_000):
    r = dict(record)
    r["id"] = i
    documents.append(r)

encoded = json.dumps(documents)
decoded = json.loads(encoded)

total = sum(d["id"] for d in decoded)
checksum((len(encoded), len(decoded), total))
