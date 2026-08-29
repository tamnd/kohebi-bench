"""`kohebi-bench` command line entry point.

Two commands. `run` measures whole programs under whole runtimes, which is the
comparison the project is ultimately judged on. `lex` measures one piece of the
frontend against CPython's `tokenize` module, which is what there is to measure
while the runtime is still being built.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from . import lex as lexmod
from .report import Report, describe_environment
from .runtimes import ALL, DEFAULT_COMPARISON, Measurement, at, collect, measure


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kohebi-bench",
        description="Benchmark kohebi against CPython, PyPy, and GraalPy.",
        epilog="A number without a method is marketing. This tool records the method.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="Measure the benchmark suite under every runtime.")
    run.add_argument("suite", type=Path, nargs="?", default=Path("benchmarks"))
    run.add_argument(
        "--runtime",
        action="append",
        metavar="NAME",
        choices=sorted(ALL),
        help="Runtime to measure. Repeatable. Defaults to every known runtime.",
    )
    run.add_argument("--baseline", default="cpython", choices=sorted(ALL))
    run.add_argument(
        "--kohebi",
        default="kohebi",
        metavar="PATH",
        help=(
            "The kohebi binary to measure (default: whichever is on PATH). "
            "Usually target/release/kohebi in a checkout of tamnd/kohebi."
        ),
    )
    _add_common(run, runs=30, timeout=600.0)

    lex = commands.add_parser(
        "lex",
        help="Measure the kohebi lexer against CPython's tokenize module.",
        description=(
            "Tokenize a corpus of Python with both, check that they counted the same "
            "tokens, then time them. Defaults to this interpreter's own standard library."
        ),
    )
    lex.add_argument(
        "--corpus",
        type=Path,
        default=None,
        metavar="DIR",
        help="Directory of Python files (default: this interpreter's standard library).",
    )
    lex.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Use only the first N files. For a smoke test, not for a published number.",
    )
    lex.add_argument(
        "--kohebi",
        default="kohebi",
        metavar="PATH",
        help="The kohebi binary to measure (default: whichever is on PATH).",
    )
    # Ten runs rather than thirty. One run tokenizes the whole standard
    # library, so this is already thousands of files of work per sample and the
    # variance between samples is small.
    _add_common(lex, runs=10, timeout=900.0)

    args = parser.parse_args(argv)
    if args.command == "lex":
        return _lex(args)
    return _run(args, parser)


def _add_common(parser: argparse.ArgumentParser, *, runs: int, timeout: float) -> None:
    parser.add_argument(
        "--runs",
        type=int,
        default=runs,
        metavar="N",
        help=f"Timed runs per benchmark (default: {runs}). Fewer than 10 is not publishable.",
    )
    parser.add_argument("--warmup", type=int, default=3, metavar="N")
    parser.add_argument("--timeout", type=float, default=timeout, metavar="SECONDS")
    parser.add_argument("--out", type=Path, default=None, metavar="DIR")
    parser.add_argument(
        "--allow-noisy",
        action="store_true",
        help="Do not fail when the machine is too noisy to draw conclusions from.",
    )


def _run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.suite.is_dir():
        parser.error(f"{args.suite} is not a directory")

    chosen = [ALL[n] for n in args.runtime] if args.runtime else list(DEFAULT_COMPARISON)
    chosen = [at(r, args.kohebi) for r in chosen]
    baseline = at(ALL[args.baseline], args.kohebi)
    if baseline not in chosen:
        chosen.insert(0, baseline)

    available = [r for r in chosen if r.available()]
    missing = [r.name for r in chosen if not r.available()]
    if baseline not in available:
        print(f"baseline {baseline.name} is not installed", file=sys.stderr)
        return 2
    if missing:
        print(f"not installed, skipping: {', '.join(missing)}", file=sys.stderr)

    # Before anything is timed, because a report built from the wrong binary is
    # worse than no report: every number in it is right except the one that
    # matters, so it survives being read carefully.
    wrong = [complaint for r in available if (complaint := r.misidentified())]
    if wrong:
        for complaint in wrong:
            print(f"error: {complaint}", file=sys.stderr)
        print("fix PATH, or pass the binary explicitly, and run again", file=sys.stderr)
        return 2

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
            _report_one(m)

    notes = [
        f"Suite: `{args.suite}`, {len(benchmarks)} benchmark(s), "
        f"{args.runs} timed runs each after {args.warmup} warmup run(s).",
    ]
    if missing:
        notes.append(
            f"Not installed on this machine, so absent from every table: {', '.join(missing)}."
        )
    notes.append(
        "Each benchmark is a whole process, startup included, because that is what a "
        "user experiences."
    )

    report = Report(
        baseline=baseline.name,
        measurements=measurements,
        environment=describe_environment(available),
        notes=notes,
    )
    return _finish(report, measurements, args)


def _lex(args: argparse.Namespace) -> int:
    kohebi = lexmod.kohebi_lex(args.kohebi)
    if not kohebi.available():
        print(
            f"{args.kohebi} is not on PATH. Build it with `cargo build --release` in a "
            "checkout of tamnd/kohebi and pass --kohebi target/release/kohebi.",
            file=sys.stderr,
        )
        return 2

    root = args.corpus or lexmod.stdlib_root()
    if not root.is_dir():
        print(f"{root} is not a directory", file=sys.stderr)
        return 2

    print(f"reading {root} ... ", end="", flush=True, file=sys.stderr)
    corpus = lexmod.build(root, limit=args.limit)
    print(
        f"{len(corpus.files)} files, {corpus.total_bytes / 1024 / 1024:.1f} MiB, "
        f"{corpus.total_lines} lines, {len(corpus.skipped)} skipped",
        file=sys.stderr,
    )
    if not corpus.files:
        print(f"no Python files under {root}", file=sys.stderr)
        return 1

    runtimes = [lexmod.CPYTHON_TOKENIZE, kohebi]
    for r in runtimes:
        print(f"{r.name}: {r.version()}", file=sys.stderr)

    with tempfile.TemporaryDirectory(prefix="kohebi-bench-lex-") as tmp:
        # Files CPython tokenizes and kohebi refuses. There is at least one in
        # every standard library and it is deliberate, so it comes out of the
        # corpus rather than out of the comparison.
        try:
            refused = lexmod.refusals(kohebi, corpus, Path(tmp), timeout_s=args.timeout)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            print(exc, file=sys.stderr)
            return 1
        for path, reason in refused:
            print(f"  left out {path}: {reason}", file=sys.stderr)
        corpus = corpus.without(refused)

        # The list file is named for the corpus because the harness takes the
        # benchmark name from the file it is given.
        listing = corpus.write(Path(tmp) / "lex-stdlib.txt")

        print("checking both sides count the same tokens ... ", end="", flush=True, file=sys.stderr)
        agreement = lexmod.verify(runtimes, listing, timeout_s=args.timeout)
        if not agreement.agreed:
            print("no", file=sys.stderr)
            print(agreement.detail, file=sys.stderr)
            # No timing follows. A speed number from an implementation that
            # produced the wrong answer is worse than no number at all.
            return 1
        print(f"yes, {agreement.tokens} tokens each", file=sys.stderr)

        # What each side costs before it has read a single file. Both numbers
        # are inside the timings below, since both sides are whole processes,
        # and an interpreter that starts slowly should not be able to hide it.
        # Reporting the floor is what lets a reader take it back out.
        empty = Path(tmp) / "empty.txt"
        empty.write_text("")
        floors = {}
        for runtime in runtimes:
            m = measure(runtime, empty, runs=5, warmup=1, timeout_s=args.timeout)
            floors[runtime.name] = 0.0 if m.failed else m.wall.median

        measurements = []
        for runtime in runtimes:
            print(f"  {runtime.name} ... ", end="", flush=True, file=sys.stderr)
            m = measure(
                runtime,
                listing,
                runs=args.runs,
                warmup=args.warmup,
                timeout_s=args.timeout,
            )
            measurements.append(m)
            _report_one(m)

    notes = [
        f"Corpus: {root}, {len(corpus.files)} files, "
        f"{corpus.total_bytes / 1024 / 1024:.1f} MiB, {corpus.total_lines} lines.",
        f"Both sides produced {agreement.tokens} tokens, file for file, before being timed.",
        f"{len(corpus.skipped)} file(s) left out: not UTF-8, or one of the two sides "
        "will not tokenize them.",
    ]
    notes.append(
        "Memory is not the same shape of work on the two sides. CPython's tokenize "
        "yields one token at a time, while kohebi builds the whole stream for a file "
        "and hands it over, which is what the parser above it will want. Read the "
        "peak memory column with that in mind."
    )
    for m in measurements:
        if m.failed:
            continue
        floor = floors.get(m.runtime, 0.0)
        notes.append(
            f"{m.runtime}: {lexmod.throughput(corpus, m.wall.median)}, "
            f"of which {floor * 1000:.0f} ms was starting the process. "
            f"Without that, {lexmod.throughput(corpus, max(m.wall.median - floor, 1e-9))}."
        )

    report = Report(
        baseline=lexmod.CPYTHON_TOKENIZE.name,
        measurements=measurements,
        environment=describe_environment(runtimes),
        notes=notes,
    )
    return _finish(report, measurements, args)


def _report_one(m: Measurement) -> None:
    """One line per measurement, on stderr, so a long run shows progress."""
    if m.failed:
        print("FAILED", file=sys.stderr)
        return
    print(
        f"{m.wall.median * 1000:.1f} ms "
        f"(+/- {m.wall.iqr * 1000:.1f}), "
        f"{m.peak_rss_bytes / 1024 / 1024:.0f} MiB",
        file=sys.stderr,
    )


def _finish(report: Report, measurements: list[Measurement], args: argparse.Namespace) -> int:
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
