# Driving the CID loop unattended

The `build` skill runs **one** iteration. Building a whole project means running it many times.
This split is deliberate:

- **The skill** = one verified increment (`update-state → define-next → advance → review`).
- **The driver** = whatever re-runs the skill until the loop signals `IDLE` or `STOP`.
- **The quality gate** (from `policy.md`) = verification only. It does not loop — Claude does.

Every iteration ends with a report block containing `Verdict:` and `Loop:` lines (line order:
Phase, Verdict, Loop, Step, Note) — the `Loop:` line is the signal every driver below keys off; do
not parse "the last lines". The loop stops itself only on `Loop: IDLE` (no autonomous work left:
project converged or everything human-blocked) or `Loop: STOP` (a `HUMAN REVIEW REQUESTED` — a
decision only the human should make). A `NEEDS_WORK` verdict does **not** stop the loop; the next
iteration retries. There is no separate `DONE` signal — "project converged" is one of IDLE's
cases; automation ported from a harness that emitted `Loop: DONE` or `## Status: DONE` must key on
`IDLE` instead, or its stop condition will never fire.

## Three drivers (pick by how unattended you need it)

| Driver                       | Re-runs when            | Needs session open | Survives restart                    |
| ---------------------------- | ----------------------- | ------------------ | ----------------------------------- |
| **`/goal`**                  | previous turn finishes  | yes                | yes (`--resume`)                    |
| **`/loop`**                  | a time interval elapses | yes                | restored on `--resume` if unexpired |
| **Durable scheduler / `-p`** | a schedule fires        | no                 | yes (durable)                       |

*"Survives restart" means re-attaching when you manually resume the session (`--resume` /
`--continue`) — not running while the session is closed. A `/loop` schedule is restored on resume
if it has not hit its 7-day expiry — so **check the scheduled-task list before re-issuing
`/loop`**: a restored schedule plus a re-issued one double-fires full iterations. Only the last row
runs truly unattended.*

### A. `/goal` — drive until the loop parks itself (recommended for interactive bring-up)

`/goal` keeps starting a new turn after each one finishes until a condition holds; the condition and
the conversation are judged by a small fast model after every turn, so key it off the printed
report block:

```
/goal Run the /long-horizon:build skill to advance exactly one CID iteration, then repeat. Print the report block each time. The goal is MET when the latest report shows "Loop: IDLE" or "Loop: STOP" — on STOP, summarize the HUMAN REVIEW REQUESTED reason and hand back to me. Otherwise keep going. Stop after 40 turns regardless.
```

- Setting the goal starts the first turn immediately.
- `/goal` is model-driven, not a deterministic re-invoker — the "Run the skill … then repeat"
    phrasing is what makes re-invocation reliable. For a guaranteed cadence use `/loop` (driver B).
- The `stop after 40 turns` clause bounds a runaway loop — keep one; the role agents have no
    per-role turn cap, so by default this driver-level cap is the only runaway bound.
- Pair with an auto/accept-edits permission mode so iterations run without per-tool approval.
- `/goal` requires workspace trust and hooks enabled (it is a Stop hook under the hood).

### B. `/loop` — re-run on an interval

`/loop` re-runs a prompt on a cadence (session-scoped; auto-expires after 7 days; fires only while
the session is idle; `Esc` stops it):

```
/loop 20m /long-horizon:build
```

If `/long-horizon:init` wrote a project `.claude/loop.md` (it points a bare `/loop` at this build
skill), then a **bare** `/loop` — or `/loop 30m` with no prompt — also drives the loop.

Use `/goal` to stop the moment the loop parks; use `/loop` for a steady heartbeat while you watch.
Keep the interval ≥ the time one iteration takes.

### C. Durable scheduling — runs without an open session

For truly unattended building, use a durable scheduler that re-issues one deterministic iteration
per fire:

