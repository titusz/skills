#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Validate a Claude Code skill directory.

Usage:
    uv run validate_skill.py <skill-directory>
"""

import re
import sys

import yaml
from pathlib import Path


# Claude Code supported SKILL.md frontmatter fields
ALLOWED_FIELDS = {
    "name",
    "description",
    "argument-hint",
    "disable-model-invocation",
    "user-invocable",
    "allowed-tools",
    "model",
    "context",
    "agent",
    "hooks",
}


def validate_skill(skill_path):
    """Validate a skill directory. Returns (valid, message)."""
    skill_path = Path(skill_path)

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found"

    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return False, "No YAML frontmatter found"

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    try:
        frontmatter = yaml.safe_load(match.group(1))
        if not isinstance(frontmatter, dict):
            return False, "Frontmatter must be a YAML dictionary"
    except yaml.YAMLError as e:
        return False, f"Invalid YAML in frontmatter: {e}"

    unexpected = set(frontmatter.keys()) - ALLOWED_FIELDS
    if unexpected:
        return False, (
            f"Unexpected frontmatter field(s): {', '.join(sorted(unexpected))}. "
            f"Allowed: {', '.join(sorted(ALLOWED_FIELDS))}"
        )

    if "name" not in frontmatter:
        return False, "Missing 'name' in frontmatter"
    if "description" not in frontmatter:
        return False, "Missing 'description' in frontmatter"

    name = frontmatter["name"]
    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name).__name__}"
    name = name.strip()

    if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", name):
        return False, f"Name '{name}' must be kebab-case (lowercase, digits, hyphens, no leading/trailing hyphens)"
    if "--" in name:
        return False, f"Name '{name}' cannot contain consecutive hyphens"
    if len(name) > 64:
        return False, f"Name too long ({len(name)} chars, max 64)"
    if name.startswith("claude") or name.startswith("anthropic"):
        return False, f"Name '{name}' uses a reserved prefix"
    if name != skill_path.name:
        return False, f"Name '{name}' does not match directory name '{skill_path.name}'"

    description = frontmatter["description"]
    if not isinstance(description, str):
        return False, f"Description must be a string, got {type(description).__name__}"
    description = description.strip()

    if not description:
        return False, "Description is empty"
    if "<" in description or ">" in description:
        return False, "Description cannot contain angle brackets"
    if len(description) > 1024:
        return False, f"Description too long ({len(description)} chars, max 1024)"
    if "TODO" in description.upper():
        return False, "Description contains TODO placeholder"

    readme = skill_path / "README.md"
    if readme.exists():
        return False, "Skill folder should not contain README.md"

    return True, "Skill is valid"


def main():
    if len(sys.argv) != 2:
        print("Usage: uv run validate_skill.py <skill-directory>")
        sys.exit(1)

    valid, message = validate_skill(sys.argv[1])
    print(message)
    sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()
