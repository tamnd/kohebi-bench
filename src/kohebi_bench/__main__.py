"""`kohebi-bench` command line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .report import Report, describe_environment
from .runtimes import ALL, DEFAULT_COMPARISON, collect, measure


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kohebi-bench",
        description="Benchmark kohebi against CPython, PyPy, and GraalPy.",
        epilog="A number without a method is marketing. This tool records the method.",
    )
    parser.add_argument("suite", type=Path, nargs="?", default=Path("benchmarks"))
    parser.add_argument(
        "--runtime",
        action="append",
        metavar="NAME",
        choices=sorted(ALL),
        help="Runtime to measure. Repeatable. Defaults to every known runtime.",
    )
    parser.add_argument("--baseline", default="cpython", choices=sorted(ALL))
    parser.add_argument(
        "--runs",
        type=int,
        default=30,
        metavar="N",
        help="Timed runs per benchmark (default: 30). Fewer than 10 is not publishable.",
    )
    parser.add_argument("--warmup", type=int, default=3, metavar="N")
    parser.add_argument("--timeout", type=float, default=600.0, metavar="SECONDS")
    parser.add_argument("--out", type=Path, default=None, metavar="DIR")
    parser.add_argument(
        "--allow-noisy",
        action="store_true",
        help="Do not fail when the machine is too noisy to draw conclusions from.",
    )
    args = parser.parse_args(argv)

    if not args.suite.is_dir():
        parser.error(f"{args.suite} is not a directory")

    chosen = [ALL[n] for n in args.runtime] if args.runtime else list(DEFAULT_COMPARISON)
    baseline = ALL[args.baseline]
    if baseline not in chosen:
        chosen.insert(0, baseline)

    available = [r for r in chosen if r.available()]
    missing = [r.name for r in chosen if not r.available()]
    if baseline not in available:
        print(f"baseline {baseline.name} is not installed", file=sys.stderr)
        return 2
    if missing:
        print(f"not installed, skipping: {', '.join(missing)}", file=sys.stderr)

    benchmarks = collect(args.suite)
    if not benchmarks:
        print(f"no benchmarks under {args.suite}", file=sys.stderr)
        return 1

    if args.runs < 10:
        print(
            f"warning: {args.runs} runs is below the 10 needed for a publishable "
            "confidence interval",
            file=sys.stderr,
        )

    for r in available:
        print(f"{r.name}: {r.version()}", file=sys.stderr)

    measurements = []
    for bench in benchmarks:
        for runtime in available:
            print(f"  {bench.stem} under {runtime.name} ... ", end="", flush=True, file=sys.stderr)
            m = measure(
                runtime,
                bench,
                runs=args.runs,
                warmup=args.warmup,
                timeout_s=args.timeout,
                env={"PYTHON_JIT": "1"} if runtime.name == "cpython-jit" else None,
            )
            measurements.append(m)
            if m.failed:
                print("FAILED", file=sys.stderr)
            else:
                print(
                    f"{m.wall.median * 1000:.1f} ms "
                    f"(+/- {m.wall.iqr * 1000:.1f}), "
                    f"{m.peak_rss_bytes / 1024 / 1024:.0f} MiB",
                    file=sys.stderr,
                )

    report = Report(
        baseline=baseline.name,
        measurements=measurements,
        environment=describe_environment(available),
    )
    print(report.to_markdown())
    if args.out:
        report.write(args.out)
        print(f"wrote {args.out}/results.json", file=sys.stderr)

    noisy = [m for m in measurements if not m.failed and not m.wall.stable]
    if noisy and not args.allow_noisy:
        print(
            f"{len(noisy)} measurement(s) too noisy to publish; "
            "re-run on a quiet machine or pass --allow-noisy",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
