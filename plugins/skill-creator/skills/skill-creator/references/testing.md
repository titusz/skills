# Testing Methodology

Choose the testing approach that matches the skill's visibility and quality requirements.

## 1. Triggering Tests

Goal: Ensure the skill loads at the right times.

Prepare two sets of test queries:

**Should trigger** (10+ queries):
- Obvious requests matching the skill's purpose
- Paraphrased versions of the same requests
- Requests using different terminology for the same task

**Should NOT trigger** (5+ queries):
- Unrelated topics
- Adjacent but out-of-scope tasks
- Tasks that belong to a different skill

Example for a "project-setup" skill:

```
Should trigger:
- "Help me set up a new ProjectHub workspace"
- "I need to create a project in ProjectHub"
- "Initialize a ProjectHub project for Q4 planning"

Should NOT trigger:
- "What's the weather in San Francisco?"
- "Help me write Python code"
- "Create a spreadsheet"
```

**Debugging tip:** Ask Claude "When would you use the [skill-name] skill?" Claude will quote the description back. Adjust based on what is missing.

## 2. Functional Tests

Goal: Verify the skill produces correct outputs.

Test cases to cover:
- Valid outputs generated for standard inputs
- API/MCP calls succeed
- Error handling works for known failure modes
- Edge cases (empty input, large input, unusual formats)

Example test structure:

```
Test: Create project with 5 tasks
Given: Project name "Q4 Planning", 5 task descriptions
When: Skill executes workflow
Then:
- Project created successfully
- 5 tasks created with correct properties
- All tasks linked to project
- No API errors
```

Run the same request 3-5 times and compare outputs for structural consistency.

## 3. Performance Comparison

Goal: Prove the skill improves results vs. baseline.

Compare the same task with and without the skill enabled:

| Metric | Without skill | With skill |
|--------|--------------|------------|
| Back-and-forth messages | Count | Count |
| Failed API calls | Count | Count |
| Tokens consumed | Estimate | Estimate |
| User corrections needed | Count | Count |

## Pro Tip

Iterate on a single challenging task until Claude succeeds, then extract the winning approach into the skill. This leverages in-context learning and provides faster signal than broad testing. Once the foundation works, expand to multiple test cases for coverage.
