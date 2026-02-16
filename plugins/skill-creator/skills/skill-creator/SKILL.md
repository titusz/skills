---
name: skill-creator
description: Guide for creating effective Claude Code skills. Use when users want to create, build, update, or improve a skill that extends Claude's capabilities with specialized knowledge, workflows, or tool integrations. Triggers on "create a skill", "build a skill", "new skill", "improve this skill", "update skill", "skill for [use case]", "make a skill for", "design a skill", "create a plugin".
---

# Skill Creator

Guidance for creating effective Claude Code skills packaged as plugins.

## About Skills

Skills are modular, self-contained packages that extend Claude's capabilities by providing
specialized knowledge, workflows, and tools. They transform Claude from a general-purpose
agent into a specialized agent equipped with procedural knowledge that no model can fully possess.

### What Skills Provide

1. Specialized workflows - Multi-step procedures for specific domains
2. Tool integrations - Instructions for working with specific file formats or APIs
3. Domain expertise - Company-specific knowledge, schemas, business logic
4. Bundled resources - Scripts, references, and assets for complex and repetitive tasks

## Core Principles

### Concise is Key

The context window is a shared resource. Skills share it with everything else Claude needs:
system prompt, conversation history, other skills' metadata, and the user request.

**Default assumption: Claude is already very smart.** Only add context Claude doesn't already
have. Challenge each piece of information: "Does Claude really need this?" and "Does this
paragraph justify its token cost?"

Prefer concise examples over verbose explanations.

### Set Appropriate Degrees of Freedom

Match the level of specificity to the task's fragility and variability:

**High freedom (text-based instructions)**: Multiple approaches are valid, decisions depend
on context, or heuristics guide the approach.

**Medium freedom (pseudocode or scripts with parameters)**: A preferred pattern exists, some
variation is acceptable, or configuration affects behavior.

**Low freedom (specific scripts, few parameters)**: Operations are fragile and error-prone,
consistency is critical, or a specific sequence must be followed.

### Composability

Skills may be loaded alongside other skills. Design each skill to work independently without
assuming it is the only capability available. Avoid generic instructions that could conflict
with other skills.

### Anatomy of a Skill

Every skill consists of a required SKILL.md file and optional bundled resources:

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/          - Executable code (Python/Bash/etc.)
    ├── references/       - Documentation loaded into context as needed
    └── assets/           - Files used in output (templates, icons, fonts, etc.)