- **Bundled reference driver** — `/long-horizon:init` copies it to `.cid/bin/driver.py`. From the
    project root:

    ```
    uv run .cid/bin/driver.py --max-iterations 20
    ```

    runs `claude -p "/long-horizon:build" --permission-mode acceptEdits` in a loop, parsing the
    printed `Loop:` line after each run. Exit codes: `0` = IDLE, `2` = STOP, `6` = iteration
    budget exhausted while `Loop: CONTINUE` — normal progress, re-run to continue (the expected
    exit almost every fire under the per-tick scheduling below). `3`/`4`/`5` are abnormal (no
    `Loop:` line in the output, per-iteration timeout, environment/process failure — including
    claude exiting non-zero) — treat those as "human, look at this". Each iteration's full output lands in `.cid/logs/`
    (self-gitignored), so a failed trajectory can be replayed and diagnosed instead of guessed at.
    Flags: `--interval`, `--timeout`, `--permission-mode`, `--prompt`, `--claude`.

- **OS scheduler / Desktop scheduled task** — fire `uv run .cid/bin/driver.py --max-iterations 1`
    per tick: exit `6` means the iteration ran and the loop wants to continue — leave the schedule
    armed; disable the task on `0`/`2` and triage `3`–`5`. (Or fire the
    `/long-horizon:build` prompt directly and disable when a fire reports `Loop: IDLE` or
    `Loop: STOP`.)

- **CI (e.g. GitHub Actions `schedule`)** — run the driver (one or a few iterations per fire),
    with two hard requirements. The push policy
    in `policy.md` must be **"push loop branch every iteration"**: a stateless runner destroys
    unpushed commits, so under push-on-PASS every NEEDS_WORK iteration vanishes and the next fire
    retries it identically, with no journal trail for the stuck-loop STOP to ever fire. And the
    checkout needs history (`fetch-depth: 0` — the default shallow clone breaks review's
    `git diff HEAD~1..HEAD`). A fresh runner sees only committed *and pushed* files — which
    includes `.cid/bin/driver.py` itself, since the pack is committed.

Prefer a deterministic `/long-horizon:build`-per-fire over scheduling a `/goal` condition: it
guarantees the build skill is issued each fire and cannot be satisfied by a turn that merely
*says* `Loop: CONTINUE` (within a fire, role sequencing remains enforced by the skill's Rules —
see Design notes).

## Cost and safety notes

- **Permissions first.** An accept-edits permission mode covers the roles' pack writes, and the
    Bash allow rules `/long-horizon:init` scaffolds into `.claude/settings.json` cover the commands
    every iteration runs (git, `gh run list` for the CI check, the pack helper scripts under
    `.cid/bin/`, the quality-gate subcommands). The
    roles cannot remove this setup step themselves: Claude Code ignores the `permissionMode`
    frontmatter field (along with `hooks` and `mcpServers`) when loading agents from a plugin, for
    security — a marketplace plugin must not silently escalate past the user's chosen permission
    posture — so the accept-edits decision stays with you, per project. The
    init skill's `references/templates.md` is the authoritative commentary on those rules — the
    pack's `.cid/` location and the one-allow-rule-per-gate-subcommand splitting rule live there.
    Note that an **untrusted** workspace ignores project allow rules entirely, so accept the trust
    dialog once before headless driving. A permission denial mid-iteration halts safely:
    `LOOP: STOP` with a report naming the blocked action.
- Each iteration spawns **four subagents in series** — real cost and latency per iteration. The
    roles deliberately pin neither `model` nor effort in their frontmatter (the reference harnesses
    this skill distills pin top-tier models per role; a marketplace plugin cannot assume every
    project wants that cost), so the roles inherit the session's model — the flip side is that an
    unattended run on a weak session model gets weak roles. Pick the session model (and interval)
    deliberately.
- The role agents deliberately set no `maxTurns` cap (a role cut off mid-work leaves a
    half-implemented increment, which is worse than a slow one — bound runaway at the driver
    instead), so a hung role stalls the run until you notice. Keep `/goal` turn-caps small,
    schedule fires at an interval ≥ one iteration's typical time, and check unattended runs
    periodically.
