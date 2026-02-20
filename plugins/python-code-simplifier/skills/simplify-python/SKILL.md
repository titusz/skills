---
name: simplify-python
description: >-
  Simplify Python code for clarity and maintainability. Use when users say "simplify",
  "simplify this code", "clean up Python", "refine this code", "make this simpler",
  "simplify recent changes". Delegates to the python-code-simplifier agent.
user-invocable: true
argument-hint: '[file, directory, or scope]'
allowed-tools:
  - Task
---

# Simplify Python Code

Delegate to the `python-code-simplifier:python-code-simplifier` agent to simplify Python code.

## Determine Scope

Parse `$ARGUMENTS` to determine what to simplify:

- **File path** (e.g., `src/main.py`): Simplify that specific file
- **Directory** (e.g., `src/`): Simplify Python files in that directory
- **Description** (e.g., "the auth module"): Pass as context to the agent
- **Empty**: Simplify recently modified Python code (agent uses `git diff`)

## Dispatch

Launch a Task with `subagent_type` set to `python-code-simplifier:python-code-simplifier` and a prompt describing the scope:

- If a specific file or directory was given, instruct the agent to focus on that path
- If a description was given, pass it as the scope context
- If no arguments, instruct the agent to find and simplify recent changes
