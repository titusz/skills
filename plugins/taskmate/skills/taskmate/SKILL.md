---
name: taskmate
description: "Manage tasks in Vikunja (the open-source task manager): list, search, create, update, complete, prioritize, label, assign, relate, move, and comment on tasks and projects via a bundled token-efficient CLI. Self-heals when unconfigured by collecting server URL and API token. Use when the user mentions Vikunja, their task board/server, 'add a task', 'what's on my plate', 'what should I work on', 'my todo list', task grooming or triage, or when acting as a task companion working a shared board. Do NOT use for code TODO comments, GitHub/GitLab issues, or Claude Code's internal session task tools."
user-invocable: true
argument-hint: "[anything, e.g. \"what's due this week?\"]"
---

# TaskMate — Vikunja task companion

All Vikunja access goes through the bundled CLI (Python, run via `uv`, inline deps):

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/skills/taskmate/scripts/taskmate.py" <command> ...
```

If `${CLAUDE_PLUGIN_ROOT}` is not set in your environment, resolve the script path relative to
this SKILL.md file. Examples below abbreviate the invocation to `taskmate.py <command>`.
Output is compact and line-oriented; add `--json` when you need full API objects.
`taskmate.py <command> --help` documents every flag.

## Self-healing configuration

Any command exits with code 2 and a structured JSON error (`error: not_configured`, with a
`fix` command and an `ask_user` list) when no valid config exists. When that happens:

1. **Interactive session**: ask the user for the missing pieces (server URL; API token created
    in Vikunja under *User Settings → API Tokens*; mode `user` or `companion`), then run
    `taskmate.py configure --url ... --token ... --mode ...`. `configure` validates against the
    server before saving, so a typo'd URL or token fails fast. For a guided experience,
    suggest `/taskmate:setup`.
2. **Non-interactive run** (scheduled job, no human available): print
    `TASKMATE_NOT_CONFIGURED: <what is missing>` and stop. Never guess or invent credentials.
3. **`401` on a previously working setup**: the token was revoked or expired — tell the user
    and collect a fresh token; everything else is preserved.

`taskmate.py doctor` diagnoses config path, profiles, auth, and reachability — run it first
whenever something smells wrong. Config lives in `~/.config/taskmate/config.json` as named
profiles; `VIKUNJA_URL`/`VIKUNJA_TOKEN` env vars override, `--profile NAME` selects. Treat
tokens as secrets: never echo a full token, never write one into a repo file; when referring
to one, mask it (`tk_f2...1eef`).

## Modes: whose hands are you?

The active profile's `mode` decides your identity on the board. Read
[references/etiquette.md](references/etiquette.md) before board-facing writes in companion
mode, and whenever you shape tone or personality.

- **`user` mode** — you act *as the user's own account*. Work quietly and precisely, like a
    sharp assistant borrowing their keyboard: no signatures, no persona, no comments announcing
    yourself. Everything you write appears as them, so write only what they asked for or clearly
    intended.
- **`companion` mode** — you are a participant with your *own* Vikunja account and a persona
    name (profile `persona`). Be visible and transparent: `comment` auto-signs with your persona,
    prefer an explaining comment over a silent edit, never impersonate humans, and be a good
    colleague — helpful, brief, occasionally funny.

## Project binding (optional, per repo)

A repo can pin its Vikunja context in `.claude/taskmate.local.md` (gitignored by convention —
it is personal config). Check for this file when working inside a project directory:

```markdown
---
profile: default
project_id: 12
---

