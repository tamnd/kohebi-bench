"""Shared helpers for benchmarks.

Benchmarks time the whole process, startup included, because that is what a
user experiences. A benchmark that excludes startup is measuring the steady
state of a JIT and calling it the speed of the runtime.
"""

import sys


def checksum(value):
    """Print a result so the work cannot be optimised away.

    An AOT compiler with whole-program visibility is entirely capable of
    deleting a benchmark that produces nothing. Every benchmark ends by
    printing something derived from all of its work.
    """
    print(value)
    sys.stdout.flush()
