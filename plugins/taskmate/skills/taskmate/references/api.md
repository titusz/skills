# Vikunja API reference for TaskMate

The bundled CLI covers the common 90%. This file is for the rest: raw endpoints via
`taskmate.py call METHOD path`, the filter language, and gotchas that cost real debugging
time. API base is `<server>/api/v1`; auth header `Authorization: Bearer <token>`.
Interactive docs live at `<server>/api/v1/docs` (OpenAPI spec: `<server>/api/v1/docs.json`).

## Endpoint map

| Purpose                       | Method              | Endpoint                                                                      |
| ----------------------------- | ------------------- | ----------------------------------------------------------------------------- |
| Current user                  | GET                 | `user`                                                                        |
| Search users                  | GET                 | `users?s=<query>`                                                             |
| List projects                 | GET                 | `projects`                                                                    |
| Create project                | PUT                 | `projects`                                                                    |
| Get / update / delete project | GET / POST / DELETE | `projects/{id}`                                                               |
| Share project with user       | PUT                 | `projects/{id}/users` body `{"user_id": N, "right": 1}`                       |
| Project members               | GET                 | `projects/{id}/projectusers`                                                  |
| List all accessible tasks     | GET                 | `tasks` (scope to a project via filter `project_id = N`)                      |
| Tasks in a project view       | GET                 | `projects/{id}/views/{viewID}/tasks`                                          |
| Create task                   | PUT                 | `projects/{id}/tasks`                                                         |
| Get / update / delete task    | GET / POST / DELETE | `tasks/{id}`                                                                  |
| Comments                      | GET / PUT           | `tasks/{id}/comments`                                                         |
| Update / delete comment       | POST / DELETE       | `tasks/{id}/comments/{commentID}`                                             |
| Assignees                     | PUT / DELETE        | `tasks/{id}/assignees` / `tasks/{id}/assignees/{userID}`                      |
| Labels on task                | PUT / DELETE        | `tasks/{id}/labels` / `tasks/{id}/labels/{labelID}`                           |
| All labels                    | GET / PUT           | `labels`                                                                      |
| Relations                     | PUT / DELETE        | `tasks/{id}/relations` / `tasks/{id}/relations/{kind}/{otherID}`              |
| Attachments                   | GET                 | `tasks/{id}/attachments`                                                      |
| Teams                         | GET                 | `teams`                                                                       |
| Notifications                 | GET                 | `notifications`                                                               |
| Kanban buckets                | GET                 | `projects/{id}/views/{viewID}/buckets` (view IDs from project detail `views`) |

Sharing rights: `0` read, `1` read+write, `2` admin.

## Filter language

Pass via `tasks --filter "..."`. Fields: `done`, `priority`, `percent_done`, `due_date`,
`start_date`, `end_date`, `done_at`, `assignees`, `labels`, `project`, `reminders`,
`created`, `updated`. Operators: `=` `!=` `>` `>=` `<` `<=` `like` (with `%` wildcards) `in`.
Combine with `&&` and `||`, group with parentheses.

Date values accept RFC3339 or relative math: `now`, `now+7d`, `now-1w`, `now/w` (start of
week), units `s m h d w M y`. Examples that work:

```text
done = false && priority >= 3
due_date < now && done = false                  # overdue
updated < now-30d && done = false               # stale
assignees in titusz, kira && due_date < now+7d  # someone's week
labels in okr && percent_done < 0.5
project in 6, 7, 8                              # roll-up across projects
```

Notes: `assignees` matches usernames, `labels` matches label titles (both accept
comma-separated lists with `in`). The CLI sends `filter_timezone` from the profile so
relative dates resolve in the user's timezone. The CLI defaults to `done = false` when you
pass no filter; pass `--all` or your own `--filter` to override.

## Gotchas (each of these cost someone an afternoon)

- **PUT creates, POST updates** — inverted from typical REST. The CLI hides this; remember it
    for `call`.
- **Filter fields are snake_case at the API** (`due_date`, `done_at`, `percent_done`). The
    Vikunja web UI and its docs show camelCase (`dueDate`) because the frontend translates
    before sending — raw API calls and `--filter` strings must use snake_case or the server
    rejects the filter. There is also no `GET projects/{id}/tasks` (that route only creates);
    project-scoped listing is `filter=project_id = N` or a view route.
- **Task update replaces the whole object.** `POST tasks/{id}` with a partial body zeroes
    omitted fields (due date vanishes, title blanks). Always GET, merge, POST — the CLI's
    `update`/`done`/`move` do this automatically. Never hand-craft a partial update via `call`.
- **`percent_done` is 0..1**, not 0..100. The CLI's `--percent` takes 0–100 and converts.
- **Null dates are `0001-01-01T00:00:00Z`**, not `null`. Sending JSON `null` is ignored by the
    server-side unmarshal; to clear a due date the CLI sends the sentinel (`update --clear-due`).
- **Descriptions and comments are HTML** (TipTap editor). Markdown pasted in shows as literal
    `**stars**`. The CLI converts plain text to `<p>`/`<br>` HTML on write and strips HTML on
    display. Keep formatting minimal: short plain labels like `Objective:` outperform bold/tables.
- **API tokens are shown once** at creation and cannot be re-read. If a token is lost, create
    a new one; don't delete a working token casually. Tokens also carry per-route permissions —
    a `403` on one route while others work means the token was created with narrow scopes.
- **Bulk label endpoint (`POST tasks/{id}/labels/bulk`) has returned 500s** on real instances.
    Attach labels one at a time (the CLI does).
- **Assignees must have project access.** Assigning fails silently or 403s until the project
    is shared with that user (`PUT projects/{id}/users`). In companion mode this applies to the
    companion account itself: someone must share the project with it first.
- **Pagination caps at 50 per page** on default instances; the CLI auto-paginates up to
    `--limit`. Don't assume one response is everything.
- **Git Bash / MSYS mangles leading-slash arguments** (`/labels/16` becomes
    `C:/Program Files/Git/labels/16`). `call` therefore takes paths without the leading slash
    and detects the mangled form with a helpful error.
- **Rendering side effects of native fields**: nonzero priority renders loud exclamation
    marks, near due dates render "Due in ..." warnings, nonzero `percent_done` renders progress
    bars. For clean overview boards some teams prefer short labels (`P1`, `Q3`) over native
    fields — follow the conventions already visible on the board you're working.
- **Web links**: task `<server>/tasks/{id}`, project `<server>/projects/{id}`. Include them in
    reports; humans click, agents re-fetch.
