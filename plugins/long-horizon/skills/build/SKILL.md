---
name: build
description: >-
  Advance a long-horizon project by exactly one CID-loop iteration (update-state → define-next →
  advance → review), with rigor adjusted to the project's current phase (new/poc/mvp/stable). Use
  when explicitly asked to "run the build loop", "advance the project", "run one CID iteration", on
  /long-horizon:build, or when an automation (/goal, /loop, a scheduled task) drives autonomous
  building. Requires a CID context pack at .cid/ (create one with
  /long-horizon:init). NOT for one-off edits, questions, or reviewing unrelated work.
user-invocable: true
---

Run **one CID-loop iteration** — Continuous Iterative Development. You are the **orchestrator**: you
do no implementation yourself. You spawn four **roles**, each as an independent fresh-context
subagent, in order, and route their results. The roles ship with this plugin and read their own
context from `.cid/`; you only launch them and read the files they commit.

The point of four separate subagents is **role isolation**: the role that implements (`advance`)
must never be the role that reviews it (`review`). Do not collapse them or do their work inline.
Sequencing, the no-inline-implementation rule, and staying out of the pack files are enforced by
the Rules below, not by structure — hold to them exactly (design rationale:
`references/automation.md` → Design notes).

## Steps

1. **Preflight.** Confirm the CID context pack exists (`.cid/target.md`). If it
    does not, stop and tell the user to run `/long-horizon:init` first — never scaffold it yourself.
    Read `.cid/policy.md` for the **branch model**: ensure you are on the loop
    branch (create it if it does not exist — on a repo with no commits this simply starts it); the
    loop never commits to the protected branch. Run `git status --short` and note the starting
    state. *Done when* you have confirmed the pack, are on the loop branch, and noted the git state.

2. **update-state.** Spawn the `long-horizon:update-state` agent (Agent tool,
    `subagent_type: "long-horizon:update-state"`, prompt: "Run your role for this CID iteration.").
    When it returns, read `.cid/state.md`.

    - If `state.md` shows `## Status: IDLE` **and** records an unratified phase transition
        (a `Transition:` line under `## Phase` — whether recorded this iteration or carried
        forward from an aborted one) → skip to step 5 (`review` runs ratify-only) and route its
        signal. No phase change may end the loop unreviewed.
    - If it shows `## Status: IDLE` with no transition recorded → **stop the iteration**, emit
        `LOOP: IDLE` with the blockers it names, and report. Do not spawn the other roles.
        *Done when* `state.md` reflects this iteration's assessment (including the current phase), or
        you have emitted `LOOP: IDLE`, or you have routed to step 5 for ratification.

3. **define-next.** Spawn the `long-horizon:define-next` agent
    (`subagent_type: "long-horizon:define-next"`, same prompt). When it returns, read
    `.cid/next.md`.

    - If it says `## Step: NONE` → if `state.md` records a `Transition:` line, skip
        `advance` and go to step 5 (`review` runs ratify-only); otherwise stop, emit `LOOP: IDLE`
        with its `## Reason`, and report.
    - Otherwise confirm it defines exactly one work package with runnable Verification.
        *Done when* `next.md` holds one scoped, verifiable step (or you emitted `LOOP: IDLE`).

4. **advance.** Spawn the `long-horizon:advance` agent
    (`subagent_type: "long-horizon:advance"`, same prompt). It implements, tests to the phase's bar,
    runs the quality gate, writes `handoff.md`, and commits. *Done when* the subagent has returned
    and committed (or written a blocker handoff).

5. **review.** Spawn the `long-horizon:review` agent (`subagent_type: "long-horizon:review"`, same
    prompt). It independently inspects the diff, re-runs the gates, ratifies any phase transition
    `state.md` recorded this iteration, curates learnings, sets the verdict, appends the journal
    row, and pushes on PASS (per policy). When routed here from step 2 or 3 without an advance
    commit, it runs ratify-only (see the review role). When it returns, read
    `.cid/handoff.md`. *Done when* `handoff.md` carries a `**Verdict:**` and a
    `**Loop:**` line.

6. **Route the loop signal** from `handoff.md`:

    - `**Loop:** IDLE` → no autonomous work remains (project converged, or everything left is
        human-blocked — there is no separate `DONE` signal; target-met convergence is an IDLE
        case). Emit `LOOP: IDLE` and surface the blockers.
    - `**Loop:** STOP` (a `HUMAN REVIEW REQUESTED` was raised) → **halt**. Emit `LOOP: STOP` and
        surface the exact reason to the human. This is the one stop the autonomous loop keeps; do not
        try to resolve a human-only decision yourself.
    - `**Loop:** CONTINUE` (the normal case, **including a NEEDS_WORK verdict** — the next iteration
        retries) → emit `LOOP: CONTINUE`.
        *Done when* you have emitted exactly one `LOOP:` signal.

7. **Report.** End your output with this block verbatim (so a `/goal` evaluator — which reads only
    what you surfaced in the conversation — and the human can read the outcome without opening
    files):

    ```
    CID iteration complete.
    Phase:   <new | poc | mvp | stable>  (note a transition as "old → new")
    Verdict: <PASS | PASS_WITH_NOTES | NEEDS_WORK | SKIPPED>
    Loop:    <CONTINUE | IDLE | STOP>
    Step:    <the next.md step title; "ratify: <old> → <new>" on a ratify-only iteration; or "-">
    Note:    <one line — what landed, or why it stopped>
    ```

    Use `Verdict: SKIPPED` when the iteration stopped before `review` ran (IDLE at step 2/3, or a
    dead role).

## Rules

- **Spawn, don't do.** Never implement, scope, or assess inline — that destroys role isolation.
    Launch the subagents and read what they commit.
- **One iteration per invocation.** Looping across iterations is the driver's job (`/goal`,
    `/loop`, or a scheduled task) — see `references/automation.md` in this skill for driving the loop
    unattended.
- **Run roles in order** and stop early on `LOOP: IDLE` (steps 2–3) or `LOOP: STOP` (step 6). Do
    not spawn a later role after a stop signal.
- **Stay out of the agents' files.** They own `.cid/*`; you only read them to
    route.
- If a subagent dies or returns nothing, report it as a failed iteration (`LOOP: STOP`, Note: which
    role died) rather than papering over it.
