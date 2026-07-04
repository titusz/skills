# Split — break oversized tasks into subtasks

purpose: find tasks that are secretly projects and break them into 2–7 actionable subtasks
mode: mutate
max-mutations: 10

## Gather

```bash
taskmate.py tasks --filter "done = false" --limit 50
```

Fetch `taskmate.py task <id>` for candidates. Oversized smells: title contains "and"/"then"
or spans multiple deliverables; description holds a checklist or 150+ words of plan; labeled
`epic`; priority >= 3 with weeks of age but no subtasks and no progress; comments negotiating
scope. Skip tasks that already have subtask relations.

## Decide

Pick the 1–3 worst offenders (never more per run). For each, draft subtasks that are:

- **Independently completable** — each one finishable in a single sitting/session.
- **Verb-first and concrete** ("Draft outline", not "Outline stuff").
- **2–7 in number** — more means the parent needs a project, not subtasks; propose that
    instead.
- **Ordered** — if sequence matters, note it in each subtask description ("after #<prev>").
    Reserve `blocking`/`blocked` relations for hard dependencies.

The parent stays open as the tracking task; subtasks inherit its project, get priority one
notch below the parent, and split the parent's due date sensibly (earlier steps earlier).

## Act

With `--apply`, per approved parent:

```bash
taskmate.py add <project> "<subtask title>" --desc "..." [--due ...] [--priority N]
taskmate.py relate <new-id> parenttask <parent-id>
```

Then one comment on the parent summarizing the breakdown (companion mode: signed; user mode:
only when the user asked for the split). Interactive dry-run: show each proposed breakdown
and let the user prune before applying — humans often know one subtask is already obsolete.

## Output

Per parent: the subtask list with IDs and links. If nothing qualifies, print `NO_ACTION` —
do not manufacture splits; a board of small tasks is the goal, not raw material.
