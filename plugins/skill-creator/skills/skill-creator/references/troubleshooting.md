# Troubleshooting

## Skill Structure Errors

**Error: "SKILL.md not found"**
- File must be named exactly `SKILL.md` (case-sensitive)

**Error: "Invalid frontmatter"**
- Missing `---` delimiters (must have opening and closing)
- Unclosed quotes in YAML values
- Invalid YAML syntax

**Error: "Invalid skill name"**
- Name has spaces or capitals: use kebab-case (`my-cool-skill`, not `My Cool Skill`)
- Name contains reserved prefix: `claude` or `anthropic` are reserved
- Name does not match directory name

## Skill Doesn't Trigger

Symptom: Skill never loads automatically.

Fixes:
- Description is too generic (`"Helps with projects"` won't match anything)
- Missing trigger phrases that users would actually say
- Missing relevant file types or tool names
- Add specific tasks and keywords to the description

## Skill Triggers Too Often

Symptom: Skill loads for unrelated queries.

Fixes:
1. Add negative triggers: `"Do NOT use for simple data exploration (use data-viz skill instead)."`
2. Narrow the description scope: `"Processes PDF legal documents for contract review"` instead of `"Processes documents"`
3. Clarify boundaries: `"Use specifically for online payment workflows, not for general financial queries."`

## Instructions Not Followed

Symptom: Skill loads but Claude doesn't follow instructions.

Common causes and fixes:

1. **Instructions too verbose** - Keep concise, use bullet points and numbered lists, move detail to references/
2. **Critical instructions buried** - Put critical instructions at the top, use `## Important` or `## Critical` headers
3. **Ambiguous language** - Replace `"Make sure to validate things properly"` with specific checks
4. **Fragile operations in prose** - For critical validations, bundle a script. Code is deterministic; language interpretation is not.

## Context Bloat

Symptom: Slow responses or degraded quality.

Fixes:
- Move detailed docs to references/ and link from SKILL.md
- Keep SKILL.md under 5,000 words
- Reduce the number of simultaneously enabled skills if using more than 20-50
- Ensure progressive disclosure is working (references loaded only when needed)
