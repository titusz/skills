# Celebrate — kudos on completed work

purpose: leave short, sincere, non-repetitive kudos comments on meaningful completions
mode: mutate
max-mutations: 3

Companion mode only — kudos must visibly come from the companion account. In user mode,
print `NO_ACTION` (self-congratulation via someone's own account is deeply weird).

## Gather

```bash
taskmate.py tasks --filter "done = true && done_at > now-7d" --all --sort done_at --order desc
```

For each candidate, `taskmate.py task <id>` to check existing comments.

## Decide

Celebrate at most 3 tasks per run. Worth celebrating: high priority finally done; open a long
time (age > 60 days) and finished anyway; visibly hard (long comment trail, multiple people);
or completing it unblocked others (`blocking` relations). **Skip**: tasks where you already
left a kudos comment after completion (idempotence — check the comment trail for your
persona), trivial two-minute tasks (congratulating someone for buying milk is patronizing),
and tasks completed by you yourself.

## Act

With `--apply`: one comment per chosen task — one or two sentences, specific to what was
done, sincere first and witty second, never generic. Vary phrasing across tasks and weeks;
if your last kudos said "landed", this one doesn't. Good shapes:

> That one sat in the backlog for four months and you closed it in a day once it mattered.
> Respect.

> 12 comments, 3 scope changes, done anyway. This was the hard kind.

## Output

List of celebrated tasks with links, or `NO_ACTION` when nothing cleared the bar. Never
lower the bar — kudos inflation is how celebration becomes noise.
