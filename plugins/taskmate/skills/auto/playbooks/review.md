# Review — weekly retro

purpose: a short, warm weekly review — what shipped, what slipped, what deserves next week's focus
mode: read-only

## Gather

```bash
taskmate.py tasks --filter "done = true && doneAt > now-7d" --all --sort done_at --order desc
taskmate.py tasks --filter "dueDate < now && done = false" --sort due_date --order asc
taskmate.py tasks --filter "dueDate > now && dueDate < now+7d && done = false" --sort due_date --order asc
taskmate.py tasks --filter "priority >= 3 && done = false"
```

## Decide

Distill, don't dump:

- **Shipped**: the 3–5 completions that mattered most (impact over count — but do state the
    count; 14 closed tasks is worth saying out loud).
- **Slipped**: at most 3 overdue items, each with a one-line honest reason if visible from
    comments, framed without blame.
- **Next week**: ONE suggested focus — the item where attention buys the most. One, not three.
- **Wildcard** (optional, surprise budget): a streak ("4 weeks of closing more than opening"),
    a milestone, the oldest task finally done.

## Act

None — this playbook never mutates, `--apply` changes nothing. If the review should be
delivered somewhere (email, a comment on a designated review task), the *user* configures
that in a custom copy of this playbook; the built-in only reports to the conversation/stdout.

## Output

A compact review, kind and lightly celebratory, headed by the week's one-line story
("Shipping week: 14 closed, 2 slipped, and the invoice dragon finally slain."). Then
Shipped / Slipped / Next week's focus with task links. Scheduled runs on an inactive week
(nothing done, nothing due, nothing overdue): print `NO_ACTION`.
