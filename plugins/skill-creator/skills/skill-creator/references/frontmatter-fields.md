# Frontmatter Fields Reference

All supported YAML frontmatter fields for SKILL.md files.

## Required Fields

### name

Kebab-case identifier. Must match the skill directory name.

- Lowercase letters, digits, and hyphens only
- No leading/trailing hyphens, no consecutive hyphens
- Max 64 characters
- Cannot start with `claude` or `anthropic` (reserved prefixes)

### description

Primary triggering mechanism. Claude uses this to decide when to load the skill automatically.

- Include what the skill does AND when to use it
- Add trigger phrases users would actually say
- Add negative triggers to prevent over-triggering (e.g., "Do NOT use for X")
- Max 1024 characters

Good: `"Create and edit PDF documents. Use when working with .pdf files, merging PDFs, or extracting pages. Triggers on 'edit PDF', 'merge PDFs', 'PDF form'. Do NOT use for reading PDF content only."`

Bad: `"Helps with documents"` (too vague, no triggers)

## Optional Fields

### user-invocable

Controls whether users can invoke the skill directly with `/skill-name` syntax.

- `true` or `false` (default: depends on skill configuration)
- When enabled, the skill appears in the list of available slash commands
- Combine with `argument-hint` to guide user input

```yaml
user-invocable: true
```

### argument-hint

Placeholder text shown to users when invoking the skill. Only meaningful when
`user-invocable` is enabled.

```yaml
argument-hint: "PR URL or number"
```

### allowed-tools

Restricts which tools the skill can use. Useful for security-sensitive skills or
to prevent unintended side effects.

```yaml
allowed-tools:
  - Read
  - Glob
  - Grep
  - WebFetch
```

When omitted, the skill can use all available tools.

### model

Preferred model for executing the skill. Use when the skill's complexity warrants
a specific model tier.

```yaml
model: "sonnet"    # faster, cheaper - good for straightforward tasks
model: "opus"      # stronger reasoning - good for complex analysis
```

### disable-model-invocation

Prevents Claude from automatically triggering this skill based on description matching.
The skill can only be invoked explicitly by the user with `/skill-name`.

```yaml
disable-model-invocation: true
```

Useful for destructive operations, expensive workflows, or skills that should only
run on explicit request.

### context

Additional context configuration for the skill. Controls what additional files or
resources are loaded when the skill triggers.

### agent

Subagent configuration for the skill. Controls agent behavior such as tool access
and execution parameters.

### hooks

Shell commands that execute in response to skill lifecycle events. Use
`${CLAUDE_PLUGIN_ROOT}` for portable paths in hook commands.
