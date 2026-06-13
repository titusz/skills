# Changelog

All notable changes to this marketplace are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the marketplace
version (`metadata.version` in `.claude-plugin/marketplace.json`) follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This version tracks the **catalog as a whole**: a new plugin is a minor bump, a
catalog-wide fix is a patch. Individual plugins carry their own `version` in
their `plugin.json` — see [Versioning](.claude/CLAUDE.md#versioning).

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
