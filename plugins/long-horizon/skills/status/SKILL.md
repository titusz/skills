---
name: status
description: >-
  Report where a CID-loop project stands without advancing it: current phase, convergence toward
  the target, last verdicts, open issues, blockers, and the suggested next action. Read-only. Use
  when asked "where does the project stand", "show loop status", "how is the build loop doing", or
  on /long-horizon:status. NOT for running an iteration (use /long-horizon:build) or setting up a
  project (use /long-horizon:init).
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash(git log:*), Bash(uv run .cid/bin:*), Bash(echo:*)
---

Report the state of this project's CID loop. **Read-only** — do not modify any file, commit, or
spawn roles. If `.cid/target.md` does not exist, say the project is not initialized
and point to `/long-horizon:init`; report nothing else.

## Live snapshot (expanded when this skill is invoked)

- Journal metrics: !`uv run .cid/bin/metrics.py 2>&1 || echo "(metrics script unavailable)"`
- Recent commits: !`git log --oneline -10 2>&1 || echo "(no git history)"`

## Gather

1. `.cid/state.md` — status, phase, convergence, blockers (note the `assessed-at`
    hash and whether HEAD has moved since — if so, label the snapshot stale)
2. `.cid/handoff.md` — last verdict and loop signal
3. The journal metrics from the snapshot above — verdict mix, streaks, phase trajectory (if the
    snapshot line shows an error instead, read the last ~10 rows of `.cid/journal.md` directly)
4. `.cid/issues.md` — counts per priority; list `critical` titles
5. `.cid/next.md` — the pending step, if any
6. The commit cadence from the snapshot above (re-run `git log --oneline -10` only if it failed)

## Report

Keep it to one screen, in this order:

1. **Headline** — phase, status (ACTIVE/IDLE), and the one-line answer to "how is it going" (e.g.
    "mvp, converging: 3 of 12 Verify criteria open, last 5 iterations all PASS").
2. **Convergence** — remaining Verify criteria per milestone; flag drift if the state notes a
    polish streak.
3. **Recent iterations** — last ~5 journal rows (verdict + step title).
4. **Issues** — counts by priority; every `critical` by name.
5. **Blockers** — human-blocked items from `state.md`, verbatim.
6. **Next** — the pending `next.md` step or the handoff's `**Next:**` suggestion, and the suggested
    action: run `/long-horizon:build`, resolve a STOP, sign off a blocker, or run
    `/long-horizon:retro` if the journal shows a rough patch (repeated NEEDS_WORK, drift).

If the snapshot is stale (HEAD moved since `assessed-at`), say so — the numbers describe the last
assessment, and the next `/long-horizon:build` will refresh them.
