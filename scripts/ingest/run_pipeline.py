#!/usr/bin/env python3
"""Run the ingest pipeline: fetch -> normalize -> dedupe.

Stops on the first failing step. Forwards --source / --limit / --dry-run to
fetch_jobs.py; normalize and dedupe take no relevant CLI args.
"""
import argparse
import subprocess
import sys
from pathlib import Path

INGEST_DIR = Path(__file__).parent
PYTHON = sys.executable


def run(script: Path, extra_args: list[str]) -> int:
    print(f"\n=== {script.name} ===", flush=True)
    return subprocess.run([PYTHON, str(script), *extra_args]).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full ingest pipeline")
    parser.add_argument("--source", choices=["linkedin", "greenhouse", "workday", "all"], default="all")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    fetch_args = ["--source", args.source]
    if args.limit is not None:
        fetch_args += ["--limit", str(args.limit)]
    if args.dry_run:
        fetch_args.append("--dry-run")

    steps = [
        (INGEST_DIR / "fetch_jobs.py", fetch_args),
        (INGEST_DIR / "normalize_jobs.py", []),
        (INGEST_DIR / "dedupe_jobs.py", []),
    ]

    for script, extra in steps:
        rc = run(script, extra)
        if rc != 0:
            print(f"\n{script.name} failed (exit {rc}); stopping pipeline.", file=sys.stderr)
            return rc

    print("\nIngest pipeline complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
