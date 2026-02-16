# titusz/skills

A Claude Code plugin marketplace hosted at github.com/titusz/skills.

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
└── README.md
```

## Adding a Plugin

1. Create `plugins/<name>/` with the standard plugin layout
2. Create `plugins/<name>/.claude-plugin/plugin.json` with manifest
3. Add skills in `plugins/<name>/skills/<skill-name>/SKILL.md`
4. Register the plugin in `.claude-plugin/marketplace.json` under `plugins`
5. Update README.md with the plugin listing

## Plugin Development Guidelines

- Each plugin is self-contained in `plugins/<name>/`
- Plugin names use kebab-case (lowercase letters, numbers, hyphens)
- Skills follow the [Agent Skills](https://agentskills.io) open standard
- Keep `SKILL.md` under 500 lines; move reference material to separate files
- Use YAML frontmatter for metadata (`name`, `description`, `allowed-tools`, etc.)
- Bundled scripts use Python with `uv`/`uvx` for dependency management
- All scripts must be cross-platform (Linux, macOS, Windows)
- Use `${CLAUDE_PLUGIN_ROOT}` in hooks/scripts for portable paths

## Script Standards

- Python scripts use `uv` or `uvx` for dependency management and execution
- Use `#!/usr/bin/env python3` shebangs
- Inline script dependencies with `uv` where possible to keep plugins self-contained
- Test scripts on Windows (MSYS/Git Bash) in addition to Linux/macOS
