#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Validate a Claude Code skill directory.

Usage:
    uv run validate_skill.py <skill-directory>
"""

import argparse
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

MIN_DESCRIPTION_LENGTH = 50
MAX_DESCRIPTION_LENGTH = 1024
MAX_NAME_LENGTH = 64
MAX_BODY_LINES = 500


def validate_skill(skill_path):
    """Validate a skill directory. Returns (errors, warnings)."""
    skill_path = Path(skill_path)
    errors = []
    warnings = []

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return ["SKILL.md not found"], []

    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return ["No YAML frontmatter found"], []

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return ["Invalid frontmatter format (missing closing ---)"], []

    try:
        frontmatter = yaml.safe_load(match.group(1))
        if not isinstance(frontmatter, dict):
            return ["Frontmatter must be a YAML dictionary"], []
    except yaml.YAMLError as e:
        return [f"Invalid YAML in frontmatter: {e}"], []

    # Check for unexpected fields
    unexpected = set(frontmatter.keys()) - ALLOWED_FIELDS
    if unexpected:
        errors.append(
            f"Unexpected frontmatter field(s): {', '.join(sorted(unexpected))}. "
            f"Allowed: {', '.join(sorted(ALLOWED_FIELDS))}"
        )

    # Validate name
    if "name" not in frontmatter:
        errors.append("Missing 'name' in frontmatter")
    else:
        name = frontmatter["name"]
        if not isinstance(name, str):
            errors.append(f"Name must be a string, got {type(name).__name__}")
        else:
            name = name.strip()
            if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", name):
                errors.append(
                    f"Name '{name}' must be kebab-case "
                    "(lowercase, digits, hyphens, no leading/trailing hyphens)"
                )
            if "--" in name:
                errors.append(f"Name '{name}' cannot contain consecutive hyphens")
            if len(name) > MAX_NAME_LENGTH:
                errors.append(
                    f"Name too long ({len(name)} chars, max {MAX_NAME_LENGTH})"
                )
            if name.startswith("claude") or name.startswith("anthropic"):
                errors.append(f"Name '{name}' uses a reserved prefix")
            if name != skill_path.name:
                errors.append(
                    f"Name '{name}' does not match directory name '{skill_path.name}'"
                )

    # Validate description
    if "description" not in frontmatter:
        errors.append("Missing 'description' in frontmatter")
    else:
        description = frontmatter["description"]
        if not isinstance(description, str):
            errors.append(
                f"Description must be a string, got {type(description).__name__}"
            )
        else:
            description = description.strip()
            if not description:
                errors.append("Description is empty")
            elif len(description) < MIN_DESCRIPTION_LENGTH:
                warnings.append(
                    f"Description is short ({len(description)} chars). "
                    f"Descriptions under {MIN_DESCRIPTION_LENGTH} chars often lack "
                    "trigger phrases needed for reliable skill activation."
                )
            if "<" in description or ">" in description:
                errors.append("Description cannot contain angle brackets")
            if len(description) > MAX_DESCRIPTION_LENGTH:
                errors.append(
                    f"Description too long ({len(description)} chars, max {MAX_DESCRIPTION_LENGTH})"
                )
            if "TODO" in description.upper():
                errors.append("Description contains TODO placeholder")

    # Validate body content
    body = content[match.end() + 4 :]  # skip past closing --- and newline
    body_stripped = body.strip()

    if not body_stripped:
        errors.append("SKILL.md has no body content (only frontmatter)")
    else:
        body_lines = body_stripped.splitlines()
        if len(body_lines) > MAX_BODY_LINES:
            warnings.append(
                f"Body is {len(body_lines)} lines (recommended max {MAX_BODY_LINES}). "
                "Consider moving content to references/ files."
            )
        if "TODO" in body_stripped.upper() and "[TODO" in body_stripped:
            warnings.append("Body contains TODO placeholders that should be completed")

    # Check for files that should not be in the skill directory
    readme = skill_path / "README.md"
    if readme.exists():
        errors.append("Skill folder should not contain README.md")

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(
        description="Validate a Claude Code skill directory"
    )
    parser.add_argument(
        "skill_directory", help="Path to the skill directory to validate"
    )
    args = parser.parse_args()

    errors, warnings = validate_skill(args.skill_directory)

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if not errors and not warnings:
        print("Skill is valid")
    elif not errors:
        print(f"Skill is valid with {len(warnings)} warning(s)")

    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
