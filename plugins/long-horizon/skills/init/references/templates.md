# CID context pack templates

Templates for the context pack and project-level config files `/long-horizon:init` scaffolds
(the greenfield stack scaffold and `CLAUDE.md` are project-specific and have no template). Replace
`<angle-bracket>` placeholders with project-specific content; keep the structure — the four roles
parse these files by their headings.

## `.cid/README.md`

```markdown
# CID Context Pack (`.cid/`)

Working memory for the **CID loop** (Continuous Iterative Development) — the autonomous agent loop
that advances this project in small, verified increments; its roles own and maintain these files.
Human entry points: `target.md` (the target — human-owned) and `issues.md` (the backlog). Run
`/long-horizon:status` to see where the project stands.
```

## `.cid/target.md`

```markdown
# Target — <project name> v1

> This file is the *fixed target* the CID loop advances toward — the desired end-state plus the bar
> every increment is verified against. It is **human-owned**: the loop verifies against it but
> never edits it. Where this file and a spec/ADR disagree, note it here and decide — the loop will
> flag the conflict, not resolve it.

## Goal (frozen core — no drift without a human)

<2-4 sentences: what this project does when it is done, and for whom. The function served and the
acceptance bar — not the implementation.>

## Stack

<language, key libraries/services, platform constraints — locked decisions the loop must respect>

## Quality bar (the gate — non-negotiable)

The quality gate command in `policy.md` is green for every increment. <Add the project's testing
philosophy: what kinds of tests count as evidence, what fixtures/oracles exist, anything the gate
deliberately does NOT measure and why.> **Never weaken a gate to pass** — fix the root cause.

## PoC exit criteria (what the `poc` phase must prove)

The riskiest assumption: <name it>. The `poc` phase exists to prove it end-to-end, before anything
else gets built.

**Verify:**

- <runnable check 1 — a command/assertion that demonstrates the risky part works end-to-end>
- <runnable check 2>

## Milestones

### M1 — <name>

<1-3 sentences: what exists when this milestone is met.>
**Verify:** <runnable checks, one per line — commands that exit 0 or mechanically checkable
assertions. These are the loop's fitness signal; make each one specific.>

### M2 — <name>

<...>
**Verify:** <...>

## Out of scope for v1

<explicitly deferred work — the loop never picks it up and it never blocks completion>

## Done When

Every v1 milestone meets its **Verify** criteria with the quality gate green and no open
`critical` or `normal` issue in `issues.md`. <Add any human sign-off gates here — e.g. "plus a
human UX sign-off on the final UI" — the loop treats these as human-blocked items, reports IDLE,
and waits.>
```

## `.cid/policy.md`

````markdown
# CID Loop Policy

How the loop operates on this project. Human-owned; `/long-horizon:retro apply` may tune **only**
the sections marked *tunable*, one bounded change per retro, logged in `journal.md`. The retro
skill (`/long-horizon:retro`) is the single binding authority on what it may touch and what goes
to the human as a proposal — do not restate its guardrails here.

## Quality gate

```
<the one command that must be green for every increment, e.g. "mise run check" or
"npm run lint && npm test">
```

## Branch model

- **Loop branch:** `<develop>` — the loop commits here, never to the protected branch.
- **Protected branch:** `<main>` — human-gated; a human merges loop work via a reviewed PR.
- **Push policy:** <"push loop branch on PASS" | "push loop branch every iteration" (required for
    stateless CI drivers — an unpushed iteration dies with the runner; see the build skill's
    `references/automation.md`) | "commit locally, never push">

## Second opinion (optional)

<A command for an independent external reviewer the `review` role runs in the background, e.g.
`codex review --commit HEAD`, or "none". Its findings are triaged by review, never verdict-setting;
if it is unavailable the loop continues without it.>

## Phase policy (tunable)

The loop's rigor follows the project's **phase** (new → poc → mvp → stable), computed each
iteration by the `update-state` role from the exit criteria in `target.md` — the transition rules,
including when a phase may move backward, live in that role, not here. Per-phase knobs:

