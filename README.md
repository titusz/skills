# titusz/skills

A personal [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugin marketplace with reusable
skills, agents, and hooks.

## Installation

Add the marketplace and browse available plugins:

```bash
/plugin marketplace add titusz/skills
```

Then install individual plugins:

```bash
/plugin install <plugin-name>@titusz-skills
```

## Plugins

| Plugin                     | Description                                                                                                          | License    |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------- | ---------- |
| **skill-creator**          | Guide for creating effective Claude Code skills with structured methodology, design patterns, and validation tooling | Apache-2.0 |
| **get-youtube-transcript** | Fetch transcripts from YouTube videos using youtube-transcript-api                                                   | Apache-2.0 |
| **python-code-simplifier** | Simplifies and refines Python code for clarity, consistency, and maintainability                                     | Apache-2.0 |
| **zensical-customizer**    | Customize and extend Zensical documentation sites with interactive pages, templates, JS widgets, and CSS styling     | Apache-2.0 |
| **create-cli**             | Design CLI parameters and UX: arguments, flags, subcommands, help text, output formats, error messages, exit codes   | Apache-2.0 |
| **docs-for-agents**        | Create and maintain prescriptive reference documentation optimized for AI coding agents                              | Apache-2.0 |

## Development

To test plugins locally during development:

```bash
claude --plugin-dir ./plugins/<plugin-name>
```

## License

MIT