```

#### SKILL.md (required)

- **Frontmatter** (YAML): Contains `name` and `description` fields (required). The `description`
  is the primary triggering mechanism - Claude uses it to decide when to load the skill.
  Include both what the skill does and specific triggers/contexts for when to use it.
  All "when to use" information belongs in the description, not in the body.
- **Body** (Markdown): Instructions and guidance. Only loaded AFTER the skill triggers.

#### Bundled Resources (optional)

**scripts/**: Executable code for tasks requiring deterministic reliability or repeated execution.
Scripts may be executed without loading into context, saving tokens.

**references/**: Documentation loaded into context as needed to inform Claude's process.
Keeps SKILL.md lean. For files >10k words, include grep search patterns in SKILL.md.
Information should live in either SKILL.md or references, not both.

**assets/**: Files used in output (templates, images, fonts). Not loaded into context but
copied or used in the final output.

#### What Not to Include

Do NOT create extraneous documentation: README.md, INSTALLATION_GUIDE.md, CHANGELOG.md, etc.
The skill should only contain information needed for an AI agent to do the job.

### Progressive Disclosure

Skills use a three-level loading system to manage context efficiently:

1. **Metadata (name + description)** - Always in context (~100 words)
2. **SKILL.md body** - When skill triggers (<5k words)
3. **Bundled resources** - As needed by Claude

Keep SKILL.md body under 500 lines. Split content into separate files when approaching this
limit. Reference split files from SKILL.md with clear descriptions of when to read them.

**Key principle:** When a skill supports multiple variations, keep only the core workflow and
selection guidance in SKILL.md. Move variant-specific details into reference files.

Consult these reference guides based on your skill's needs:

- **Multi-step processes**: See [references/workflows.md](references/workflows.md)
- **Output formats or quality standards**: See [references/output-patterns.md](references/output-patterns.md)
- **Testing methodology**: See [references/testing.md](references/testing.md)
- **Common issues**: See [references/troubleshooting.md](references/troubleshooting.md)

## Skill Creation Process

1. Understand the skill with concrete examples
2. Plan reusable skill contents (scripts, references, assets)
3. Initialize the plugin (run init_plugin.py)
4. Edit the skill (implement resources and write SKILL.md)
5. Validate and register the plugin
6. Iterate based on real usage

Follow these steps in order, skipping only if there is a clear reason.

### Step 1: Understand the Skill with Concrete Examples

Skip only when the skill's usage patterns are already clearly understood.

To create an effective skill, understand concrete examples of how it will be used.
Ask the user questions like:

- "What functionality should this skill support?"
- "Can you give examples of how it would be used?"
- "What would a user say that should trigger this skill?"

Identify which category the skill fits:

1. **Document & Asset Creation** - Creating consistent, high-quality output
2. **Workflow Automation** - Multi-step processes with consistent methodology
3. **MCP Enhancement** - Workflow guidance that enhances MCP server tool access

### Step 2: Plan Reusable Skill Contents

Analyze each example by:

1. Considering how to execute the task from scratch
2. Identifying what scripts, references, and assets would help when executing repeatedly

Example: A `pdf-editor` skill for "rotate this PDF" → `scripts/rotate_pdf.py` avoids
rewriting the same code each time.

Example: A `big-query` skill for "how many users logged in?" → `references/schema.md`
avoids re-discovering table schemas each time.

### Step 3: Initialize the Plugin

Skip if the skill already exists and only needs iteration.

Run the init script to create a new plugin with template structure:

```bash
uv run scripts/init_plugin.py <skill-name> --path <output-directory>
```

The script creates:
- Plugin directory with `.claude-plugin/plugin.json`
- Skill directory with template `SKILL.md` and example resource directories
- Example files in `scripts/`, `references/`, and `assets/` to customize or delete

### Step 4: Edit the Skill

The skill is being created for another instance of Claude to use. Include information
that would be beneficial and non-obvious. Consider what procedural knowledge, domain-specific
details, or reusable assets would help another Claude instance execute tasks effectively.

#### Start with Reusable Contents

Begin with the reusable resources identified in Step 2. This step may require user input
(e.g., brand assets, API documentation, templates).

Test added scripts by running them to ensure correctness. If there are many similar scripts,
test a representative sample.

Delete any example files/directories not needed for the skill.

#### Update SKILL.md

**Writing Guidelines:** Always use imperative/infinitive form.

##### Frontmatter

Write the YAML frontmatter with `name` and `description`:

- `name`: Kebab-case identifier matching the directory name
- `description`: Primary triggering mechanism. Include both what the skill does and when to
  use it. Include trigger phrases. Add negative triggers to prevent over-triggering.
  - Good: "Comprehensive document creation and editing with tracked changes. Use when working
    with .docx files for creating, modifying, or reviewing documents."
  - Bad: "Helps with projects" (too vague, no triggers)
  - Bad: "Implements the Project entity model" (too technical, no user context)

##### Body

Write instructions for using the skill and its bundled resources.

### Step 5: Validate and Register

Validate the skill structure:

```bash
uv run scripts/validate_skill.py <path/to/skill-directory>
```

The validator checks:
- YAML frontmatter format and required fields
- Skill naming conventions and directory structure
- Description completeness and quality
- File organization

If distributing via a plugin marketplace, register the plugin in the marketplace's
`marketplace.json` under the `plugins` array.

### Step 6: Test and Iterate

Skills are living documents. Test before distributing, then iterate based on real usage.

**Testing approach** (see [references/testing.md](references/testing.md) for details):

1. **Triggering tests** - Verify the skill loads on relevant queries and not on unrelated ones.
   Run 10-20 test queries. Adjust description triggers as needed.
2. **Functional tests** - Verify correct outputs, successful tool calls, error handling, edge cases.
3. **Performance comparison** - Compare the same task with and without the skill.

**Iteration signals:**

- **Under-triggering**: Add keywords, trigger phrases, or file types to the description.
- **Over-triggering**: Add negative triggers, narrow the description scope.
- **Execution issues**: Improve instructions, add error handling, use scripts for fragile operations.
- **Context bloat**: Move detail to references/, keep SKILL.md under 5,000 words.

See [references/troubleshooting.md](references/troubleshooting.md) for diagnosing common issues.
