---
name: retro
description: >-
  Self-improvement pass for a CID-loop project: analyze the iteration journal, learnings, issues,
  and git history for loop-level problems (repeated NEEDS_WORK, drift, oversized steps, recurring
  blockers), then propose harness improvements — and with the "apply" argument, apply at most one
  bounded policy tuning. Use when asked to "run a retro on the loop", "tune the build loop", "why
  does the loop keep failing", or on /long-horizon:retro. NOT for reviewing code (the review role
  does that) or advancing the project (use /long-horizon:build).
user-invocable: true
argument-hint: '[apply — also apply the top bounded improvement; omit to propose only]'
---

Run a **retrospective on the loop itself** — not on the code. The loop's roles review every code
increment; nobody reviews the *harness* unless you do. Your output is diagnosis + proposals; with
`apply`, also one bounded change. If `.cid/journal.md` does not exist or has fewer
than ~5 rows, say there is not enough track record yet and stop.

## Step 1 — Measure

Run `uv run .cid/bin/metrics.py --window 20 --all` for the deterministic journal numbers —
verdict mix and NEEDS_WORK rate, Advances tally, streaks, same-step bounces, phase trajectory
(script or `uv` unavailable → derive them from `journal.md` + `journal-archive.md` by hand). Then
add what the script cannot see, from git history (`git log --oneline`, the `cid(<role>):`
cadence), `learnings.md` + `learnings/`, `issues.md`, and `policy.md`, for the last ~20
iterations:

- **NEEDS_WORK clustering** — do the script's failures cluster on a phase, an area, or a role's
    handoff?
- **Convergence** — is the script's polish share drift (criteria open and reachable) or
    legitimate (hardening in `stable`)?
- **Step sizing** — steps that blew the phase budget or bounced (blocker handoffs)
- **Escalation health** — STOP/IDLE signals: were they real, or should the loop have handled them?
- **Ledger health** — `learnings.md` index and detail files vs. the `review` role's rotation
    budgets (that role is the single source for the numbers); `journal.md` past the archive
    threshold its own header states; stale issues

## Step 2 — Diagnose

Name the top 1–3 loop-level problems with evidence (iteration numbers, journal rows, commit
hashes). Distinguish *harness* problems (bad policy knob, missing learning, vague Verify criteria
in `target.md`) from *project* problems (hard code — not yours to fix). No problems found is a
valid finding — say so and stop; do not invent tuning for its own sake.

## Step 3 — Propose

For each diagnosis, one concrete proposal:

- **Policy tuning** — a specific edit to a *tunable* section of `policy.md` (phase knob, a role
    adjustment for define-next/advance; update-state and review adjustments go to the human as
    proposals)
- **Target sharpening** — a `target.md` Verify criterion that proved vague or unverifiable →
    propose the runnable form (human applies it; the loop never edits `target.md`)
- **Ratchet** — a recurring failure that should become an executable check in the gate
- **Hygiene** — ledger rotation, journal archiving, stale-issue sweep

File each proposal as an `issues.md` entry (`Source: [retro]`, priority `low` for human-directed
ones, `normal` for ones the loop should pick up), and summarize them in your report.

## Step 4 — Apply (only if $ARGUMENTS contains `apply`)

Apply **at most one** proposal per retro, and only within these guardrails:

- Only *tunable* `policy.md` sections — within the phase table, only the `Step budget` and
    `Allowed work` rows — plus the define-next/advance role adjustments and hygiene
    (ledger rotation, journal archiving).
- **Never** the quality gate, the branch model, the `update-state` or `review` role adjustments,
    the rigor rows of the phase table (`Tests required`, `Review depth`, `Debt tolerance`),
    `target.md`, or any source file. The reviewer and the assessor are the loop's quality gate — a
    self-tuning loop that can soften its own reviewer or gates will Goodhart itself (a softened
    reviewer *improves* the NEEDS_WORK metric, so the rollback test would ratify the move instead
    of reverting it), and a softened assessor is the symmetric case (`update-state` computes the
    phase that selects the binding rigor column and judges when a Verify criterion counts as met,
    so biasing it *improves* the Convergence metric the revert test also keys on); those changes
    go to the human as proposals.
- Record the change in `journal.md` as a row:
    `| - | <date> | - | retro: <what changed> | - | - | - |` so the next retro can evaluate it
    against the metrics — and revert it if the NEEDS_WORK rate, the step-bounce rate, or the
    Convergence rate (Step 1) got worse since. Convergence is in the revert test because the
    tunable `Allowed work` row steers what work gets picked: widening it toward easy polish work
    *improves* the NEEDS_WORK rate while Verify criteria stall — only the journal's `Advances`
    column catches that.
- Commit as `cid(retro): <what changed and why>`.

**These guardrails are prose, not mechanism.** Unlike the runner-enforced harnesses this skill
distills (which auto-revert guardrail-breaking meta commits and own the re-evaluation schedule),
nothing here mechanically reverts a bad retro commit, no role checks a `cid(retro):` commit against
*these guardrails* (review's integrity scan pattern-matches gate circumvention in the commits since
the last review — that includes a retro commit, so it can catch a gate-weakening retro edit, but
not an off-limits tuning such as a rigor-row change), and an applied tuning is
re-evaluated only when a human runs the next retro. Granting `apply` means trusting the retro to obey the list above —
review `cid(retro):` commits yourself until that trust is earned.

Without `apply`, touch nothing except the `issues.md` proposal entries (commit them as
`cid(retro): file proposals`).

## Step 5 — Report

Metrics summary → diagnoses with evidence → proposals (and the one applied change, if any) → the
follow-up: when to run the next retro (default: every ~10 iterations, or after a NEEDS_WORK
streak).