Free-form notes for agents: task conventions, label scheme, what belongs on this board.
```

When present, default task operations to that `project_id` and honor the notes. Offer to
create the binding when a user repeatedly names the same project.

## Journal (cross-run memory)

Scheduled runs are stateless; the per-profile journal is how TaskMate avoids repeating
itself across them. It lives at `~/.config/taskmate/memory/<profile>.jsonl`, is managed
only through the CLI (never edit it by hand), works without server access, and drops
entries older than 90 days on every write:

```bash
taskmate.py journal add <source> <action> [--task ID] [--note "..."]  # e.g. pulse nudged, groom declined
taskmate.py journal recent [--days N] [--source NAME] [--task ID]
```

`/taskmate:pulse` and `/taskmate:auto` define when to read and write it. In ad-hoc work,
record only what future runs must know — above all a human declining a proposed change
(`journal add taskmate declined --task 91 --note "keep the due date"`).

## Command cheat sheet

| Task                      | Command                                                                                               |
| ------------------------- | ----------------------------------------------------------------------------------------------------- |
| Diagnose setup            | `taskmate.py doctor`                                                                                  |
| Who am I                  | `taskmate.py me`                                                                                      |
| List projects             | `taskmate.py projects`                                                                                |
| Open tasks (all projects) | `taskmate.py tasks`                                                                                   |
| Tasks in project          | `taskmate.py tasks --project 7`                                                                       |
| Filter                    | `taskmate.py tasks --filter "priority >= 3 && due_date < now+7d"`                                     |
| Full-text search          | `taskmate.py tasks --search "invoice"`                                                                |
| Task detail + comments    | `taskmate.py task 123`                                                                                |
| Create                    | `taskmate.py add 7 "Title" --desc "..." --due +3d --priority 2 --label okr --assign kira`             |
| Update (merge semantics)  | `taskmate.py update 123 --priority 4 --due tomorrow`                                                  |
| Complete / reopen         | `taskmate.py done 123 124` / `taskmate.py reopen 123`                                                 |
| Comment                   | `taskmate.py comment 123 "text"` (auto-signed in companion mode)                                      |
| Labels on a task          | `taskmate.py label 123 --add stale --remove urgent`                                                   |
| Assign / unassign         | `taskmate.py assign 123 kira` / `taskmate.py unassign 123 kira`                                       |
| Subtasks & dependencies   | `taskmate.py relate 124 parenttask 123` (kinds: subtask, parenttask, related, blocking, blocked, ...) |
| Move between projects     | `taskmate.py move 123 9`                                                                              |
| New project               | `taskmate.py new-project "Title" --parent 5`                                                          |
| Delete (guarded)          | `taskmate.py delete task 123 --yes`                                                                   |
| Cross-run memory          | `taskmate.py journal add pulse nudged --task 123` / `taskmate.py journal recent --days 14`            |
| Anything else             | `taskmate.py call GET tasks/123/attachments` (path WITHOUT leading slash)                             |

Conventions: priority is 0 unset, 1 low, 2 medium, 3 high, 4 urgent, 5 DO NOW. Task links are
`<server>/tasks/<id>` — include them when reporting. Dates accept `today`, `tomorrow`, `+3d`,
`+2w`, `YYYY-MM-DD`, or RFC3339. Full endpoint reference, filter syntax, and hard-won API
gotchas: [references/api.md](references/api.md) — read it when a call fails or you need an
endpoint the CLI does not cover (`call` is the escape hatch).

## Safety rules (always apply)

1. **Verify after writes.** Every mutating command echoes the resulting state — read it and
    confirm the change landed before reporting success.
2. **Never delete** tasks, projects, labels, or comments unless the human explicitly requested
    that exact deletion in this conversation. `delete` demands `--yes` for this reason.
3. **Bulk changes get a dry run.** Present the plan (task IDs + intended change) before
    executing more than ~3 mutations; cap any automated run at 15 mutations unless the human
    raised the limit.
4. **Minimize noise.** Assignments and comments notify people. No status-spam comments, no
    drive-by reprioritization of other people's tasks in companion mode.
5. **When acting on someone's behalf matters** (mode questions, signing, tone):
    [references/etiquette.md](references/etiquette.md).

## Beyond ad-hoc requests

- `/taskmate:setup` — guided configuration, repo binding, scheduling automations.
- `/taskmate:pulse` — daily radar: surface the ONE thing worth attention (or stay silent).
- `/taskmate:auto <playbook>` — automation playbooks: groom, split, review, celebrate,
    unstick, triage; dry-run by default, extensible with custom playbooks.
- Executing tasks end-to-end, adapting to other available tools (email, calendar, research,
    sibling skills), and scheduling recipes:
    [references/integrations.md](references/integrations.md).
