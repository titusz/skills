# Triage — route inbox tasks

purpose: move captured inbox tasks into the right projects with sensible metadata
mode: mutate

## Gather

```bash
taskmate.py projects                       # find the Inbox (usually #1) and the destinations
taskmate.py tasks --project <inbox-id>
taskmate.py labels
```

Fetch `taskmate.py task <id>` where the title alone doesn't tell you what a task is.

## Decide

For each inbox task, infer from title, description, and the visible project landscape:

- **Destination project** — match by topic; when torn between two, prefer the more specific.
    Confidence below ~80%: leave it and ask instead of guessing.
- **Priority** — only when the text signals urgency ("asap", "before Friday", a hard
    external deadline). Default: leave at 0 rather than inventing importance.
- **Due date** — only from explicit dates or clear events in the text; `+1w` is not a
    default, it's a lie with a timestamp.
- **Labels** — reuse existing labels that obviously fit. Never invent a new labeling scheme
    during triage.
- **Not actually a task** ("idea:", vague notes) → propose (don't perform) rewording into an
    actionable first step, or leave with a question.

## Act

With `--apply`, per confidently-routed task: `taskmate.py move <id> <project>`, plus any
`update`/`label` calls decided above. Companion mode: comment on moved tasks only when the
move might surprise someone ("Moved from Inbox to Website — looks like the copy rewrite
batch."). Low-confidence tasks stay put and appear in the report as questions
("#88 'call Sam' — which Sam, and about what?").

## Output

Routed (with destinations and links), left-with-questions, and a one-line inbox verdict.
Empty inbox: print `NO_ACTION` — and when interactive, congratulate them; an empty inbox on
a real board is a rare and beautiful thing.
