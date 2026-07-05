# Changelog

All notable changes to this marketplace are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the marketplace
version (`metadata.version` in `.claude-plugin/marketplace.json`) follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This version tracks the **catalog as a whole**: a new plugin is a minor bump, a
catalog-wide fix is a patch. Individual plugins carry their own `version` in
their `plugin.json` — see [Versioning](.claude/CLAUDE.md#versioning).

## [0.5.1] — 2026-07-05

### Fixed

- **taskmate 0.1.1** — Vikunja API compatibility fixes for task listing and
    filters. `tasks --project N` now scopes through the filter grammar
    (`project_id = N` on `GET /tasks`) instead of `GET /projects/{id}/tasks`,
    which current Vikunja exposes only for task creation. All bundled filter
    examples (pulse scans, groom/review/celebrate playbooks, docs) now use the
    snake_case field names the API accepts (`due_date`, `done_at`,
    `percent_done`) — the camelCase spellings shown in the Vikunja web UI are
    translated by its frontend and rejected on raw API calls.

## [0.5.0] — 2026-07-04

### Added

- **taskmate** — a task companion for the [Vikunja](https://vikunja.io) task
    manager. Self-healing configuration (collects server URL + API token when
    missing, structured errors agents can act on), a token-efficient bundled CLI
    (Python via `uv`, covers tasks/projects/labels/assignees/relations/comments
    plus a raw-API escape hatch), and two identity modes: `user` (act as the
    human's own account, quietly) or `companion` (the agent's own account with a
    signing persona and colleague etiquette). Skills: the auto-triggering core,
    `/taskmate:setup` (guided onboarding), `/taskmate:pulse` (read-only daily
    radar — one high-signal nudge or silence), and `/taskmate:auto <playbook>`
    (dry-run-by-default automations: groom, split, review, celebrate, unstick,
    triage; extensible via custom playbook files). A per-profile journal
    (`taskmate.py journal add|recent`, 90-day retention) gives otherwise
    stateless scheduled runs cross-run memory, so pulse and playbooks don't
    repeat nudges or re-propose changes a human declined.

## [0.4.0] — 2026-07-02

### Added

- **long-horizon** — Continuous Iterative Development (CID) for long-horizon
    projects, distilled from CID harnesses proven on two real long-running builds.
    An autonomous loop of four fresh-context roles (update-state → define-next →
    advance → review) advances a project in small verified increments toward a
    human-owned target. The loop self-determines its phase (new/poc/mvp/stable)
    from checkable exit criteria and adjusts rigor per phase; skills:
    `/long-horizon:init` (greenfield/brownfield setup wizard),
    `/long-horizon:build` (one iteration), `/long-horizon:status` (read-only
    report), `/long-horizon:retro` (self-improvement pass with guarded
    auto-apply).

## [0.3.1] — 2026-06-13

### Changed

- **address-feedback** (`0.1.0` → `0.1.1`) — instruct the agent to avoid
    overengineering when applying fixes: right-size each fix to the problem (no
    abstraction, config knob, helper layer, or defensive scaffolding the issue
    doesn't call for), and treat a fix that seems to need new structure or a broad
    refactor as an escalation signal rather than a licence to build it inline.

## [0.3.0] — 2026-06-13

### Added

- **address-feedback** — triage and act on a code review without assuming the
    reviewer is right: verify each item against the actual code, apply the
    small/valid/uncontested fixes directly, escalate load-bearing or risky ones to
    the user as grounded options, then run the project's quality gates before
    reporting.

## [0.2.0] — 2026-06-13

### Added

- **cybernetics** — review an idea, system, or problem against Frederic Vester's
    8 bio-cybernetic rules; map feedback loops, score each rule, surface the
    highest-leverage fixes, and judge viability.

## [0.1.0] — 2026-02-16

Initial marketplace release. (Reconstructed retroactively — the marketplace
predates this changelog.) Plugins available at this version:

- **get-youtube-transcript** — fetch transcripts from YouTube videos.
- **python-code-simplifier** — Opus subagent that simplifies and refines Python code.
- **zensical-customizer** — customize and extend Zensical documentation sites.
- **create-cli** — design command-line interface parameters and UX.
- **docs-for-agents** — create prescriptive reference documentation for AI coding agents.
- **systems-thinking** — classify a problem (clear/complicated/complex/chaotic) and recommend the matching protocol.
- **high-stakes** — run any task through an adversarial-verification Workflow.

[0.1.0]: https://github.com/titusz/skills/releases/tag/v0.1.0
[0.2.0]: https://github.com/titusz/skills/releases/tag/v0.2.0
[0.3.0]: https://github.com/titusz/skills/releases/tag/v0.3.0
[0.3.1]: https://github.com/titusz/skills/releases/tag/v0.3.1
[0.4.0]: https://github.com/titusz/skills/releases/tag/v0.4.0
[0.5.0]: https://github.com/titusz/skills/releases/tag/v0.5.0
[0.5.1]: https://github.com/titusz/skills/releases/tag/v0.5.1
