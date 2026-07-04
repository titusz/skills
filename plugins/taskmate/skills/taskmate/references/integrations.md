# Integrations: adapting to your environment

TaskMate is designed for agents whose other tools are unknown in advance. This file covers
discovering what you have, putting it to work, executing tasks end-to-end, and running on a
schedule.

## Capability probe

At the start of substantial TaskMate work (especially scheduled runs), take stock of what
this session can actually do — check your available tools for:

- **Web search / fetch** → research for `unstick`, enrich task context with sources.
- **Email** → deliver pulse nudges or weekly reviews to humans (only when genuinely useful;
    see the noise ledger in etiquette.md).
- **Calendar** → correlate due dates with real availability ("three urgent tasks due Thursday,
    but your Thursday is back-to-back meetings").
- **Browser automation** → operate the Vikunja web UI for the rare things the API lacks.
- **Code / repo access** → execute technical tasks directly, link commits and PRs in task
    comments.
- **Sibling skills** (if installed, from this marketplace or elsewhere): `deep-research` for
    serious task research, `systems-thinking` when a task is stuck because the *decision* is
    unclear, `high-stakes` for deliverables where a quiet mistake is expensive, `long-horizon`
    when an epic is really a multi-session project needing its own iteration loop.

Never assume a capability: verify the tool exists before promising its output. Degrade
gracefully — no email tool means the pulse nudge goes to the conversation, not nowhere.

## The task execution loop

TaskMate's highest form: don't just manage tasks — *do* them. When asked to work a board
(or a scheduled run finds a task marked for you, e.g. labeled `agent` or assigned to the
companion account):

1. **Pick** one task you can genuinely complete with the tools you verified. Prefer: assigned
    to you > labeled for agents > explicitly requested. Skip tasks needing human judgment.
2. **Claim** it (companion mode: assign yourself + one-line comment; user mode: only work
    tasks the user told you to work).
3. **Execute** with whatever tools apply. Stay inside the task's scope.
4. **Report on the task**: comment with the outcome, links, and evidence; set `done` or
    `percent_done` honestly. Partial progress with a clear handoff note is a fine outcome.
5. **Stop after a bounded number** of tasks per run (default: 1–3). A working session, not a
    rampage.

## Scheduling automations

Every schedulable entry point is quiet by design: `/taskmate:pulse --quiet` prints exactly
`NO_SIGNAL` when nothing deserves attention; `/taskmate:auto <playbook>` prints `NO_ACTION`
when there is nothing to do. Wrappers can suppress those outputs to keep silent runs silent.

**Inside Claude Code** — ask for it in natural language ("run /taskmate:pulse --quiet every
weekday at 8:30") so the harness creates the scheduled job, where supported.

**OS-level cron (Linux/macOS):**

```cron
# Morning radar, weekdays 08:30
30 8 * * 1-5  claude -p "/taskmate:pulse --quiet" --allowedTools "Bash,Read,Glob,Grep"

# Weekly backlog grooming with mutations, Mondays 07:00
0 7 * * 1    claude -p "/taskmate:auto groom --apply" --allowedTools "Bash,Read,Glob,Grep"

# Friday afternoon review + celebration
0 16 * * 5   claude -p "/taskmate:auto review" --allowedTools "Bash,Read,Glob,Grep,WebSearch"
```

**Windows Task Scheduler:** same `claude -p ...` command via `schtasks /create` or a
scheduled PowerShell action.

Scheduling guidance:

- Start read-only (`pulse`, dry-run playbooks); add `--apply` only after a week of sane
    dry-run output.
- Give mutating jobs the narrowest tool allowlist that works.
- Scheduled runs stay non-repetitive via the journal (`taskmate.py journal ...`, per-profile
    file in `~/.config/taskmate/memory/`). It writes through the CLI, so the `Bash` allowlist
    above already covers it — no extra write permissions needed.
- A scheduled run that hits `not_configured` or `401` must report
    `TASKMATE_NOT_CONFIGURED`/the auth error and exit — never retry-loop against a production
    server, never invent credentials.
- Sensible rhythm: `pulse` daily, `groom`/`triage` weekly, `review`+`celebrate` weekly
    (Friday), `unstick` weekly, `split` on demand.

## Repo ↔ board bridging

When working inside a repository bound via `.claude/taskmate.local.md`:

- On finishing significant repo work, offer to update the corresponding board task (comment
    with the commit/PR link, adjust `percent_done`).
- When the user describes new work in conversation, offer to capture it as a task in the
    bound project — capture beats memory.
- Keep direction honest: the board is the shared source of truth for *what and why*; the repo
    holds *how*. Don't duplicate long technical detail into task descriptions — link instead.
