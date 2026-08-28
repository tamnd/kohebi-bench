"""Tests for the lexer comparison.

None of these need kohebi to be installed. The kohebi side is a subprocess that
prints `<tokens> <path>` lines, so a small Python script that prints the same
thing stands in for it, and one that prints the wrong thing stands in for a
lexer that has regressed. What is being tested here is the harness, not the
lexer, and the harness has to be right about a disagreement before the number
it produces means anything.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from kohebi_bench import lex
from kohebi_bench.__main__ import main
from kohebi_bench.runtimes import Runtime

HERE = Path(__file__).resolve().parent


@pytest.fixture
def corpus_dir(tmp_path: Path) -> Path:
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "a.py").write_text("x = 1\n")
    (root / "b.py").write_text("def f():\n    return 2\n")
    return root


def stub(tmp_path: Path, name: str, body: str) -> Runtime:
    """A runtime that is a Python script, so these tests run anywhere."""
    script = tmp_path / f"{name}.py"
    script.write_text(body)
    return Runtime(
        name,
        (sys.executable, str(script)),
        version_argv=(sys.executable, "--version"),
    )


#: Prints the same lines the real thing does.
HONEST = """
import sys
paths = [l.strip() for l in open(sys.argv[1]) if l.strip()]
for p in paths:
    print(len(open(p).read().split()), p)
"""

#: Off by one on every file, the way a lexer that lost a token would be.
WRONG = """
import sys
paths = [l.strip() for l in open(sys.argv[1]) if l.strip()]
for p in paths:
    print(len(open(p).read().split()) - 1, p)
"""


class TestBuild:
    def test_collects_every_python_file(self, corpus_dir: Path):
        corpus = lex.build(corpus_dir)
        assert len(corpus.files) == 2
        assert corpus.total_lines == 3
        assert corpus.total_bytes == sum(p.stat().st_size for p in corpus.files)

    def test_limit_stops_early(self, corpus_dir: Path):
        assert len(lex.build(corpus_dir, limit=1).files) == 1

    def test_a_file_cpython_cannot_tokenize_is_recorded_not_dropped_silently(
        self, corpus_dir: Path
    ):
        (corpus_dir / "bad.py").write_text("def f(:\n    (((\n")
        corpus = lex.build(corpus_dir)
        assert [p.name for p in corpus.files] == ["a.py", "b.py"]
        assert len(corpus.skipped) == 1
        path, reason = corpus.skipped[0]
        assert path.name == "bad.py"
        assert reason, "a skipped file without a reason is how a corpus rots"

    def test_a_file_that_is_not_utf8_is_recorded(self, corpus_dir: Path):
        (corpus_dir / "latin.py").write_bytes(b"# \xe9\nx = 1\n")
        corpus = lex.build(corpus_dir)
        assert [p.name for p in corpus.files] == ["a.py", "b.py"]
        assert "not UTF-8" in corpus.skipped[0][1]

    def test_a_byte_order_mark_is_not_part_of_the_program(self, corpus_dir: Path):
        # Decoded as plain utf-8 the mark stays in the string and CPython's
        # tokenizer calls it an identifier, which is not what happens to the
        # file when Python runs it.
        (corpus_dir / "bom.py").write_bytes(b"\xef\xbb\xbfx = 1\n")
        corpus = lex.build(corpus_dir)
        assert len(corpus.files) == 3

    def test_without_takes_files_out_and_corrects_the_totals(self, corpus_dir: Path):
        corpus = lex.build(corpus_dir)
        smaller = corpus.without([(corpus_dir / "b.py", "made up")])
        assert [p.name for p in smaller.files] == ["a.py"]
        assert smaller.total_lines == 1
        assert smaller.total_bytes == (corpus_dir / "a.py").stat().st_size
        assert smaller.skipped[-1][1] == "made up"

    def test_the_list_file_holds_one_path_per_line(self, corpus_dir: Path, tmp_path: Path):
        corpus = lex.build(corpus_dir)
        listing = corpus.write(tmp_path / "list.txt")
        assert listing.read_text().splitlines() == [str(p) for p in corpus.files]


class TestVerify:
    def test_two_sides_that_agree_report_the_token_total(self, corpus_dir: Path, tmp_path: Path):
        listing = lex.build(corpus_dir).write(tmp_path / "list.txt")
        one = stub(tmp_path, "one", HONEST)
        two = stub(tmp_path, "two", HONEST)
        agreement = lex.verify([one, two], listing)
        assert agreement.agreed
        assert agreement.tokens > 0

    def test_a_disagreement_is_reported_with_both_answers(self, corpus_dir: Path, tmp_path: Path):
        listing = lex.build(corpus_dir).write(tmp_path / "list.txt")
        agreement = lex.verify(
            [stub(tmp_path, "one", HONEST), stub(tmp_path, "two", WRONG)],
            listing,
        )
        assert not agreement.agreed
        assert "one" in agreement.detail
        assert "two" in agreement.detail

    def test_a_side_that_fails_is_reported_rather_than_raised(
        self, corpus_dir: Path, tmp_path: Path
    ):
        listing = lex.build(corpus_dir).write(tmp_path / "list.txt")
        broken = stub(tmp_path, "broken", "import sys\nsys.exit('deliberate')\n")
        agreement = lex.verify([stub(tmp_path, "ok", HONEST), broken], listing)
        assert not agreement.agreed
        assert "deliberate" in agreement.detail


class TestRefusals:
    def test_a_corpus_everything_reads_drops_nothing(self, corpus_dir: Path, tmp_path: Path):
        corpus = lex.build(corpus_dir)
        assert lex.refusals(stub(tmp_path, "ok", HONEST), corpus, tmp_path) == []

    def test_the_refused_file_comes_out_and_the_rest_is_kept(
        self, corpus_dir: Path, tmp_path: Path
    ):
        # Stands in for `€ = 2`, which CPython's tokenize accepts as a name and
        # the compiler rejects. kohebi follows the compiler.
        refuser = stub(
            tmp_path,
            "refuser",
            """