- The loop works on the loop branch from `policy.md` and never pushes the protected branch; a human
    merges via a gated PR. Keep it that way — it is what makes unattended operation safe. Two of
    the safety invariants get a structural backstop: the deny rules `/long-horizon:init` scaffolds
    block Edit/Write edits to `target.md` and plain pushes to the protected branch (backstops with
    known bypass limits — the init templates' commentary documents them — layered with review's
    integrity scan). The rest — never weaken gates, each role writes only its own files — are
    prompt-level rules; know that limitation when running unattended.
- Triage every `Loop: STOP` promptly: the loop parked a decision it refuses to make for you.

## Recommended progression

1. **Bootstrap interactively.** Run `/long-horizon:build` once by hand. Watch the four roles.
    Confirm the gate goes green.
2. **Supervise.** Drive it while you watch: `/goal` (stops the moment the loop parks) or
    `/loop 20m /long-horizon:build` (deterministic heartbeat), with an auto permission mode.
3. **Graduate to unattended.** Schedule a durable driver — `.cid/bin/driver.py`, or your own loop
    firing `/long-horizon:build`. Each
    morning, triage any `Loop: STOP` or `Loop: IDLE` it parked for you, and occasionally run
    `/long-horizon:retro` to tune the loop from its own track record.

## Design notes

Rationale for the plugin's structural choices, collected here so the per-iteration prompts stay
lean:

- **A prose orchestrator, not a Workflow.** A structural substrate (schema-forced outputs,
    enforced sequencing) was considered and rejected: the loop must behave identically under
    headless `claude -p` in arbitrary user projects, where plain skills and agents are the only
    grounded, portable substrate. The cost: sequencing is enforced by the build skill's Rules, not
    by structure. One structural piece looked cheap but was dropped after testing:
    `disallowed-tools: Edit, Write` on the build skill would strip the file-editing tools from a
    drifted orchestrator, but the removal applies to the session's whole tool pool while the skill
    is active — spawned subagents included, regardless of their own `tools` frontmatter (verified
    empirically on Claude Code 2.1.198: a subagent declaring `tools: Write` cannot write while the
    parent skill disallows Write), which would break every role. The orchestrator's
    no-inline-implementation rule is therefore prose too.
- **A thin bundled driver, no more.** Driver C ships as `.cid/bin/driver.py` (copied into the
    pack by `/long-horizon:init`) because hand-written drivers kept re-solving the same two
    problems: parsing the `Loop:` line and keeping a replayable record of each iteration. The
    driver deliberately contains no loop intelligence — it only re-invokes
    `claude -p "/long-horizon:build"`, parses the report block, logs, and stops — so the rationale
    for replacing the earlier scripted-runner generation of this harness (which owned sequencing)
    does not apply to it, and a user whose scheduling environment (shell, CI, OS schedulers) wants
    its own idiom can replace it with a dozen lines and lose nothing.
- **No skill-scoped hooks as a structural backstop.** Skill-scoped `hooks` in SKILL.md frontmatter
    (unlike plugin-global hooks, which fire in unrelated projects) could gate tool use during the
    build skill without that noise. Not adopted: a hook can veto or re-prompt at a tool boundary
    but cannot itself sequence four subagent spawns, so enforcing role order would mean
    cross-platform hook scripts tracking loop state — reimplementing the orchestrator in a
    less auditable place. The deny rules `/long-horizon:init` scaffolds already give the two
    highest-value invariants a mechanical backstop; the rest stay prompt-level rules.
- **A committed learnings ledger, not agent `memory`.** The agent `memory` frontmatter key (in its
    committable `project` scope) would give each role persistent memory for free, but it lives
    under `.claude/agent-memory/` — a protected path whose writes are never auto-approved, the same
    constraint that moved the pack to `.cid/` — so unattended runs would stall on it; and each
    role would curate its own memory with no reviewer in the loop. The committed `learnings.md`
    index + `learnings/` detail files keep cross-iteration knowledge in one place that `review`
    curates and rotates, reviewable in git history.
- **Phase transitions: self-determined by `update-state`, ratified by `review`.** A dedicated
    phase-assessor role was rejected as an extra hop per iteration; instead the reviewer that
    already runs each iteration re-verifies any recorded transition, and the orchestrator routes
    otherwise-idle iterations through review while a transition is pending — no phase change ends
    the loop unreviewed.
