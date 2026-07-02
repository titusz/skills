#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Deterministic analytics over the CID iteration journal.

Parses the markdown table in .cid/journal.md (plus .cid/journal-archive.md with
--all) and prints the loop's fitness signals — verdict mix, convergence from the
Advances column, verdict streaks, same-step bounces, and phase trajectory — so
CID roles consume one small digest instead of re-deriving arithmetic from raw
table rows. Read-only. Exits 0 even when the journal is missing (with a note)
so callers need no error handling.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

EXPECTED_CELLS = 7  # | # | Date | Phase | Step | Advances | Verdict | Loop |
PASSING = ("PASS", "PASS_WITH_NOTES")


def split_row(line: str) -> list[str] | None:
    """Return the cell values of a markdown table row, or None for non-rows.

    Splits only on unescaped pipes so cells may carry `\\|` (e.g. a Verify
    criterion containing a shell pipeline), and unescapes them.
    """
    stripped = line.strip()
    if len(stripped) < 2 or not (stripped.startswith("|") and stripped.endswith("|")):
        return None
    cells = re.split(r"(?<!\\)\|", stripped[1:-1])
    return [cell.strip().replace("\\|", "|") for cell in cells]


def is_separator(cells: list[str]) -> bool:
    """True for markdown header-separator rows like | - | ---- | :-: |."""
    return all(cell and set(cell) <= set("-: ") for cell in cells)


def parse_rows(text: str) -> tuple[list[dict], int]:
    """Parse journal markdown into row dicts, counting rows that fit no known shape."""
    rows: list[dict] = []
    malformed = 0
    for line in text.splitlines():
        cells = split_row(line)
        if cells is None:
            continue
        if is_separator(cells) or cells[0] == "#":
            continue
        if len(cells) != EXPECTED_CELLS or not (cells[0] == "-" or cells[0].isdigit()):
            malformed += 1
            continue
        number, date, phase, step, advances, verdict, loop = cells
        rows.append(
            {
                "n": None if number == "-" else int(number),
                "date": date,
                "phase": phase,
                "step": step,
                "advances": advances,
                "verdict": verdict.upper(),
                "loop": loop.upper(),
                "retro": number == "-",
            }
        )
    return rows, malformed


def tail_run(values: list) -> int:
    """Length of the run of identical values at the end of the list."""
    run = 0
    for value in reversed(values):
        if not values or value != values[-1]:
            break
        run += 1
    return run


def find_bounces(window: list[dict]) -> list[dict]:
    """Steps reviewed more than once in the window with at least one failure."""
    by_step: dict[str, list[str]] = {}
    for row in window:
        by_step.setdefault(row["step"], []).append(row["verdict"])
    return [
        {"step": step, "count": len(verdicts), "failures": failures}
        for step, verdicts in by_step.items()
        if len(verdicts) >= 2
        and (failures := sum(1 for v in verdicts if v not in PASSING)) >= 1
    ]


def phase_trajectory(window: list[dict]) -> list[dict]:
    """Ordered phase changes inside the window, keyed by iteration number."""
    trajectory: list[dict] = []
    for row in window:
        if not trajectory or trajectory[-1]["phase"] != row["phase"]:
            trajectory.append({"phase": row["phase"], "since": row["n"]})
    return trajectory


def compute(rows: list[dict], malformed: int, window_size: int) -> dict:
    """Aggregate the journal rows into the digest the CID roles consume."""
    iterations = [r for r in rows if not r["retro"]]
    window = iterations[-window_size:] if window_size else iterations
    verdicts = Counter(r["verdict"] for r in window)
    needs_work = verdicts.get("NEEDS_WORK", 0)
    closed = [r["advances"] for r in window if r["advances"] not in ("-", "")]
    steps = [r["step"] for r in window]
    return {
        "total_iterations": len(iterations),
        "retro_rows": sum(1 for r in rows if r["retro"]),
        "window": len(window),
        "verdicts": dict(verdicts),
        "needs_work_rate": round(needs_work / len(window), 2) if window else 0.0,
        "verdict_streak": {
            "verdict": window[-1]["verdict"] if window else None,
            "length": tail_run([r["verdict"] for r in window]),
        },
        "advances_closed": closed,
        "polish_iterations": len(window) - len(closed),
        "step_streak": {
            "step": window[-1]["step"] if window else None,
            "length": tail_run(steps),
            "verdicts": [r["verdict"] for r in window[-tail_run(steps) :]]
            if window
            else [],
        },
        "bounces": find_bounces(window),
        "phases": phase_trajectory(window),
        "last_row": window[-1] if window else None,
        "malformed_rows": malformed,
    }


def render(metrics: dict, source: str) -> str:
    """Format the digest as the compact text block roles read."""
    lines = [
        f"CID journal metrics — window: last {metrics['window']} of "
        f"{metrics['total_iterations']} iterations ({source})"
    ]
    verdicts = ", ".join(f"{k} {v}" for k, v in sorted(metrics["verdicts"].items()))
    lines.append(
        f"Verdicts: {verdicts or '(none)'}"
        f"  (NEEDS_WORK rate {int(metrics['needs_work_rate'] * 100)}%)"
    )
    streak = metrics["verdict_streak"]
    if streak["verdict"]:
        lines.append(f"Streak:   {streak['length']} consecutive {streak['verdict']}")
    lines.append(
        f"Advances: {len(metrics['advances_closed'])} closed Verify criteria, "
        f"{metrics['polish_iterations']} refactor/polish"
    )
    for criterion in metrics["advances_closed"]:
        lines.append(f"  closed: {criterion}")
    step = metrics["step_streak"]
    if step["step"] and step["length"] >= 2:
        lines.append(
            f'Step tail: "{step["step"]}" in the last {step["length"]} iterations '
            f"({', '.join(step['verdicts'])})"
        )
    for bounce in metrics["bounces"]:
        lines.append(
            f'Bounce:   "{bounce["step"]}" reviewed {bounce["count"]}x, '
            f"{bounce['failures']} failed"
        )
    if not metrics["bounces"]:
        lines.append("Bounce:   (none)")
    phases = " -> ".join(
        f"{p['phase']} (since #{p['since']})" for p in metrics["phases"]
    )
    lines.append(f"Phases:   {phases or '(none)'}")
    if metrics["retro_rows"]:
        lines.append(f"Retro rows: {metrics['retro_rows']} (excluded from metrics)")
    if metrics["malformed_rows"]:
        lines.append(
            f"WARNING: {metrics['malformed_rows']} malformed table row(s) skipped — "
            "check .cid/journal.md by hand"
        )
    return "\n".join(lines)


def main() -> int:
    """Parse arguments, read the journal, and print the digest."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", default=".cid", help="CID pack directory")
    parser.add_argument(
        "--window", type=int, default=10, help="iterations to analyze (0 = all)"
    )
    parser.add_argument(
        "--all", action="store_true", help="include journal-archive.md rows"
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args()

    pack = Path(args.dir)
    journal = pack / "journal.md"
    if not journal.is_file():
        print(f"No journal at {journal} — no iterations recorded yet.")
        return 0

    sources = [journal]
    archive = pack / "journal-archive.md"
    if args.all and archive.is_file():
        sources.insert(0, archive)  # archive rows are older; keep chronological order

    rows: list[dict] = []
    malformed = 0
    for source in sources:
        parsed, bad = parse_rows(source.read_text(encoding="utf-8"))
        rows.extend(parsed)
        malformed += bad

    metrics = compute(rows, malformed, args.window)
    label = " + ".join(s.name for s in sources)
    print(json.dumps(metrics, indent=2) if args.json else render(metrics, label))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
