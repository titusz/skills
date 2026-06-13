# titusz/skills

A Claude Code **plugin marketplace** (github.com/titusz/skills). The repo root *is* the
marketplace root — there is no build step and no application. "Code" here is mostly Markdown
(`SKILL.md`, agent definitions, reference docs) plus JSON manifests. Plugins distribute three
kinds of artifacts: **skills**, **agents** (subagents), and **hooks**. Skills follow the
[Agent Skills](https://agentskills.io) open standard.

## Project Structure

```
skills/                           # repo root = marketplace root
├── .claude-plugin/
│   └── marketplace.json          # marketplace catalog (lists all plugins)
├── plugins/
│   └── <plugin-name>/            # each plugin is self-contained
│       ├── .claude-plugin/
│       │   └── plugin.json       # plugin manifest (name, version, description)
│       ├── skills/               # skills provided by this plugin
│       │   └── <skill-name>/
│       │       ├── SKILL.md      # skill entrypoint (required)
│       │       └── scripts/      # bundled scripts (optional)
│       ├── agents/               # custom subagents (optional)
│       └── hooks/                # hook configurations (optional)
├── .claude/                      # project dev tooling (not distributed)
│   └── CLAUDE.md
├── cauldron/                     # internal experiments (gitignored)
├── CHANGELOG.md                  # marketplace release notes
└── README.md
```

## Commands

There is no compiler or test suite — validation is the pre-commit hooks. This repo uses
**`prek`** (a drop-in pre-commit runner, not `pre-commit`):

```bash
prek run --all-files            # all hooks: check-json, check-yaml, ruff, ruff-format, mdformat
prek run check-json --all-files # validate marketplace.json + every plugin.json
prek run mdformat --all-files   # format Markdown (mkdocs flavor; numbered lists, LF endings)
prek run ruff --all-files       # lint/format any bundled Python (scripts/)
```

Run a plugin against the live working tree (tightest edit-test loop, bypasses the cache):

```bash
claude --plugin-dir ./plugins/<plugin-name>
```

## Architecture: how a plugin loads

Wiring a plugin in touches **four** places — the first three ship to users; the fourth makes
it auto-load for local dogfooding in this repo:

1. `plugins/<name>/.claude-plugin/plugin.json` — the plugin manifest
2. `.claude-plugin/marketplace.json` — the marketplace catalog entry (root-level)
3. `README.md` — the human-facing plugin table
4. `.claude/settings.json` — `enabledPlugins["<name>@titusz-skills"] = true` for local auto-load

`.claude/settings.json` self-registers the repo as a `directory` marketplace named
`titusz-skills` with `path: "."` (intentionally relative — do not let the CLI rewrite it to an
absolute Windows path). Launching `claude` from the repo root then auto-loads every
in-development plugin.

**Cache gotcha:** installed plugins are copied into
`~/.claude/plugins/cache/titusz-skills/<plugin>/<version>/`, keyed by version — not live-linked.
Editing a `SKILL.md` is **not** picked up by `plugin marketplace update`. To refresh a cached
install: bump `version` in `plugin.json`, or
`claude plugin uninstall <name>@titusz-skills --scope project && claude plugin install <name>@titusz-skills --scope project`,
then restart. For active development prefer `claude --plugin-dir` above, which reads the working
tree directly.

## Adding a Plugin

1. Create `plugins/<name>/` with the standard plugin layout
2. Create `plugins/<name>/.claude-plugin/plugin.json` with manifest (start at `version` `0.1.0`)
3. Add skills in `plugins/<name>/skills/<skill-name>/SKILL.md`
4. Register the plugin in `.claude-plugin/marketplace.json` under `plugins`
5. Update README.md with the plugin listing
6. Enable local dogfooding in `.claude/settings.json`: `enabledPlugins["<name>@titusz-skills"] = true`
7. Bump the marketplace `metadata.version` (minor) and add a `CHANGELOG.md` entry
8. After committing, tag and release the new marketplace version (see Versioning)

## Versioning

Two independent version fields, two different jobs. Discovery is **pull-based** —
Claude Code has no push notification for new plugins; users only see catalog
changes after they run `/plugin marketplace update`, then browse `/plugin`. So we
signal changes out-of-band: README table, `CHANGELOG.md`, and GitHub releases.

**Marketplace version — `metadata.version` in `.claude-plugin/marketplace.json`**

- Purely informational; bumping it triggers no client behavior. It is the
    human-facing semver for the catalog as a whole.
- Bump **minor** when adding a plugin, **patch** for catalog-wide metadata fixes.
- Each bump gets a `CHANGELOG.md` entry and a matching git tag + GitHub release
    (`vMAJOR.MINOR.PATCH`).

**Plugin version — `version` in each `plugins/<name>/.claude-plugin/plugin.json`**

- This is the *functional* update key. Claude Code resolves a plugin's version in
    order: `plugin.json` `version` → marketplace entry `version` → git commit SHA →
    `unknown`. Because `plugin.json` wins, **it is the source of truth** — keep the
    marketplace entry's `version` in sync with it for display.
- **You must bump a plugin's `version` whenever you want already-installed users
    to receive changes.** Pushing commits without bumping is invisible to
    `/plugin update` — it reports "already at the latest version" because the
    version string (the cache key) is unchanged. The same key drives the local
    cache (see the cache gotcha above).
- A brand-new plugin needs no bump to be discoverable; users just refresh the
    marketplace and install it. Bumping only matters for updates to existing,
    installed plugins.
- Follow semver per plugin: patch for fixes, minor for new capability, major for
    breaking changes to a skill's interface or behavior.

**Release flow for a catalog change**

1. Make the plugin change (bump that plugin's `version` if it is an update).
2. Bump `metadata.version` and add a `CHANGELOG.md` entry.
3. Commit and push.
4. `git tag vMAJOR.MINOR.PATCH && git push origin vMAJOR.MINOR.PATCH`
5. `gh release create vMAJOR.MINOR.PATCH --title ... --notes ...` — the release
    notes are the announcement channel for "new plugins available."

## Skill Anatomy and Conventions

A skill is `plugins/<name>/skills/<skill-name>/SKILL.md` with YAML frontmatter, optionally
accompanied by a `references/` directory and/or `scripts/`.

- **`description` is the trigger.** It's how Claude decides to auto-invoke the skill, so the
    convention is to pack it with trigger phrases ("Use when…", quoted user phrasings) *and*
    negative guidance ("Do NOT use for…"). This matters more than the prose body.
- **Progressive disclosure.** `SKILL.md` is the entrypoint and stays lean (under 500 lines);
    heavyweight material goes in sibling `references/*.md` that the skill pulls in on demand.
- **Two execution patterns:**
    - *Self-contained* — the skill body does the work directly (e.g. `get-youtube-transcript`,
        `create-cli`).
    - *Delegating* — the skill frontmatter sets `allowed-tools: [Task]` and hands off to a
        subagent in `agents/` (e.g. `simplify-python` → the `python-code-simplifier` agent) or to a
        `Workflow` (e.g. `high-stakes`).
- **Common skill frontmatter keys:** `name`, `description`, `user-invocable` (exposes it as a
    `/slash` command), `argument-hint`, `allowed-tools`.
- **Agent frontmatter** (in `agents/*.md`) differs: `name`, `description`, `model`, `tools`,
    `permissionMode`, `memory`.

## Conventions

- Plugin names are kebab-case (lowercase letters, numbers, hyphens). Keep each plugin fully
    self-contained under `plugins/<name>/`.
- Markdown is auto-formatted by mdformat (mkdocs flavor) — numbered list markers and LF line
    endings are enforced; let the hook reformat rather than hand-tuning.
- `cauldron/` is gitignored scratch space for drafts and experiments before they become real
    plugins — never reference it from shipped plugins.
- Use `${CLAUDE_PLUGIN_ROOT}` in hooks/scripts for portable paths.

## Script Standards

- Bundled Python in `scripts/` runs via `uv`/`uvx` (e.g. `uvx --from <pkg> <entrypoint>`), never
    a global interpreter — this keeps each plugin self-contained.
- Use `#!/usr/bin/env python3` shebangs; inline script dependencies with `uv` where possible.
- All scripts must be cross-platform — test on Windows (MSYS/Git Bash) in addition to Linux/macOS.
