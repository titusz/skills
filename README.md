![titusz/skills — Claude Code plugin marketplace](assets/titusz-skills-banner.png)

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

| Plugin                     | Description                                                                                                                                                                                                                                                             | License |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| **get-youtube-transcript** | Fetch transcripts from YouTube videos using youtube-transcript-api                                                                                                                                                                                                      | MIT     |
| **python-code-simplifier** | Simplifies and refines Python code for clarity, consistency, and maintainability                                                                                                                                                                                        | MIT     |
| **zensical-customizer**    | Customize and extend Zensical documentation sites with interactive pages, templates, JS widgets, and CSS styling                                                                                                                                                        | MIT     |
| **create-cli**             | Design CLI parameters and UX: arguments, flags, subcommands, help text, output formats, error messages, exit codes                                                                                                                                                      | MIT     |
| **docs-for-agents**        | Create and maintain prescriptive reference documentation optimized for AI coding agents                                                                                                                                                                                 | MIT     |
| **systems-thinking**       | Apply systems thinking to a problem or decision — classify it (clear/complicated/complex/chaotic), diagnose with DART, recommend the matching protocol                                                                                                                  | MIT     |
| **high-stakes**            | Run any task through an adversarial-verification Workflow — many subagents hunt ten failure modes (silent assumptions, sycophancy, dead code, etc.) and loop until two clean rounds                                                                                     | MIT     |
| **cybernetics**            | Review an idea, system, or problem against Frederic Vester's 8 bio-cybernetic rules — map its feedback loops, score each rule, find the highest-leverage fixes, and judge its viability                                                                                 | MIT     |
| **address-feedback**       | Triage and act on a code review — verify each item against the actual code, apply the small/valid/uncontested fixes directly, escalate load-bearing or risky ones as grounded options, then run quality gates                                                           | MIT     |
| **long-horizon**           | Continuous Iterative Development (CID) for long-horizon projects — an autonomous loop of four fresh-context roles advances the project in small verified increments, self-determines its phase (new/poc/mvp/stable), and self-improves via learnings and retros         | MIT     |
| **taskmate**               | A task companion for the [Vikunja](https://vikunja.io) task manager — self-healing setup, token-efficient CLI, two identity modes (user/companion account), daily pulse radar, and schedulable automation playbooks (groom, split, review, celebrate, unstick, triage)  | MIT     |
| **devcontainer-setup**     | Generate or upgrade a cross-platform .devcontainer that mounts host git/Claude Code/Codex credentials, pins toolchains via [mise](https://mise.jdx.dev), bootstraps Anthropic cloud sessions, and ships a doctor check/repair command — zero secrets in committed files | MIT     |
| **evaluate-startup**       | Evaluate a startup or business idea with evidence — adaptive founder interview, parallel deep research, adversarial fact-checking, a scored analysis separating attractiveness from conviction, a standalone HTML report, and a searchable index of all evaluations     | MIT     |
| **imagegen**               | Generate and edit raster images via the Codex CLI's built-in image tool on a ChatGPT subscription (no API key) — reference images, reusable art-style cards, exact-size post-processing, outputs stored with their prompts in a project-local `cauldron/` folder        | MIT     |

## Development

To test plugins locally during development:

```bash
claude --plugin-dir ./plugins/<plugin-name>
```

## License

MIT
