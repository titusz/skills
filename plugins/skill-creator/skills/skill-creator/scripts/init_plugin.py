#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Create a new Claude Code plugin with skill template.

Usage:
    uv run init_plugin.py <plugin-name> --path <output-directory>

Examples:
    uv run init_plugin.py my-skill --path ./plugins
    uv run init_plugin.py pdf-editor --path ~/.claude/skills
"""

import sys
from pathlib import Path


SKILL_TEMPLATE = """\
---
name: {skill_name}
description: >-
  [TODO: Explain what the skill does and when to use it. Include trigger phrases
  and specific scenarios. This is the primary triggering mechanism.]
---

# {skill_title}

[TODO: 1-2 sentences explaining what this skill enables]

## [TODO: First main section based on chosen structure]

[TODO: Add content. Common structures:
- **Workflow-Based**: Step-by-step procedures (## Step 1 -> ## Step 2)
- **Task-Based**: Different operations (## Merge PDFs -> ## Split PDFs)
- **Reference/Guidelines**: Standards or specs (## Guidelines -> ## Specs)
- **Capabilities-Based**: Interrelated features (### 1. Feature -> ### 2. Feature)

Delete this guidance section when done.]

## Resources

### scripts/
Executable code that can be run directly to perform specific operations.
Delete or replace `example.py` with actual scripts.

### references/
Documentation loaded into context as needed. Delete or replace
`example_reference.md` with actual reference material.

### assets/
Files used in output (templates, images, fonts). Delete or replace
`example_asset.txt` with actual assets.

**Delete any unneeded directories.** Not every skill requires all three.
"""

PLUGIN_JSON_TEMPLATE = """\
{{
  "name": "{plugin_name}",
  "description": "[TODO: Brief plugin description]",
  "version": "0.1.0"
}}
"""

EXAMPLE_SCRIPT = """\
#!/usr/bin/env python3
\"\"\"Example helper script for {skill_name}. Replace or delete.\"\"\"


def main():
    print("Example script for {skill_name}")


if __name__ == "__main__":
    main()
"""

EXAMPLE_REFERENCE = """\
# Reference Documentation

Replace this placeholder with actual reference material for the skill.

Reference docs are ideal for:
- API documentation
- Detailed workflow guides
- Database schemas
- Domain knowledge that's too lengthy for SKILL.md
"""

EXAMPLE_ASSET = """\
This placeholder represents where asset files would be stored.
Replace with actual files (templates, images, fonts, etc.) or delete.
"""


def title_case(name):
    """Convert kebab-case name to Title Case."""
    return " ".join(word.capitalize() for word in name.split("-"))


def init_plugin(plugin_name, path):
    """Create a new plugin directory with skill template."""
    plugin_dir = Path(path).resolve() / plugin_name

    if plugin_dir.exists():
        print(f"Error: Directory already exists: {plugin_dir}", file=sys.stderr)
        return None

    try:
        # Plugin manifest
        manifest_dir = plugin_dir / ".claude-plugin"
        manifest_dir.mkdir(parents=True)
        (manifest_dir / "plugin.json").write_text(
            PLUGIN_JSON_TEMPLATE.format(plugin_name=plugin_name)
        )

        # Skill directory
        skill_dir = plugin_dir / "skills" / plugin_name
        skill_dir.mkdir(parents=True)

        skill_title = title_case(plugin_name)
        (skill_dir / "SKILL.md").write_text(
            SKILL_TEMPLATE.format(skill_name=plugin_name, skill_title=skill_title)
        )

        # Example resource directories
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "example.py").write_text(
            EXAMPLE_SCRIPT.format(skill_name=plugin_name)
        )

        references_dir = skill_dir / "references"
        references_dir.mkdir()
        (references_dir / "example_reference.md").write_text(EXAMPLE_REFERENCE)

        assets_dir = skill_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "example_asset.txt").write_text(EXAMPLE_ASSET)

    except Exception as e:
        print(f"Error creating plugin: {e}", file=sys.stderr)
        return None

    print(f"Created plugin at {plugin_dir}")
    print("  .claude-plugin/plugin.json")
    print(f"  skills/{plugin_name}/SKILL.md")
    print(f"  skills/{plugin_name}/scripts/example.py")
    print(f"  skills/{plugin_name}/references/example_reference.md")
    print(f"  skills/{plugin_name}/assets/example_asset.txt")
    print()
    print("Next steps:")
    print("1. Edit SKILL.md to complete the TODO items")
    print("2. Edit .claude-plugin/plugin.json description")
    print("3. Replace or delete example files in scripts/, references/, assets/")
    return plugin_dir


def main():
    if len(sys.argv) < 4 or sys.argv[2] != "--path":
        print("Usage: uv run init_plugin.py <plugin-name> --path <output-directory>")
        print()
        print("Examples:")
        print("  uv run init_plugin.py my-skill --path ./plugins")
        print("  uv run init_plugin.py pdf-editor --path /some/path")
        sys.exit(1)

    plugin_name = sys.argv[1]
    path = sys.argv[3]

    result = init_plugin(plugin_name, path)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
