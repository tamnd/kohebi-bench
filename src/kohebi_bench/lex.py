"""Lexer throughput, kohebi against CPython's `tokenize` module.

The runtime cannot execute a program yet, so the benchmark suite has nothing to
run under it. The lexer does exist, and it is the first piece of the frontend,
so this is where the performance trend line starts. A frontend that is slower
than CPython's is a bottleneck that gets harder to find the more that is built
on top of it, and the point of measuring now is to never be surprised later.

Two things happen here, and the order matters. First both sides tokenize the
corpus once and their output is compared: they print the same `<tokens> <path>`
lines, so a disagreement in token counts stops the run before any timing is
done. A speed number from an implementation that produced the wrong answer is
worse than no number. Only then is either side timed.

The corpus is CPython's own standard library by default, which is around 1900
files and a few tens of megabytes of real Python written by many hands over
thirty years. It is on every machine that can run this, so nothing has to be
downloaded or vendored, and it is the same corpus `tamnd/kohebi-compat` checks
agreement against.
"""

from __future__ import annotations

import io
import re
import subprocess
import sys
import sysconfig
import tokenize
from dataclasses import dataclass
from pathlib import Path

from .runtimes import Runtime

#: The CPython side, run from a path so it works under any interpreter.
SCRIPT = Path(__file__).resolve().with_name("_lex_cpython.py")

CPYTHON_TOKENIZE = Runtime(
    "cpython-tokenize",
    (sys.executable, str(SCRIPT)),
    "the tokenize module, generate_tokens",
    version_argv=(sys.executable, "--version"),
)


def kohebi_lex(binary: str = "kohebi") -> Runtime:
    """The kohebi side, optionally from a path to a build you just made."""
    return Runtime(
        "kohebi-lex",
        (binary, "tokenize", "--format", "count", "--files-from"),
        "the lexer, with line and column positions",
        version_argv=(binary, "--version"),
    )


@dataclass(frozen=True, slots=True)
class Corpus:
    """The files both sides will read, and what had to be left out."""

    files: tuple[Path, ...]
    skipped: tuple[tuple[Path, str], ...]
    total_bytes: int
    total_lines: int

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(f"{f}\n" for f in self.files), encoding="utf-8")
        return path

    def without(self, dropped: list[tuple[Path, str]]) -> Corpus:
        """The same corpus with some files taken out, and the totals corrected.

        Only the dropped files are read again, so this costs nothing next to
        building the corpus in the first place.
        """
        gone = {path for path, _ in dropped}
        lost_bytes = 0
        lost_lines = 0
        for path in gone:
            raw = path.read_bytes()
            text = raw.decode("utf-8-sig", errors="replace")
            lost_bytes += len(raw)
            lost_lines += text.count("\n") + (0 if text.endswith("\n") or not text else 1)
        return Corpus(
            tuple(f for f in self.files if f not in gone),
            self.skipped + tuple(dropped),
            self.total_bytes - lost_bytes,
            self.total_lines - lost_lines,
        )


def stdlib_root() -> Path:
    """Where this interpreter keeps its standard library."""
    return Path(sysconfig.get_paths()["stdlib"])


def build(root: Path, limit: int | None = None) -> Corpus:
    """Every file under `root` that both sides can be expected to read.

    A file is left out for one of two reasons, and both are recorded rather
    than swallowed. It is not UTF-8, which kohebi does not read yet because
    encoding declarations are a separate job. Or CPython's own tokenizer
    refuses it, which happens in a standard library because it ships deliberate
    syntax errors as test data.

    Leaving those in would make the comparison meaningless: the two sides would
    stop at different files and be timed on different amounts of work.
    """
    files: list[Path] = []
    skipped: list[tuple[Path, str]] = []
    total_bytes = 0
    total_lines = 0

    for path in sorted(root.rglob("*.py")):
        if limit is not None and len(files) >= limit:
            break
        try:
            raw = path.read_bytes()
        except OSError as exc:
            skipped.append((path, str(exc)))
            continue
        try:
            # utf-8-sig, because a byte order mark belongs to the encoding
            # rather than to the program, and both sides drop it.
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            skipped.append((path, f"not UTF-8: {exc}"))
            continue
        try:
            for _ in tokenize.generate_tokens(io.StringIO(text).readline):
                pass
        except (SyntaxError, tokenize.TokenError, IndentationError) as exc:
            skipped.append((path, f"CPython will not tokenize it: {exc}"))
            continue
        files.append(path)
        total_bytes += len(raw)
        total_lines += text.count("\n") + (0 if text.endswith("\n") or not text else 1)

    return Corpus(tuple(files), tuple(skipped), total_bytes, total_lines)


