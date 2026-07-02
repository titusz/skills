---
name: init
description: >-
  Set up a project for Continuous Iterative Development (CID): interview the user about the goal,
  stack, quality gate, and milestones; draft a target.md with runnable Verify criteria; and
  scaffold the CID context pack at .cid/ so the /long-horizon:build loop can run.
  Invoked explicitly via /long-horizon:init — model invocation is disabled below, because setting
  up the loop (interview, settings.json permission rules) is a deliberate human act. Works on empty
  directories (greenfield) and existing codebases (brownfield). NOT for running iterations (use
  /long-horizon:build) or checking progress (use /long-horizon:status).
user-invocable: true
disable-model-invocation: true
argument-hint: '[one-line project goal, or empty to be interviewed]'
---

Set up this project for the CID loop. The output is a **CID context pack** at
`.cid/` — the committed working memory that lets four fresh-context roles advance
the project autonomously. The single most load-bearing artifact is `target.md`: the loop can only
be as good as the target's **Verify criteria**, because they are its fitness signal. Spend your
effort there.

All file templates are in `references/templates.md` — read it before scaffolding.

## Step 1 — Detect the situation

- `.cid/target.md` already exists → this project is already initialized. Say so,
    show `/long-horizon:status`, and offer to *revise* the target instead of re-scaffolding. Never
    overwrite an existing pack without explicit confirmation. Note the scaffolded
    `.claude/settings.json` denies Claude edits to `.cid/target.md` (deliberate — target edits are
    a human act): to revise, draft the change for the human to apply, or ask them to lift the deny
    rule for the edit and restore it after.
- The directory has source code → **brownfield**: explore it first (structure, language, existing
    tests/gates/CI, docs) so the interview and the drafted target build on reality. Run
    `git status --short` and note any uncommitted work — it is the user's, and must stay out of the
    init commit (Step 4).
- Otherwise → **greenfield**.

## Step 2 — Interview

**$ARGUMENTS** may carry a one-line goal; use it to seed the interview. Ask what you cannot infer,
using `AskUserQuestion` for the discrete choices — in batches, not one long form. Cover:

1. **Goal** — what the project does when it is done, for whom. This becomes the frozen core of
    `target.md`: it never drifts without the human.
2. **Riskiest assumption** — the one thing most likely to sink the project (an algorithm works, an
    API is usable, a latency bound holds). This seeds the **PoC exit criteria**: the `poc` phase
    exists to prove exactly this, end-to-end, before anything else gets built.
3. **Stack** — language, key libraries/services, platform constraints. Brownfield: confirm what you
    detected rather than asking cold.
4. **Quality gate** — the one command that must be green for every increment (build + lint + test).
    Brownfield: use the existing gate. Greenfield: propose a stack-appropriate command and scaffold
    whatever it needs (task runner config, a first trivial test) so it can run green from iteration
    one. A gate that cannot run yet is the first thing the `new` phase fixes.
5. **Milestones** — draft 3–7 v1 milestones *yourself* from the goal, each with a **Verify** block,
    and present them for correction. Do not ask the user to write milestones from scratch.
6. **Branch model** — recommend: loop works on `develop`, pushes on PASS, human merges to `main`
    via a gated PR. Simpler alternative for personal projects: loop commits directly to `main`, no
    push. Let the user pick.
7. **Second opinion (optional)** — a command for an independent external reviewer the `review`
    role launches each iteration (e.g. `codex review --commit HEAD`). Default to `none` if the
    user has no external reviewer — the loop runs fine without one.

## Step 3 — Draft target.md and get sign-off

Write the draft `target.md` (template in `references/templates.md`) and show it to the user. Every
Verify criterion must be **runnable** — a command that exits 0 or an assertion checkable
mechanically. Push back on vague criteria ("works well", "is fast"): convert each to a measurable
form or move it to a human sign-off note. Extract every verifiable constraint latent in the goal —
whatever judgment residue remains should be small and explicitly routed to the human.

Iterate until the user approves. The target is human-owned from here on: the loop verifies against
it but never edits it.

Alongside the target, present the **phase policy table** (from the `policy.md` template) for
explicit ratification — in particular the `Tests required` row: the `new`/`poc` cells deliberately
relax testing to smoke/golden level, which may override stricter standing norms in the project's
or the user's own instructions. That relaxation applies only because the user approves it here,
per project — adjust any row the user objects to before scaffolding.

## Step 4 — Scaffold

Create, from the templates:

1. `.cid/README.md` — a one-paragraph orientation note
2. `.cid/target.md` — the approved target
3. `.cid/policy.md` — gate command, branch model, push policy, second-opinion
    command (set it to `none` unless the user names an external reviewer), phase policy table,
    empty role-adjustment sections
4. `.cid/state.md`, `next.md`, `handoff.md`, `learnings.md`, `issues.md`,
    `journal.md` — initial stubs
5. `.cid/bin/` — copy `scripts/cid-metrics.py` → `.cid/bin/metrics.py` and
    `scripts/cid-driver.py` → `.cid/bin/driver.py` from this skill's directory (paths relative to
    this SKILL.md). Committed with the pack so the roles — and a CI runner, which sees only the
    checkout — can run them: `metrics.py` is the journal-analytics digest the roles read each
    iteration; `driver.py` is the unattended reference driver (the build skill's
    `references/automation.md` documents it). Requires `uv` on PATH — if the user does not have it,
    say so; the roles fall back to reading the journal directly.
6. `.claude/loop.md` — points a bare `/loop` at `/long-horizon:build` (tell the user this changes
    what a bare `/loop` does in this project)
7. `.claude/settings.json` — **merge in** (never clobber an existing file) the permission rules
    from the template: allow rules so driver-run iterations proceed without per-command prompts,
    deny rules backing two loop invariants (no edits to `.cid/target.md`, no push to the protected
    branch). The template's commentary in `references/templates.md` is authoritative for the
    rules' rationale — in particular the compound-gate rule (**one allow rule per quality-gate
    subcommand**) and why the pack lives at `.cid/`, not under `.claude/`.
8. Greenfield only: `git init` if needed, the stack scaffold the gate needs, and a `CLAUDE.md`
    noting the project is built by the CID loop (conventions, glossary seed)

Then: create the loop branch per the chosen branch model, and commit **only the files this init
created or modified** as `cid(init): scaffold CID context pack` — add them by explicit path, never
`git add -A`/`git add .`, so pre-existing uncommitted work stays out of the commit (tell the user
what was left unstaged). Explicit paths do not protect a file init *modifies*: if a file you must
edit (typically `.claude/settings.json`) already carried uncommitted user changes per the Step 1
`git status`, staging it would sweep those hunks in too — ask the user to commit or stash that
file **before** you edit it. Run the quality gate once to confirm it is green (fix
the scaffold until it is — a red gate at init poisons every later iteration).

## Step 5 — Hand off

Report what was created and end with next steps:

1. `/long-horizon:build` — run the first iteration by hand and watch the four roles.
2. Drive it: `/goal … Loop: IDLE or STOP …` or `/loop 20m /long-horizon:build` (details in the
    build skill's `references/automation.md`).
3. `/long-horizon:status` any time; `/long-horizon:retro` after ~10 iterations.
4. To steer the loop later: edit `target.md` / file issues — never edit code mid-loop without
    committing, and prefer a `cid(steer):` commit for out-of-band interventions.
