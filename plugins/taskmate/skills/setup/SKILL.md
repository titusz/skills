---
name: setup
description: "Guided TaskMate/Vikunja setup: create or update a connection profile (server URL + API token), choose user vs companion mode, pick a persona, bind the current repo to a Vikunja project, and schedule automations. Use when the user says 'set up taskmate', 'connect vikunja', 'configure my task server', wants to add a second profile/account, or when any TaskMate command reports not_configured or a 401."
user-invocable: true
argument-hint: '[profile-name]'
---

# TaskMate setup

Walk the user through a working, verified configuration. CLI:
`uv run "${CLAUDE_PLUGIN_ROOT}/skills/taskmate/scripts/taskmate.py" ...` (below: `taskmate.py`).

## 1. Assess

Run `taskmate.py doctor`. If a working profile already exists, say so and ask what they want:
add another profile (e.g. a companion account next to their user account), change mode or
persona, bind this repo to a project, or set up scheduled automations — then jump to that step.

## 2. Collect connection details

Ask the user (AskUserQuestion works well; one question at a time is kinder than a form):

1. **Server URL** — e.g. `https://tasks.example.com` (no `/api/v1` suffix needed).
2. **API token** — created in the Vikunja web UI: avatar → *Settings* → *API Tokens* →
    *Create a token*. Recommend granting all permissions the agent should have and warn that
    the token is **shown only once**. Never echo the full token back; mask it (`tk_ab...ef`).
3. **Mode** —
    - `user`: the token belongs to the user's own account; the agent acts as them, silently.
    - `companion`: the token belongs to a separate account for the agent. Requires someone to
        register that account and share the relevant projects with it (read+write). If the
        account doesn't exist yet, guide them: register it in the Vikunja UI, log in as it once,
        create its API token, share projects via project → *Share*.
4. **Persona** (companion mode only) — the signing name. If they have no preference, offer a
    couple of fitting suggestions with a wink and let them pick.
5. **Timezone** — IANA name (e.g. `Europe/Berlin`) so date filters resolve correctly.

## 3. Configure and verify

```bash
taskmate.py configure --url URL --token TOKEN --mode MODE [--persona NAME] [--timezone TZ] [--profile NAME] [--make-default]
taskmate.py doctor
```

`configure` validates against the live server before saving — on failure, fix URL/token and
retry rather than saving broken config. Then show the user who they're connected as and how
many projects are visible. In companion mode with zero visible projects, remind them to share
projects with the companion account.

## 4. Offer the nice-to-haves (optional, don't push)

- **Repo binding**: if working inside a git repo, offer to create `.claude/taskmate.local.md`
    (frontmatter: `profile`, `project_id`) pointing at one of their projects — list projects
    first so they can pick. Ensure the file is gitignored (it's personal config; add
    `.claude/taskmate.local.md` to `.gitignore` if needed).
- **Automations**: briefly present the schedulable pieces — `/taskmate:pulse --quiet` (daily
    radar), `/taskmate:auto groom|review|celebrate|unstick|triage` — and set up whichever they
    want, per the scheduling recipes in
    `${CLAUDE_PLUGIN_ROOT}/skills/taskmate/references/integrations.md`.
    Recommend starting with dry-runs.

## 5. Close the loop

Finish with a one-line summary (profile, account, mode, server, bound project if any) and one
concrete next step, e.g. "try `/taskmate:pulse`". First impressions count: make this moment
feel like meeting a great new coworker, not finishing a form.
