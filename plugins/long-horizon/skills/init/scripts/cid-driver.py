#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Reference driver for unattended CID-loop building.

Re-invokes `claude -p "/long-horizon:build"` from the project root until the
printed report block says `Loop: IDLE` (exit 0) or `Loop: STOP` (exit 2),
bounded by --max-iterations. Exit 6 means the budget ran out while
`Loop: CONTINUE` — normal progress, re-run to continue (the expected exit under
one-iteration-per-tick scheduling). Abnormal endings needing human triage:
unparseable iteration output (exit 3), per-iteration timeout (exit 4),
environment or process failure including a non-zero claude exit (exit 5).
Each iteration's full output is written to .cid/logs/ (self-gitignored) so any
trajectory can be replayed and diagnosed.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

EXIT_IDLE = 0
EXIT_STOP = 2
EXIT_UNPARSEABLE = 3
EXIT_TIMEOUT = 4
EXIT_ENVIRONMENT = 5
EXIT_BUDGET = 6

LOOP_RE = re.compile(r"\bloop\b\s*:\**\s*(continue|idle|stop)\b", re.IGNORECASE)
VERDICT_RE = re.compile(
    r"\bverdict\b\s*:\**\s*(pass_with_notes|needs_work|skipped|pass)\b", re.IGNORECASE
)


def resolve_command(spec: str) -> list[str]:
    """Split a command spec and resolve its executable, handling Windows shims."""
    argv = shlex.split(spec, posix=(os.name != "nt"))
    executable = shutil.which(argv[0])
    if executable is None:
        raise FileNotFoundError(f"command not found: {argv[0]}")
    argv[0] = executable
    if os.name == "nt" and Path(executable).suffix.lower() in (".cmd", ".bat"):
        argv = ["cmd", "/c", *argv]
    return argv


def last_match(pattern: re.Pattern, text: str) -> str | None:
    """Uppercased last capture of the pattern in the text, or None."""
    matches = pattern.findall(text)
    return matches[-1].upper() if matches else None


def run_iteration(argv: list[str], timeout: int) -> tuple[int | None, str, str, float]:
    """Run one claude invocation; exit code None signals a timeout."""
    start = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return (
            proc.returncode,
            proc.stdout or "",
            proc.stderr or "",
            time.monotonic() - start,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return None, stdout, stderr, time.monotonic() - start


def write_log(
    logs: Path,
    n: int,
    argv: list[str],
    code: int | None,
    stdout: str,
    stderr: str,
    duration: float,
) -> Path:
    """Persist one iteration's full output; keep the log directory untracked."""
    logs.mkdir(parents=True, exist_ok=True)
    gitignore = logs / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n", encoding="utf-8")
    path = logs / f"iter-{n:04d}-{time.strftime('%Y%m%d-%H%M%S')}.log"
    header = (
        f"command: {subprocess.list2cmdline(argv)}\n"
        f"exit: {'timeout' if code is None else code}  duration: {duration:.0f}s\n"
    )
    path.write_text(
        f"{header}--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}\n",
        encoding="utf-8",
    )
    return path


def main() -> int:
    """Drive CID iterations until the loop parks itself or a bound trips."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--max-iterations", type=int, default=20)
    parser.add_argument("--interval", type=int, default=0, help="seconds between runs")
    parser.add_argument("--timeout", type=int, default=3600, help="seconds per run")
    parser.add_argument("--permission-mode", default="acceptEdits")
    parser.add_argument("--prompt", default="/long-horizon:build")
    parser.add_argument(
        "--claude", default="claude", help="claude command (may carry flags)"
    )
    parser.add_argument("--logs", default=".cid/logs", help="iteration log directory")
    args = parser.parse_args()

    if not Path(".cid/target.md").is_file():
        print(
            "No .cid/target.md here — run from the project root of an initialized project."
        )
        return EXIT_ENVIRONMENT
    try:
        argv = [
            *resolve_command(args.claude),
            "-p",
            args.prompt,
            "--permission-mode",
            args.permission_mode,
        ]
    except FileNotFoundError as exc:
        print(exc)
        return EXIT_ENVIRONMENT

    logs = Path(args.logs)
    for n in range(1, args.max_iterations + 1):
        code, stdout, stderr, duration = run_iteration(argv, args.timeout)
        log = write_log(logs, n, argv, code, stdout, stderr, duration)
        loop = last_match(LOOP_RE, stdout)
        verdict = last_match(VERDICT_RE, stdout) or "-"
        print(
            f"[{n}/{args.max_iterations}] {duration:.0f}s  "
            f"Verdict: {verdict}  Loop: {loop or '?'}  log: {log}"
        )
        if code is None:
            print(f"Iteration timed out after {args.timeout}s — see {log}.")
            return EXIT_TIMEOUT
        if code != 0:
            print(f"claude exited {code} — not trusting the report block; see {log}.")
            return EXIT_ENVIRONMENT
        if loop == "IDLE":
            print(
                "Loop parked: IDLE — no autonomous work remains. Triage the blockers."
            )
            return EXIT_IDLE
        if loop == "STOP":
            print(
                "Loop parked: STOP — HUMAN REVIEW REQUESTED. See the log for the reason."
            )
            return EXIT_STOP
        if loop is None:
            print(f"No Loop: line in the output (claude exit {code}) — see {log}.")
            return EXIT_UNPARSEABLE
        if n < args.max_iterations and args.interval:
            time.sleep(args.interval)

    print(f"Iteration budget ({args.max_iterations}) exhausted while Loop: CONTINUE.")
    return EXIT_BUDGET


if __name__ == "__main__":
    sys.exit(main())