import sys
paths = [l.strip() for l in open(sys.argv[1]) if l.strip()]
for p in paths:
    if p.endswith("b.py"):
        print(f'  File "{p}", line 1', file=sys.stderr)
        print("SyntaxError: made up", file=sys.stderr)
        raise SystemExit(1)
    print(1, p)
""",
        )
        dropped = lex.refusals(refuser, lex.build(corpus_dir), tmp_path)
        assert [p.name for p, _ in dropped] == ["b.py"]
        assert dropped[0][1] == "SyntaxError: made up"

    def test_refusing_everything_is_a_regression_and_stops_the_run(
        self, corpus_dir: Path, tmp_path: Path
    ):
        for i in range(4):
            (corpus_dir / f"f{i}.py").write_text("x = 1\n")
        always = stub(
            tmp_path,
            "always",
            """
import sys
p = [l.strip() for l in open(sys.argv[1]) if l.strip()][0]
print(f'  File "{p}", line 1', file=sys.stderr)
print("SyntaxError: made up", file=sys.stderr)
raise SystemExit(1)
""",
        )
        with pytest.raises(RuntimeError, match="regression"):
            lex.refusals(always, lex.build(corpus_dir), tmp_path, tolerate=2)

    def test_a_failure_that_names_no_file_is_not_guessed_at(self, corpus_dir: Path, tmp_path: Path):
        mute = stub(tmp_path, "mute", "raise SystemExit(1)\n")
        with pytest.raises(RuntimeError, match="without naming a file"):
            lex.refusals(mute, lex.build(corpus_dir), tmp_path)


class TestCPythonSide:
    """The script that stands for CPython in the comparison."""

    def test_it_counts_the_same_tokens_the_tokenize_module_yields(
        self, corpus_dir: Path, tmp_path: Path
    ):
        listing = lex.build(corpus_dir).write(tmp_path / "list.txt")
        proc = subprocess.run(
            [sys.executable, str(lex.SCRIPT), str(listing)],
            capture_output=True,
            text=True,
            check=True,
        )
        counts = {
            line.split(" ", 1)[1]: int(line.split(" ", 1)[0])
            for line in proc.stdout.splitlines()
            if line
        }
        assert counts[str(corpus_dir / "a.py")] == 5  # NAME OP NUMBER NEWLINE ENDMARKER

    def test_a_file_it_cannot_tokenize_stops_it_and_names_the_file(self, tmp_path: Path):
        bad = tmp_path / "bad.py"
        bad.write_text("def f(:\n   (((\n")
        listing = tmp_path / "list.txt"
        listing.write_text(f"{bad}\n")
        proc = subprocess.run(
            [sys.executable, str(lex.SCRIPT), str(listing)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 1
        assert str(bad) in proc.stderr


class TestCommandLine:
    def test_lex_says_how_to_get_a_kohebi_when_there_is_none(self, capsys):
        assert main(["lex", "--kohebi", "/nonexistent/kohebi-xyz"]) == 2
        assert "cargo build --release" in capsys.readouterr().err

    def test_run_still_needs_a_directory(self, capsys):
        with pytest.raises(SystemExit):
            main(["run", "/nonexistent/benchmarks-xyz"])

    def test_a_command_is_required(self):
        with pytest.raises(SystemExit):
            main([])
