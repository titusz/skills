# Groom — backlog hygiene

purpose: keep the backlog honest — surface overdue and stale tasks, fix missing metadata, flag zombies
mode: mutate

## Gather

```bash
taskmate.py tasks --filter "dueDate < now && done = false" --sort due_date --order asc
taskmate.py tasks --filter "updated < now-30d && done = false" --sort updated --order asc
taskmate.py tasks --filter "priority >= 3 && done = false"
```

For each candidate that survives *Decide*, fetch `taskmate.py task <id>` — comments often
reveal a task is actually done, blocked, or superseded.

## Decide

- **Overdue + still relevant** → propose a realistic new due date (or clearing the date if it
    was decorative) and, if untouched for 2+ weeks, a priority bump for visibility.
- **Overdue + comments show it's done** → propose marking done (quote the evidence).
- **Stale 30–60 days, priority >= 2** → propose label `stale` so humans see the rot.
- **Stale 60+ days, priority \<= 1** → zombie: propose (to humans only) closing or archiving —
    never delete, never mark done on your own judgment.
- **High priority but no due date** → propose one inferred from context, or explicitly
    "needs human date".
- **Obvious duplicates** (same intent, similar titles) → propose relating them
    (`relate <a> duplicates <b>`) and letting a human pick the survivor.

Skip tasks a human touched in the last 48h — they're being actively managed.

## Act

With `--apply`: due-date changes, `stale` labels, duplicate relations, done-marking **only**
where a human's own comment states completion. Everything else (zombie closures, priority
changes on others' tasks in companion mode) remains a proposal. Companion mode: one summary
comment on each changed task ("Groomed: moved due date to Fri — it was 3 weeks overdue with
no activity.").

## Output

Grouped report: `changed` (verified), `proposed` (needs human), `healthy` (one-line count).
End with the single most concerning finding, kindly put. Print `NO_ACTION` if the board is
clean — and say so with mild astonishment when interactive; a clean backlog deserves respect.
