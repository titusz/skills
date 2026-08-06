# Changelog

All notable changes to this marketplace are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the marketplace
version (`metadata.version` in `.claude-plugin/marketplace.json`) follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This version tracks the **catalog as a whole**: a new plugin is a minor bump, a
catalog-wide fix is a patch. Individual plugins carry their own `version` in
their `plugin.json` — see [Versioning](.claude/CLAUDE.md#versioning).

## [0.7.0] — 2026-08-06

### Added

- **evaluate-startup** — turn a raw startup or business idea into an
    evidence-backed, scored evaluation with a durable artifact trail. Runs an
    adaptive founder interview (max 3 batches of 3 plain-language questions,
    skipping anything already answered), parallel research subagents across
    five standard angles (market, competitors, technology, customer economics,
    regulation/timing), and an adversarial review pass (fact-checker,
    consistency auditor, devil's advocate) before rendering. The scoring model
    separates **attractiveness** (weighted composite over 6 categories, scored
    against explicit anchors) from **conviction** (evidence strength), and maps
    both to a verdict band (pursue/prototype/validate/explore/monitor/avoid)
    with falsifiable assumptions, kill criteria, and a cheapest-first
    validation plan. A bundled `render.py` (uv, PEP 723) validates the
    `analysis.json` against a JSON Schema plus semantic checks (weight sums,
    recomputed composite/conviction, mechanically derived verdict band,
    dimension-mean drift), renders a
    self-contained light/dark HTML report, and maintains a searchable card
    index across all evaluations.

## [0.6.1] — 2026-08-06

### Fixed

- **devcontainer-setup 0.2.0** — host Claude Code sign-ins now carry into the
    container without a login prompt: sign-in/account state lives in
    `~/.claude.json` (not in `.credentials.json`), so the host file is mounted
    read-only at `~/.claude.json-host` and a new `setup-claude.sh` merges
    exactly the `oauthAccount` + `hasCompletedOnboarding` fields into the
    container's config — never a whole-file copy, which would import host-only
    MCP servers and history and could clobber in-container state on rebuild.
    The seed retries transient bind-mount errors and is re-runnable via
    `doctor.sh --fix`; the doctor reports account/onboarding state without
    contradicting its credentials check on Keychain-only (macOS) hosts, and
    `init-host.sh` no longer aborts container creation when `~/.claude.json`
    exists as a directory or the stub cannot be written.

## [0.6.0] — 2026-07-20

### Added

- **devcontainer-setup** — generate or upgrade a complete `.devcontainer/`
    setup for any project. Mounts the host's git identity and Claude Code/Codex
    credentials into the container (Codex via a named volume seeded from a
    read-only host mount, since its SQLite/WAL store breaks on Windows bind
    mounts), resolves the host home cross-platform via the
    `${localEnv:HOME}${localEnv:USERPROFILE}` idiom, and degrades gracefully
    when host tooling is missing (stub creation + sign-in-from-container).
    Toolchains are pinned in `mise.toml` and provisioned by `mise install`
    (language-tailored: Python/uv, Node, Go, Rust, and anything in the mise
    registry; ML projects get commit-safe CUDA GPU access via
    `hostRequirements.gpu: "optional"` that degrades to CPU-only on hosts
    without a GPU), a shared `bootstrap.sh` plus a `CLAUDE_CODE_REMOTE`-guarded
    `SessionStart` hook makes the same repo work in Anthropic cloud
    (claude.ai/code) sessions, and `doctor.sh` / `mise run doctor` verifies or
    repairs (`--fix`) git auth, agent credentials, toolchains, volume
    ownership, and line endings. Editor-agnostic (Zed, VS Code, devcontainer
    CLI) and free of secrets or machine-specific paths in committed files.
    User-invoked only (`disable-model-invocation` — it never auto-triggers);
    the slash command accepts a target directory plus a free-text project
    brief so it can also bootstrap fresh, empty repositories where there is
    nothing to inspect.

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
[0.6.0]: https://github.com/titusz/skills/releases/tag/v0.6.0
[0.6.1]: https://github.com/titusz/skills/releases/tag/v0.6.1
[0.7.0]: https://github.com/titusz/skills/releases/tag/v0.7.0