| Knob                          | new                        | poc                          | mvp                        | stable                        |
| ----------------------------- | -------------------------- | ---------------------------- | -------------------------- | ----------------------------- |
| Step budget (non-test/doc files) | 3                       | 5                            | 3                          | 2                             |
| Tests required                | n/a (specs/scaffold)       | smoke/golden only            | full, per quality bar      | full + regression test per fix |
| Review depth                  | structure & clarity        | assumption validity + gate integrity | full skeptic bar   | full bar + regression focus   |
| Debt tolerance                | n/a                        | file as issues, don't block  | fix in-step or file `normal` | minimal; no new debt        |
| Allowed work                  | scaffold, tooling, gate    | the riskiest-assumption spine | milestone Verify criteria | issues, deps, docs, hardening |

Phase intent, in one line each:

- **new** — shape the work: ratify the target, stand up the repo, make the gate runnable.
- **poc** — prove the riskiest assumption end-to-end; speed of learning outranks polish.
- **mvp** — build the milestones with full rigor; every increment verified and reviewed.
- **stable** — maintain: converge issues to zero, harden, keep gates green forever.

## Role adjustments (tunable)

Project-specific instructions each role reads in addition to its built-in protocol. Keep each
section short; durable pitfalls belong in `learnings.md`, not here.

### update-state

(human-only — the loop never edits this section)

<none yet>

### define-next

<none yet>

### advance

<none yet>

### review

(human-only — the loop never edits this section)

<none yet>
````

**Direct-to-main adaptation.** When the init interview picks the simpler branch model for personal
projects (loop commits directly to `main`, no push), the template's default `## Branch model`
bullets would contradict that choice — scaffold the section (same heading, the roles parse it)
with these bullets instead:

```markdown
- **Loop branch:** `main` — the loop commits directly here; there is no separate protected branch.
- **Protected branch:** none — every protected-branch rule is vacuously satisfied.
- **Push policy:** commit locally, never push
```

and in `.claude/settings.json` replace the protected-branch push deny with `"Bash(git push:*)"` —
with no protected branch, the mechanical backstop is the no-push policy itself.

## `.cid/state.md`

```markdown
<!-- assessed-at: (none) -->

# Project State

## Status: ACTIVE

## Phase: new

Freshly initialized — no iteration has run yet. The first `update-state` run replaces this file
with a verified assessment.
```

## `.cid/next.md`

```markdown
# Next Work Package

## Step: NONE

## Reason

No iteration has run yet — the first `define-next` run replaces this file.
```

## `.cid/handoff.md`

```markdown
## (no iterations yet)

**Verdict:** -
**Loop:** -

**Next:** Run the first CID iteration with /long-horizon:build.
```

## `.cid/learnings.md`

```markdown
# Learnings — Index

Durable, cross-cutting rules are below and **always loaded** by every role. Per-area detail lives
in `.cid/learnings/<name>.md`. When your step touches an area, look it up in the
pointer table and Read that detail file — a fresh-context role has no other memory of it.

`review` appends findings to the detail files and promotes entries into the rules below; the
promotion discipline lives in the `review` role's protocol — the single binding authority — do not
restate it here.

## Rules

<none yet — seeded by review as iterations run. The human may seed known correctness rules here at
init.>

## Detail index

| Area / path | Detail file | Gist |
| ----------- | ----------- | ---- |
```

## `.cid/issues.md`

````markdown
# Issues

Lightweight backlog `define-next` can prioritize. Append entries; `review` deletes resolved ones.

**Format** — one entry per issue:

```
## <short title>
- **Priority:** critical | normal | low
- **Source:** [human] | [review] | [retro]
- **What / where / how to verify:** <the problem, its location, and the check that proves it fixed>
```

**Priority semantics:** `critical` preempts everything; `normal` is weighed against the
state→target gap; **`low` is skipped by the loop** (reserved for human-directed work).

---
````

## `.cid/journal.md`

```markdown
# Iteration Journal

One row per completed iteration, appended by `review`; `/long-horizon:retro apply` also appends
one row per applied tuning, with `-` in the `#` column. Input for `/long-horizon:retro` metrics.
`Advances` names the `target.md` Verify criterion the iteration closed (or `-` for
refactor/polish). Append-only; `review` archives rows past ~200 into `journal-archive.md`.

