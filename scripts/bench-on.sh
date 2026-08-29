#!/usr/bin/env sh
# Run the benchmark suite on a real machine over ssh and bring the results back.
#
# GitHub runners are shared virtual machines. They are useful for noticing that
# a benchmark stopped running and useless for anything smaller than a large
# regression, so the numbers that get published have to come from hardware
# somebody owns. This script is the whole procedure for that: copy the tracked
# files to the host, run the harness there with the host recorded in the
# report, copy the results back into results/<host>/.
#
#   scripts/bench-on.sh gpc run
#   scripts/bench-on.sh server3 run --runs 50
#   scripts/bench-on.sh gpc run benchmarks/micro --runtime cpython
#   scripts/bench-on.sh gpc lex --kohebi ./kohebi
#
# The host is an ssh destination, so anything in ~/.ssh/config works. Nothing
# is installed on the remote side: the harness is standard library only and
# runs straight from PYTHONPATH, so the machine is left as it was found apart
# from one directory under /tmp.
set -eu

host=${1:?usage: scripts/bench-on.sh HOST COMMAND [kohebi-bench args...]}
shift
# `run` when no command is given, since that is what almost every invocation
# wants and spelling it out every time is noise.
if [ "$#" -eq 0 ]; then
    set -- run
fi

remote_dir=${KOHEBI_BENCH_REMOTE_DIR:-/tmp/kohebi-bench}
local_out="results/$host"

repo=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo"

echo "==> sending $(git ls-files | wc -l | tr -d ' ') tracked files to $host:$remote_dir"
ssh "$host" "rm -rf '$remote_dir' && mkdir -p '$remote_dir'"
# COPYFILE_DISABLE because tar on macOS otherwise packs an AppleDouble
# `._name.py` beside every file, which lands on the remote as eight extra
# benchmarks that fail to parse and end up in the report as results.
COPYFILE_DISABLE=1 git ls-files -z | tar --null -T - --no-xattrs -czf - | ssh "$host" "tar -xzf - -C '$remote_dir'"

# python3.14 if the host has it, otherwise whatever python3 is. The version
# used is recorded in the report either way, because comparing a run on 3.12
# against a run on 3.14 and calling the difference a speedup is the exact
# mistake this whole repository exists to prevent.
remote_python=$(ssh "$host" 'command -v python3.14 || command -v python3') || {
    echo "no python3 on $host" >&2
    exit 1
}
echo "==> using $remote_python"

# The harness exits non-zero when the machine was too noisy to publish from.
# That run still produced numbers worth looking at, so the results come back
# either way and the exit status is handed on at the end.
status=0
# ~/.local/bin on PATH because that is where the alternative runtimes get
# symlinked, and a non-interactive ssh command does not read the profile that
# would normally add it. Without this the run silently measures CPython alone
# and reports nothing missing, since a runtime that is not installed is skipped.
#
# `--out` goes last rather than first. It belongs to the subcommand, so putting
# it in front of `run` makes argparse read `run` as its value and refuse the
# line, which is what this script did until it was pointed at a suite for the
# first time and every argument after the command started mattering.
ssh "$host" "cd '$remote_dir' && PATH=\$HOME/.local/bin:\$PATH \
    KOHEBI_BENCH_HOST='$host' PYTHONPATH=src '$remote_python' \
    -m kohebi_bench $* --out '$remote_dir/out'" || status=$?

echo "==> fetching results into $local_out"
mkdir -p "$local_out"
ssh "$host" "tar -czf - -C '$remote_dir/out' ." | tar -xzf - -C "$local_out"

echo
sed -n '1,40p' "$local_out/report.md"
echo "==> full report in $local_out/report.md"
exit "$status"
