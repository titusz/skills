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
from pathlib import Path

import yaml


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


def parse_frontmatter(content):
    """Parse YAML frontmatter from SKILL.md content. Returns (frontmatter, match, error)."""
    # type: (str) -> tuple[dict | None, re.Match | None, str | None]
    if not content.startswith("---"):
        return None, None, "No YAML frontmatter found"

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None, None, "Invalid frontmatter format (missing closing ---)"

    try:
        frontmatter = yaml.safe_load(match.group(1))
    except yaml.YAMLError as e:
        return None, None, f"Invalid YAML in frontmatter: {e}"

    if not isinstance(frontmatter, dict):
        return None, None, "Frontmatter must be a YAML dictionary"

    return frontmatter, match, None


def validate_fields(frontmatter):
    """Check for unexpected frontmatter fields. Returns list of errors."""
    # type: (dict) -> list[str]
    unexpected = set(frontmatter.keys()) - ALLOWED_FIELDS
    if unexpected:
        return [
            f"Unexpected frontmatter field(s): {', '.join(sorted(unexpected))}. "
            f"Allowed: {', '.join(sorted(ALLOWED_FIELDS))}"
        ]
    return []


def validate_name(frontmatter, dir_name):
    """Validate the 'name' frontmatter field. Returns list of errors."""
    # type: (dict, str) -> list[str]
    if "name" not in frontmatter:
        return ["Missing 'name' in frontmatter"]

    name = frontmatter["name"]
    if not isinstance(name, str):
        return [f"Name must be a string, got {type(name).__name__}"]

    name = name.strip()
    errors = []
    if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", name):
        errors.append(
            f"Name '{name}' must be kebab-case "
            "(lowercase, digits, hyphens, no leading/trailing hyphens)"
        )
    if "--" in name:
        errors.append(f"Name '{name}' cannot contain consecutive hyphens")
    if len(name) > MAX_NAME_LENGTH:
        errors.append(f"Name too long ({len(name)} chars, max {MAX_NAME_LENGTH})")
    if name.startswith("claude") or name.startswith("anthropic"):
        errors.append(f"Name '{name}' uses a reserved prefix")
    if name != dir_name:
        errors.append(f"Name '{name}' does not match directory name '{dir_name}'")
    return errors


def validate_description(frontmatter):
    """Validate the 'description' frontmatter field. Returns (errors, warnings)."""
    # type: (dict) -> tuple[list[str], list[str]]
    if "description" not in frontmatter:
        return ["Missing 'description' in frontmatter"], []

    description = frontmatter["description"]
    if not isinstance(description, str):
        return [f"Description must be a string, got {type(description).__name__}"], []

    description = description.strip()
    errors = []
    warnings = []

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

    return errors, warnings


def validate_body(content, match_end):
    """Validate SKILL.md body content after frontmatter. Returns (errors, warnings)."""
    # type: (str, int) -> tuple[list[str], list[str]]
    body = content[match_end + 4 :].strip()

    if not body:
        return ["SKILL.md has no body content (only frontmatter)"], []

    warnings = []
    body_lines = body.splitlines()
    if len(body_lines) > MAX_BODY_LINES:
        warnings.append(
            f"Body is {len(body_lines)} lines (recommended max {MAX_BODY_LINES}). "
            "Consider moving content to references/ files."
        )
    if "TODO" in body.upper() and "[TODO" in body:
        warnings.append("Body contains TODO placeholders that should be completed")

    return [], warnings


def validate_skill(skill_path):
    """Validate a skill directory. Returns (errors, warnings)."""
    # type: (str | Path) -> tuple[list[str], list[str]]
    skill_path = Path(skill_path)

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return ["SKILL.md not found"], []

    content = skill_md.read_text(encoding="utf-8")
    frontmatter, match, parse_error = parse_frontmatter(content)
    if parse_error:
        return [parse_error], []

    errors = []
    warnings = []

    errors.extend(validate_fields(frontmatter))
    errors.extend(validate_name(frontmatter, skill_path.name))

    desc_errors, desc_warnings = validate_description(frontmatter)
    errors.extend(desc_errors)
    warnings.extend(desc_warnings)

    body_errors, body_warnings = validate_body(content, match.end())
    errors.extend(body_errors)
    warnings.extend(body_warnings)

    if (skill_path / "README.md").exists():
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