| # | Date | Phase | Step | Advances | Verdict | Loop |
| - | ---- | ----- | ---- | -------- | ------- | ---- |
```

## `.claude/settings.json` (merge into an existing file — never clobber)

The pack lives at `.cid/` — deliberately not under `.claude/`, whose writes the harness guards as
sensitive for subagents — so an accept-edits permission mode covers all pack writes. A visible
root directory (e.g. `cid/`) would satisfy that permission constraint equally; the hidden name was
chosen to keep loop state out of the project's visible file tree, alongside `.claude/` and `.git/`.
The tradeoff: dotdirs are invisible in default `ls`/file-explorer views and skipped by
hidden-dir defaults in search tools, yet the pack holds the human's steering surface (`target.md`,
`issues.md`) — point people at `/long-horizon:status` rather than expecting them to stumble on the
directory. The allow
rules pre-approve the Bash commands every iteration runs, so driver-run iterations don't stall on
prompts: `Bash(git:*)`, `Bash(gh run list:*)` (the CI check `update-state` runs on projects with
workflows and a remote), and the quality-gate subcommands. **A compound gate command needs one
allow rule per subcommand:** Claude Code splits commands on `&&`, `||`, `;`, `|`, `|&`, `&`, and
newlines, and a rule must match each subcommand independently — for the gate
`npm run lint && npm test` write `Bash(npm run lint:*)` **and** `Bash(npm test:*)`; a single rule
for the whole compound string matches nothing and stalls headless runs on a permission prompt.
If `policy.md` configures a second-opinion command, add an allow rule for it too (e.g.
`Bash(codex review:*)`) — without one, headless runs deny the launch every iteration and the
configured reviewer silently degrades to `Second opinion: unavailable` forever.
The `Bash(uv run .cid/bin:*)` rule covers the pack's bundled helper scripts (`metrics.py`, which
roles run every iteration; `driver.py` runs *outside* Claude and needs no rule — the prefix rule
simply covers everything under `.cid/bin/`).

The deny rules mechanically back the two invariants prose alone cannot guarantee — the loop
editing the human-owned `target.md`, and pushing the protected branch — and deny beats allow, even
under `Bash(git:*)` with acceptEdits. The leading `/` in the file patterns anchors them to the
project root (the settings file's project); a bare `.cid/target.md` pattern resolves against the
session's current directory and silently stops matching when the session runs from a subdirectory. Both are **backstops for the roles' rules and review's
integrity scan, not proofs**: the push deny is prefix-matched, so an exotic spelling
(`git push -u origin main`) can slip past it; and the `target.md` deny binds the built-in
file-editing tools (plus the file commands Claude Code recognizes in Bash, such as `sed`) but not
arbitrary subprocesses — a git-mediated write (e.g. `git checkout <old-commit> -- .cid/target.md`,
pre-approved under `Bash(git:*)`) bypasses it, and review's integrity scan checks commits, not the
working tree. Also: revising `target.md` *through Claude* later requires lifting the deny rule or editing
the file directly — that friction is deliberate (target edits are a human act).

```json
{
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "Bash(gh run list:*)",
      "Bash(uv run .cid/bin:*)",
      "Bash(<gate subcommand 1>:*)",
      "Bash(<gate subcommand 2 \u2014 one rule per subcommand of a compound gate>:*)",
      "Bash(<second-opinion command \u2014 omit this rule if policy.md says none>:*)"
    ],
    "deny": [
      "Edit(/.cid/target.md)",
      "Write(/.cid/target.md)",
      "Bash(git push origin <protected branch>:*)"
    ]
  }
}
```

## `.claude/loop.md` (project root `.claude/`, not inside the pack)

```markdown
Run the /long-horizon:build skill to advance this project by exactly one CID-loop iteration. Print
the report block (`Verdict:` / `Loop:`) at the end.

- If `Loop: IDLE`, say so, name the blockers, and remind the human to stop the `/loop` schedule
    (`Esc`) — it keeps firing full iterations against an idle project until they do.
- If `Loop: STOP`, summarize the `HUMAN REVIEW REQUESTED` reason and hand back.
- Otherwise (`CONTINUE`, including `NEEDS_WORK`) continue: the next iteration retries.

Do not start new work outside the CID loop.
```