#: `File "some/path.py", line 12`, the first line of a CPython-shaped report.
_FILE_LINE = re.compile(r'^\s*File "(?P<path>.+)", line \d+')
#: `kohebi: cannot read some/path.py: ...`
_CANNOT_READ = re.compile(r"^kohebi: cannot read (?P<path>.+?): ")


def refusals(
    runtime: Runtime,
    corpus: Corpus,
    work_dir: Path,
    *,
    timeout_s: float = 900.0,
    tolerate: int = 25,
) -> list[tuple[Path, str]]:
    """Files in `corpus` that `runtime` will not lex, found by trying.

    CPython accepting a file does not mean we do, and the two disagree in at
    least one place on purpose: `tokenize` reports `€ = 2` as a NAME while the
    compiler rejects the character, and we follow the compiler because that is
    what a user sees. The standard library ships that exact file as test data.

    Rather than hard-coding a list, the corpus is run and whatever gets refused
    comes out, one run per refusal. That converges in a couple of seconds for a
    handful of files and stops after `tolerate` of them, because at that point
    this is not a known corner any more, it is a regression, and quietly
    shrinking the corpus until the benchmark passes would hide it.

    `tamnd/kohebi-compat` is where agreement is decided. This only exists so
    that both sides are timed on the same work.
    """
    dropped: list[tuple[Path, str]] = []
    listing = work_dir / "candidates.txt"
    current = corpus
    for _ in range(tolerate + 1):
        current.write(listing)
        proc = subprocess.run(
            [*runtime.argv, str(listing)],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        if proc.returncode == 0:
            return dropped
        path, reason = _blamed(proc.stderr)
        if path is None:
            raise RuntimeError(
                f"{runtime.name} failed on the corpus without naming a file:\n{proc.stderr}"
            )
        dropped.append((path, reason))
        current = current.without([(path, reason)])
    raise RuntimeError(
        f"{runtime.name} refused more than {tolerate} files that CPython tokenizes. "
        "That is a regression rather than a known corner, so no timing was done."
    )


def _blamed(stderr: str) -> tuple[Path | None, str]:
    """The file a failed run stopped on, and why, from its error output."""
    reason = ""
    path = None
    for line in stderr.splitlines():
        match = _FILE_LINE.match(line) or _CANNOT_READ.match(line)
        if match:
            path = Path(match.group("path"))
        if line and not line.startswith(" "):
            reason = line.strip()
    if not reason:
        lines = [line.strip() for line in stderr.splitlines() if line.strip()]
        reason = lines[-1] if lines else "unknown"
    return path, reason


@dataclass(frozen=True, slots=True)
class Agreement:
    """Whether the two sides counted the same tokens in the same files."""

    agreed: bool
    detail: str = ""
    tokens: int = 0


def verify(runtimes: list[Runtime], corpus_list: Path, timeout_s: float = 900.0) -> Agreement:
    """Run each side once and compare what they printed, line for line.

    This is not a substitute for `tamnd/kohebi-compat`, which compares token by
    token including positions and text. It is the cheap check that the thing
    about to be timed is doing the same job, and it costs one run.
    """
    outputs: dict[str, list[str]] = {}
    for runtime in runtimes:
        argv = [*runtime.argv, str(corpus_list)]
        try:
            proc = subprocess.run(
                argv, capture_output=True, text=True, timeout=timeout_s, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return Agreement(False, f"{runtime.name} could not be run: {exc}")
        if proc.returncode != 0:
            first = (proc.stderr or "").strip().splitlines()
            why = first[0] if first else f"exit status {proc.returncode}"
            return Agreement(False, f"{runtime.name} failed: {why}")
        outputs[runtime.name] = proc.stdout.splitlines()

    names = list(outputs)
    first_name = names[0]
    expected = outputs[first_name]
    for name in names[1:]:
        got = outputs[name]
        if len(got) != len(expected):
            return Agreement(
                False,
                f"{first_name} reported {len(expected)} files and {name} reported {len(got)}",
            )
        for want, have in zip(expected, got, strict=True):
            if want != have:
                return Agreement(
                    False,
                    f"disagreement on token count: {first_name} said {want!r}, "
                    f"{name} said {have!r}",
                )

    tokens = sum(int(line.split(" ", 1)[0]) for line in expected)
    return Agreement(True, tokens=tokens)


def throughput(corpus: Corpus, seconds: float) -> str:
    """Megabytes and lines per second, which travel better than a speedup."""
    if seconds <= 0:
        return "unknown"
    mib = corpus.total_bytes / 1024 / 1024 / seconds
    lines = corpus.total_lines / seconds
    return f"{mib:.1f} MiB/s, {lines / 1_000_000:.2f}M lines/s"
