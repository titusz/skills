#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27"]
# ///
"""TaskMate: a token-efficient Vikunja CLI for humans and AI agents.

Config resolution (first hit wins):
  1. --profile flag / TASKMATE_PROFILE env selects a named profile
  2. VIKUNJA_URL + VIKUNJA_TOKEN env vars override profile values
  3. Profiles live in ~/.config/taskmate/config.json (path override: TASKMATE_CONFIG)

Output is compact and line-oriented by default; add --json for raw API JSON.
Exit codes: 0 ok, 1 API/network error, 2 not configured (structured JSON hint on stdout).

A per-profile journal (memory/<profile>.jsonl beside the config file) gives otherwise
stateless scheduled runs cross-run memory: `journal add|recent`. Journal commands work
offline — they never touch the Vikunja API.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from functools import partial
from pathlib import Path

import httpx

NULL_DATE = "0001-01-01T00:00:00Z"
JOURNAL_KEEP_DAYS = 90
RELATION_KINDS = [
    "subtask",
    "parenttask",
    "related",
    "blocking",
    "blocked",
    "precedes",
    "follows",
    "duplicates",
    "duplicateof",
    "copiedfrom",
    "copiedto",
]


def default_config_path() -> Path:
    """Return the config file path, honoring the TASKMATE_CONFIG override."""
    override = os.environ.get("TASKMATE_CONFIG")
    return (
        Path(override)
        if override
        else Path.home() / ".config" / "taskmate" / "config.json"
    )


def load_config() -> dict:
    """Load the config file, returning an empty skeleton when absent or invalid."""
    path = default_config_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"default_profile": "default", "profiles": {}}


def save_config(cfg: dict) -> Path:
    """Write the config file with restrictive permissions where supported."""
    path = default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def journal_path(profile_name: str) -> Path:
    """Return the per-profile journal file (cross-run agent memory)."""
    return default_config_path().parent / "memory" / f"{profile_name}.jsonl"


def load_journal(path: Path) -> list[dict]:
    """Read journal entries oldest-first, skipping corrupt lines."""
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def journal_cutoff(days: int) -> str:
    """Return the UTC timestamp `days` ago, formatted for lexicographic comparison."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def die(exit_code: int, error: str, detail: str = "", hint: str = "", **extra) -> None:
    """Print a structured JSON error (so agents can self-heal) and exit."""
    payload = {"error": error}
    if detail:
        payload["detail"] = detail
    if hint:
        payload["hint"] = hint
    payload.update(extra)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


def resolve_profile_name(name: str | None) -> str:
    """Resolve the active profile name from flag, env, and config default."""
    cfg = load_config()
    return (
        name
        or os.environ.get("TASKMATE_PROFILE")
        or cfg.get("default_profile")
        or "default"
    )


def resolve_profile(name: str | None) -> tuple[str, dict]:
    """Resolve the active profile name and settings from flags, env, and config."""
    cfg = load_config()
    profile_name = resolve_profile_name(name)
    profile = dict(cfg.get("profiles", {}).get(profile_name, {}))
    if os.environ.get("VIKUNJA_URL"):
        profile["url"] = os.environ["VIKUNJA_URL"]
    env_token = os.environ.get("VIKUNJA_TOKEN") or os.environ.get("VIKUNJA_API_TOKEN")
    if env_token:
        profile["token"] = env_token
    if not profile.get("url") or not profile.get("token"):
        die(
            2,
            "not_configured",
            detail=f"Profile '{profile_name}' has no url/token in {default_config_path()} "
            "and VIKUNJA_URL/VIKUNJA_TOKEN are not set.",
            fix="uv run taskmate.py configure --url https://vikunja.example.com --token tk_xxx "
            "[--mode user|companion] [--persona NAME] [--profile NAME]",
            ask_user=[
                "Vikunja server URL (e.g. https://tasks.example.com)",
                "API token: Vikunja web UI -> User Settings -> API Tokens -> create (grant all needed permissions)",
                "Mode: 'user' (act as the human's own account) or 'companion' (agent has its own account)",
            ],
        )
    profile.setdefault("mode", "user")
    profile.setdefault("persona", "TaskMate")
    profile.setdefault("timezone", "UTC")
    return profile_name, profile


def make_client(profile: dict) -> httpx.Client:
    """Create an HTTP client bound to the profile's Vikunja API."""
    base = profile["url"].rstrip("/") + "/api/v1"
    headers = {
        "Authorization": f"Bearer {profile['token']}",
        "User-Agent": "taskmate-cli",
    }
    return httpx.Client(base_url=base, headers=headers, timeout=30)


def api(
    ctx: dict,
    method: str,
    path: str,
    body: dict | None = None,
    params: dict | None = None,
):
    """Perform one API request, translating failures into structured errors."""
    clean = {k: v for k, v in (params or {}).items() if v not in (None, "")}
    try:
        resp = ctx["client"].request(method, path, json=body, params=clean)
    except httpx.HTTPError as exc:
        die(
            1,
            "connection_failed",
            detail=str(exc),
            hint=f"Could not reach {ctx['profile']['url']}. Check the URL, network, and that Vikunja is up.",
        )
    if resp.status_code >= 400:
        hints = {
            401: "Token rejected. Create a fresh API token in Vikunja (User Settings -> API Tokens) "
            "and re-run: taskmate.py configure --token NEW_TOKEN",
            403: "Token lacks permission for this route. Recreate the token with broader permissions, "
            "or check project sharing.",
            404: "Not found. Check the ID and that the URL points at the right Vikunja instance.",
        }
        die(
            1,
            f"http_{resp.status_code}",
            detail=f"{method} {path}: {resp.text[:400]}",
            hint=hints.get(resp.status_code, ""),
        )
    if not resp.text:
        return {}
    try:
        return resp.json()
    except json.JSONDecodeError:
        die(
            1,
            "bad_response",
            detail=resp.text[:400],
            hint="Response was not JSON. Is the URL really a Vikunja instance?",
        )


def fetch_list(ctx: dict, path: str, params: dict, limit: int) -> list:
    """Fetch a paginated collection until `limit` items or the last page."""
    items: list = []
    page = 1
    per_page = min(limit, 50)
    while len(items) < limit:
        batch = api(
            ctx, "GET", path, params={**params, "per_page": per_page, "page": page}
        )
        if not isinstance(batch, list):
            return batch
        items.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return items[:limit]


def parse_due(text: str) -> str:
    """Convert friendly date input (today, tomorrow, +3d, +2w, YYYY-MM-DD) to RFC3339."""
    text = text.strip()
    if "T" in text:
        return text
    today = datetime.now(timezone.utc).date()
    match = re.fullmatch(r"\+(\d+)([dw])", text)
    if text == "today":
        target = today
    elif text == "tomorrow":
        target = today + timedelta(days=1)
    elif match:
        count = int(match.group(1))
        target = today + timedelta(days=count * (7 if match.group(2) == "w" else 1))
    else:
        try:
            target = datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            die(
                1,
                "bad_date",
                detail=f"Could not parse '{text}'.",
                hint="Use today, tomorrow, +Nd, +Nw, YYYY-MM-DD, or full RFC3339.",
            )
    return f"{target.isoformat()}T12:00:00Z"


def has_date(value: str | None) -> bool:
    """Return True when a Vikunja date field holds a real (non-null) date."""
    return bool(value) and value != NULL_DATE


def is_overdue(value: str) -> bool:
    """Return True when an RFC3339 date lies in the past."""
    normalized = re.sub(r"\.\d+", "", value).replace("Z", "+00:00")
    try:
        due = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    return due < datetime.now(timezone.utc)


def strip_html(text: str) -> str:
    """Reduce Vikunja HTML content to readable plain text."""
    text = re.sub(r"<br ?/?>", "\n", text or "")
    text = re.sub(r"</(p|li|h[1-6]|div)>\s*", "\n", text)
    text = re.sub(r"<li[^>]*>", "- ", text)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def to_html(text: str) -> str:
    """Wrap plain text as simple HTML paragraphs; pass through text starting with a known tag."""
    known_tag = r"\s*</?(p|br|div|span|ul|ol|li|strong|em|b|i|u|a|h[1-6]|code|pre|blockquote|table|img|hr)\b"
    if re.match(known_tag, text, re.IGNORECASE):
        return text
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    return "".join(
        "<p>" + html.escape(p).replace("\n", "<br>") + "</p>" for p in paragraphs
    )


def fmt_task(task: dict) -> str:
    """Format one task as a compact single line."""
    parts = [f"#{task.get('id')}", "x" if task.get("done") else "o"]
    if task.get("priority"):
        parts.append(f"!{task['priority']}")
    parts.append(task.get("title", ""))
    if has_date(task.get("due_date")):
        overdue = (
            "(OVERDUE)" if not task.get("done") and is_overdue(task["due_date"]) else ""
        )
        parts.append(f"due:{task['due_date'][:10]}{overdue}")
    if task.get("percent_done"):
        parts.append(f"{round(task['percent_done'] * 100)}%")
    assignees = [a.get("username", "?") for a in task.get("assignees") or []]
    if assignees:
        parts.append("@" + ",".join(assignees))
    labels = [lb.get("title", "?") for lb in task.get("labels") or []]
    if labels:
        parts.append("{" + ",".join(labels) + "}")
    parts.append(f"p:{task.get('project_id')}")
    return " ".join(str(p) for p in parts)


def fmt_comment(comment: dict) -> str:
    """Format one comment as a compact single line."""
    author = (comment.get("author") or {}).get("username", "?")
    return f"[{comment.get('created', '')[:10]} {author}] {strip_html(comment.get('comment') or '')}"


def fmt_journal(entry: dict) -> str:
    """Format one journal entry as a compact single line."""
    parts = [
        entry.get("ts", "")[:10],
        entry.get("source", "?"),
        entry.get("action", "?"),
    ]
    if entry.get("task") is not None:
        parts.append(f"#{entry['task']}")
    if entry.get("note"):
        parts.append(f"- {entry['note']}")
    return " ".join(str(p) for p in parts)


def print_json(obj) -> None:
    """Print an object as readable JSON."""
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def output(args, obj, lines: list[str]) -> None:
    """Print raw JSON when --json is set, otherwise the compact lines."""
    if getattr(args, "json", False):
        print_json(obj)
    else:
        print("\n".join(lines))


def find_user(ctx: dict, username: str) -> dict:
    """Resolve a username to a user object via search, requiring an exact match."""
    users = api(ctx, "GET", "/users", params={"s": username})
    for user in users or []:
        if user.get("username", "").lower() == username.lower():
            return user
    candidates = ", ".join(u.get("username", "?") for u in users or []) or "none"
    die(
        1,
        "user_not_found",
        detail=f"No exact match for '{username}' (candidates: {candidates})",
        hint="Usernames must match exactly; try `taskmate.py users --search NAME`.",
    )


def find_label(ctx: dict, title: str, create: bool = False) -> dict:
    """Resolve a label title to a label object, optionally creating it."""
    labels = fetch_list(ctx, "/labels", {"s": title}, 1000)
    for label in labels or []:
        if label.get("title", "").lower() == title.lower():
            return label
    if create:
        return api(ctx, "PUT", "/labels", body={"title": title})
    die(
        1,
        "label_not_found",
        detail=f"No label named '{title}'",
        hint="List labels with `taskmate.py labels`; `label --add` creates missing labels automatically.",
    )


def attach_labels(ctx: dict, task_id: int, titles: list[str]) -> list[str]:
    """Attach labels to a task by title, creating missing labels; return attached titles."""
    added = []
    for title in titles:
        label = find_label(ctx, title, create=True)
        api(ctx, "PUT", f"/tasks/{task_id}/labels", body={"label_id": label["id"]})
        added.append(label.get("title", title))
    return added


def attach_assignees(ctx: dict, task_id: int, usernames: list[str]) -> list[str]:
    """Assign users to a task by username; return the canonical usernames."""
    added = []
    for username in usernames:
        user = find_user(ctx, username)
        api(ctx, "PUT", f"/tasks/{task_id}/assignees", body={"user_id": user["id"]})
        added.append(user["username"])
    return added


def detach_by_name(
    ctx: dict, task_id: int, endpoint: str, items: list, key: str, names: list[str]
) -> tuple[list[str], list[str]]:
    """Delete task sub-resources matched by case-insensitive name; return (removed, missing)."""
    current = {item[key].lower(): item["id"] for item in items}
    removed, missing = [], []
    for name in names:
        item_id = current.get(name.lower())
        if item_id is None:
            missing.append(name)
            continue
        api(ctx, "DELETE", f"/tasks/{task_id}/{endpoint}/{item_id}")
        removed.append(name)
    return removed, missing


def merged_update(ctx: dict, task_id: int, changes: dict) -> dict:
    """Update a task by merging changes into its current state (POST replaces fields)."""
    current = api(ctx, "GET", f"/tasks/{task_id}")
    current.update(changes)
    return api(ctx, "POST", f"/tasks/{task_id}", body=current)


def web_url(ctx: dict, kind: str, obj_id) -> str:
    """Return the web URL for a task ("tasks") or project ("projects")."""
    return f"{ctx['profile']['url'].rstrip('/')}/{kind}/{obj_id}"


# --- commands ---------------------------------------------------------------


def cmd_configure(args, _ctx) -> None:
    """Create or update a profile, validating credentials before saving."""
    cfg = load_config()
    profile_name = args.profile or "default"
    profile = dict(cfg.get("profiles", {}).get(profile_name, {}))
    for key in ("url", "token", "mode", "persona", "timezone"):
        value = getattr(args, key)
        if value:
            profile[key] = value.rstrip("/") if key == "url" else value
    if not profile.get("url") or not profile.get("token"):
        die(
            2,
            "missing_arguments",
            detail="configure needs at least --url and --token for a new profile.",
            ask_user=[
                "Vikunja server URL",
                "API token (Vikunja: User Settings -> API Tokens)",
            ],
        )
    probe_ctx = {"client": make_client(profile), "profile": profile}
    user = api(probe_ctx, "GET", "/user")
    cfg.setdefault("profiles", {})[profile_name] = profile
    if args.make_default or len(cfg["profiles"]) == 1:
        cfg["default_profile"] = profile_name
    path = save_config(cfg)
    print(
        f"Configured profile '{profile_name}' -> {user.get('username')} (id {user.get('id')}) "
        f"@ {profile['url']} [mode: {profile.get('mode', 'user')}]"
    )
    print(f"Saved: {path}")


def cmd_doctor(args, _ctx) -> None:
    """Diagnose configuration, connectivity, and authentication."""
    cfg = load_config()
    path = default_config_path()
    print(f"config: {path} ({'exists' if path.exists() else 'MISSING'})")
    known = ", ".join(cfg.get("profiles", {})) or "none"
    print(f"profiles: {known} (default: {cfg.get('default_profile', '-')})")
    profile_name, profile = resolve_profile(args.profile)
    masked = profile["token"][:5] + "..." + profile["token"][-4:]
    print(
        f"active: {profile_name} @ {profile['url']} [mode: {profile['mode']}, "
        f"persona: {profile['persona']}, tz: {profile['timezone']}, token: {masked}]"
    )
    ctx = {"client": make_client(profile), "profile": profile}
    user = api(ctx, "GET", "/user")
    print(f"auth: OK -> {user.get('username')} (id {user.get('id')})")
    projects = fetch_list(ctx, "/projects", {}, 100)
    print(f"projects visible: {len(projects)}")
    binding = Path(".claude/taskmate.local.md")
    if binding.exists():
        print(
            f"project binding: {binding} present (read it for repo-specific defaults)"
        )
    journal = journal_path(profile_name)
    if journal.exists():
        entries = load_journal(journal)
        newest = entries[-1].get("ts", "")[:10] if entries else "-"
        print(f"journal: {journal} ({len(entries)} entries, newest {newest})")
    print("doctor: all good")


def cmd_journal_add(args, _ctx) -> None:
    """Append a journal entry, dropping entries older than the retention horizon."""
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": args.source,
        "action": args.action,
    }
    if args.task is not None:
        entry["task"] = args.task
    if args.note:
        entry["note"] = args.note
    path = journal_path(resolve_profile_name(args.profile))
    cutoff = journal_cutoff(JOURNAL_KEEP_DAYS)
    entries = [e for e in load_journal(path) if e.get("ts", "") >= cutoff]
    entries.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries),
        encoding="utf-8",
    )
    output(args, entry, [fmt_journal(entry)])


def cmd_journal_recent(args, _ctx) -> None:
    """List recent journal entries, newest first."""
    path = journal_path(resolve_profile_name(args.profile))
    cutoff = journal_cutoff(args.days)
    entries = [e for e in load_journal(path) if e.get("ts", "") >= cutoff]
    if args.source:
        entries = [e for e in entries if e.get("source") == args.source]
    if args.task is not None:
        entries = [e for e in entries if e.get("task") == args.task]
    entries = list(reversed(entries))[: args.limit]
    output(args, entries, [fmt_journal(e) for e in entries] or ["no journal entries"])


def cmd_me(args, ctx) -> None:
    """Show the authenticated user."""
    user = api(ctx, "GET", "/user")
    output(
        args,
        user,
        [
            f"{user.get('username')} (id {user.get('id')}) name:{user.get('name') or '-'}"
        ],
    )


def cmd_projects(args, ctx) -> None:
    """List projects, compact by default."""
    projects = fetch_list(ctx, "/projects", {"s": args.search}, args.limit)
    lines = []
    for p in projects:
        extra = " [archived]" if p.get("is_archived") else ""
        parent = (
            f" parent:{p['parent_project_id']}" if p.get("parent_project_id") else ""
        )
        lines.append(f"#{p.get('id')} {p.get('title')}{parent}{extra}")
    output(args, projects, lines or ["no projects"])


def cmd_tasks(args, ctx) -> None:
    """List or filter tasks; hides done tasks unless --all or --filter is given."""
    filt = args.filter or (None if args.all else "done = false")
    if args.project:
        # The API exposes projects/{id}/tasks only for creation (PUT); listing
        # is scoped through the filter grammar instead.
        filt = f"project_id = {args.project}" + (f" && ({filt})" if filt else "")
    params = {
        "s": args.search,
        "filter": filt,
        "filter_timezone": ctx["profile"]["timezone"],
        "sort_by": args.sort,
        "order_by": args.order,
    }
    tasks = fetch_list(ctx, "/tasks", params, args.limit)
    output(args, tasks, [fmt_task(t) for t in tasks] or ["no matching tasks"])


def cmd_task(args, ctx) -> None:
    """Show one task in full detail, including relations and comments."""
    task = api(ctx, "GET", f"/tasks/{args.id}")
    comments = (
        api(ctx, "GET", f"/tasks/{args.id}/comments", params={"order_by": "asc"}) or []
    )
    if args.json:
        print_json({"task": task, "comments": comments})
        return
    lines = [fmt_task(task), f"url: {web_url(ctx, 'tasks', task.get('id'))}"]
    for kind, related in (task.get("related_tasks") or {}).items():
        refs = ", ".join(f"#{r.get('id')} {r.get('title')}" for r in related)
        lines.append(f"{kind}: {refs}")
    if has_date(task.get("created")):
        lines.append(
            f"created: {task['created'][:10]}  updated: {task.get('updated', '')[:10]}"
        )
    description = strip_html(task.get("description") or "")
    if description:
        lines.append("description:\n" + description)
    lines.append(f"comments ({len(comments)}):")
    lines.extend(fmt_comment(c) for c in comments)
    print("\n".join(lines))


def cmd_add(args, ctx) -> None:
    """Create a task, then attach optional labels and assignees."""
    body = {"title": args.title}
    if args.desc:
        body["description"] = to_html(args.desc)
    if args.due:
        body["due_date"] = parse_due(args.due)
    if args.priority is not None:
        body["priority"] = args.priority
    task = api(ctx, "PUT", f"/projects/{args.project}/tasks", body=body)
    if args.label or args.assign:
        attach_labels(ctx, task["id"], args.label or [])
        attach_assignees(ctx, task["id"], args.assign or [])
        task = api(ctx, "GET", f"/tasks/{task['id']}")
    output(args, task, [fmt_task(task), f"url: {web_url(ctx, 'tasks', task['id'])}"])


def cmd_update(args, ctx) -> None:
    """Update task fields (merge semantics: unspecified fields stay untouched)."""
    changes: dict = {}
    if args.title:
        changes["title"] = args.title
    if args.desc:
        changes["description"] = to_html(args.desc)
    if args.due:
        changes["due_date"] = parse_due(args.due)
    if args.clear_due:
        changes["due_date"] = NULL_DATE
    if args.priority is not None:
        changes["priority"] = args.priority
    if args.percent is not None:
        if not 0 <= args.percent <= 100:
            die(
                1,
                "bad_percent",
                detail=f"--percent {args.percent} is out of range.",
                hint="Use 0-100.",
            )
        changes["percent_done"] = args.percent / 100
    if not changes:
        die(
            1,
            "nothing_to_update",
            hint="Pass at least one of --title/--desc/--due/--clear-due/--priority/--percent.",
        )
    task = merged_update(ctx, args.id, changes)
    output(args, task, [fmt_task(task)])


def cmd_done(args, ctx) -> None:
    """Mark one or more tasks done."""
    tasks = [merged_update(ctx, task_id, {"done": True}) for task_id in args.ids]
    output(args, tasks, [f"x #{t['id']} {t.get('title')}" for t in tasks])


def cmd_reopen(args, ctx) -> None:
    """Reopen one or more tasks."""
    tasks = [merged_update(ctx, task_id, {"done": False}) for task_id in args.ids]
    output(args, tasks, [f"o #{t['id']} {t.get('title')}" for t in tasks])


def cmd_comment(args, ctx) -> None:
    """Add a comment; companion mode signs with the persona unless --no-sign."""
    text = args.text
    if ctx["profile"]["mode"] == "companion" and not args.no_sign:
        text += f"\n\n— {ctx['profile']['persona']}"
    comment = api(
        ctx, "PUT", f"/tasks/{args.id}/comments", body={"comment": to_html(text)}
    )
    output(args, comment, [f"comment {comment.get('id')} added to #{args.id}"])


def cmd_comments(args, ctx) -> None:
    """List a task's comments oldest-first."""
    comments = (
        api(ctx, "GET", f"/tasks/{args.id}/comments", params={"order_by": "asc"}) or []
    )
    output(args, comments, [fmt_comment(c) for c in comments] or ["no comments"])


def cmd_label(args, ctx) -> None:
    """Add and/or remove labels on a task, creating missing labels on add."""
    result = {
        "added": attach_labels(ctx, args.id, args.add or []),
        "removed": [],
        "missing": [],
    }
    if args.remove:
        task = api(ctx, "GET", f"/tasks/{args.id}")
        result["removed"], result["missing"] = detach_by_name(
            ctx, args.id, "labels", task.get("labels") or [], "title", args.remove
        )
    lines = (
        [f"+{t}" for t in result["added"]]
        + [f"-{t}" for t in result["removed"]]
        + [f"?{t} (not on task)" for t in result["missing"]]
    )
    output(args, result, lines or ["no changes"])


def cmd_assign(args, ctx) -> None:
    """Assign users to a task by username."""
    added = attach_assignees(ctx, args.id, args.usernames)
    output(args, {"assigned": added}, [f"+@{u}" for u in added])


def cmd_unassign(args, ctx) -> None:
    """Remove assignees from a task by username."""
    task = api(ctx, "GET", f"/tasks/{args.id}")
    removed, missing = detach_by_name(
        ctx,
        args.id,
        "assignees",
        task.get("assignees") or [],
        "username",
        args.usernames,
    )
    lines = [f"-@{u}" for u in removed] + [f"?@{u} (not assigned)" for u in missing]
    output(args, {"removed": removed, "missing": missing}, lines or ["no changes"])


def cmd_move(args, ctx) -> None:
    """Move a task to another project."""
    task = merged_update(ctx, args.id, {"project_id": args.project})
    output(args, task, [fmt_task(task)])


def cmd_relate(args, ctx) -> None:
    """Create a relation between two tasks (e.g. subtask, blocking)."""
    relation = api(
        ctx,
        "PUT",
        f"/tasks/{args.id}/relations",
        body={"other_task_id": args.other, "relation_kind": args.kind},
    )
    output(args, relation, [f"#{args.id} {args.kind} #{args.other}"])


def cmd_unrelate(args, ctx) -> None:
    """Remove a relation between two tasks."""
    result = api(ctx, "DELETE", f"/tasks/{args.id}/relations/{args.kind}/{args.other}")
    output(args, result, [f"removed: #{args.id} {args.kind} #{args.other}"])


def cmd_new_project(args, ctx) -> None:
    """Create a project."""
    body = {"title": args.title}
    if args.description:
        body["description"] = args.description
    if args.parent:
        body["parent_project_id"] = args.parent
    project = api(ctx, "PUT", "/projects", body=body)
    url = web_url(ctx, "projects", project.get("id"))
    output(
        args, project, [f"#{project.get('id')} {project.get('title')}", f"url: {url}"]
    )


def cmd_delete(args, ctx) -> None:
    """Delete a task or project (irreversible; requires --yes)."""
    if not args.yes:
        die(
            1,
            "confirmation_required",
            hint=f"Deleting a {args.kind} is irreversible. Re-run with --yes if the human confirmed it.",
        )
    result = api(ctx, "DELETE", f"/{args.kind}s/{args.id}")
    output(
        args,
        result or {"deleted": args.kind, "id": args.id},
        [f"deleted {args.kind} #{args.id}"],
    )


def cmd_labels(args, ctx) -> None:
    """List labels."""
    labels = fetch_list(ctx, "/labels", {"s": args.search}, args.limit)
    output(
        args,
        labels,
        [f"#{lb.get('id')} {lb.get('title')}" for lb in labels] or ["no labels"],
    )


def cmd_users(args, ctx) -> None:
    """Search users on the instance."""
    users = api(ctx, "GET", "/users", params={"s": args.search}) or []
    output(
        args,
        users,
        [
            f"#{u.get('id')} {u.get('username')} {u.get('name') or ''}".rstrip()
            for u in users
        ]
        or ["no users found"],
    )


def cmd_call(args, ctx) -> None:
    """Raw API escape hatch for endpoints without a dedicated command."""
    if re.match(r"^[A-Za-z]:[/\\]", args.path):
        die(
            1,
            "mangled_path",
            detail=f"Got '{args.path}' — your shell (Git Bash/MSYS) rewrote the leading slash.",
            hint="Pass the API path without a leading slash, e.g.: call DELETE labels/16",
        )
    body = None
    if args.body:
        try:
            body = json.loads(args.body)
        except json.JSONDecodeError as exc:
            die(
                1,
                "bad_body",
                detail=str(exc),
                hint='--body must be valid JSON, e.g. --body \'{"title": "x"}\'',
            )
    params = {}
    for pair in args.query or []:
        if "=" not in pair:
            die(
                1,
                "bad_query",
                detail=f"'{pair}' is not key=value.",
                hint="Pass --query key=value (repeatable).",
            )
        key, value = pair.split("=", 1)
        params[key] = value
    print_json(
        api(
            ctx,
            args.method.upper(),
            "/" + args.path.lstrip("/"),
            body=body,
            params=params,
        )
    )


# --- CLI wiring --------------------------------------------------------------


def register_command(sub, common, name: str, func, help_text: str):
    """Register one subcommand that shares the common parent flags."""
    sp = sub.add_parser(name, help=help_text, parents=[common])
    sp.set_defaults(func=func)
    return sp


def build_parser() -> argparse.ArgumentParser:
    """Assemble the argument parser with all subcommands."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--profile", help="config profile to use")
    common.add_argument("--json", action="store_true", help="print raw API JSON")
    parser = argparse.ArgumentParser(
        prog="taskmate.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)
    add = partial(register_command, sub, common)

    sp = add("configure", cmd_configure, "create/update a connection profile")
    sp.add_argument("--url")
    sp.add_argument("--token")
    sp.add_argument("--mode", choices=["user", "companion"])
    sp.add_argument("--persona")
    sp.add_argument("--timezone")
    sp.add_argument("--make-default", action="store_true")

    add("doctor", cmd_doctor, "diagnose config, connectivity, and auth")
    add("me", cmd_me, "show the authenticated user")

    sp = add("projects", cmd_projects, "list projects")
    sp.add_argument("--search")
    sp.add_argument("--limit", type=int, default=100)

    sp = add(
        "tasks", cmd_tasks, "list/filter tasks (open tasks only, unless --all/--filter)"
    )
    sp.add_argument("--project", type=int)
    sp.add_argument("--search")
    sp.add_argument(
        "--filter", help='Vikunja filter, e.g. "priority >= 3 && due_date < now+7d"'
    )
    sp.add_argument("--all", action="store_true", help="include done tasks")
    sp.add_argument("--sort", default="updated")
    sp.add_argument("--order", default="desc", choices=["asc", "desc"])
    sp.add_argument("--limit", type=int, default=50)

    sp = add("task", cmd_task, "show one task in detail")
    sp.add_argument("id", type=int)

    sp = add("add", cmd_add, "create a task")
    sp.add_argument("project", type=int)
    sp.add_argument("title")
    sp.add_argument("--desc")
    sp.add_argument("--due", help="today | tomorrow | +3d | +2w | YYYY-MM-DD | RFC3339")
    sp.add_argument("--priority", type=int, choices=range(6))
    sp.add_argument("--label", action="append")
    sp.add_argument("--assign", action="append")

    sp = add("update", cmd_update, "update task fields (merge semantics)")
    sp.add_argument("id", type=int)
    sp.add_argument("--title")
    sp.add_argument("--desc")
    sp.add_argument("--due")
    sp.add_argument("--clear-due", action="store_true")
    sp.add_argument("--priority", type=int, choices=range(6))
    sp.add_argument("--percent", type=int, help="0-100")

    sp = add("done", cmd_done, "mark task(s) done")
    sp.add_argument("ids", type=int, nargs="+")
    sp = add("reopen", cmd_reopen, "reopen task(s)")
    sp.add_argument("ids", type=int, nargs="+")

    sp = add("comment", cmd_comment, "comment on a task")
    sp.add_argument("id", type=int)
    sp.add_argument("text")
    sp.add_argument(
        "--no-sign",
        action="store_true",
        help="skip persona signature in companion mode",
    )

    sp = add("comments", cmd_comments, "list a task's comments")
    sp.add_argument("id", type=int)

    sp = add(
        "label", cmd_label, "add/remove labels on a task (add creates missing labels)"
    )
    sp.add_argument("id", type=int)
    sp.add_argument("--add", action="append")
    sp.add_argument("--remove", action="append")

    sp = add("assign", cmd_assign, "assign users to a task")
    sp.add_argument("id", type=int)
    sp.add_argument("usernames", nargs="+")
    sp = add("unassign", cmd_unassign, "remove assignees from a task")
    sp.add_argument("id", type=int)
    sp.add_argument("usernames", nargs="+")

    sp = add("move", cmd_move, "move a task to another project")
    sp.add_argument("id", type=int)
    sp.add_argument("project", type=int)

    sp = add("relate", cmd_relate, "relate two tasks")
    sp.add_argument("id", type=int)
    sp.add_argument("kind", choices=RELATION_KINDS)
    sp.add_argument("other", type=int)
    sp = add("unrelate", cmd_unrelate, "remove a task relation")
    sp.add_argument("id", type=int)
    sp.add_argument("kind", choices=RELATION_KINDS)
    sp.add_argument("other", type=int)

    sp = add("new-project", cmd_new_project, "create a project")
    sp.add_argument("title")
    sp.add_argument("--description")
    sp.add_argument("--parent", type=int)

    sp = add("delete", cmd_delete, "delete a task or project (requires --yes)")
    sp.add_argument("kind", choices=["task", "project"])
    sp.add_argument("id", type=int)
    sp.add_argument("--yes", action="store_true")

    sp = add("labels", cmd_labels, "list labels")
    sp.add_argument("--search")
    sp.add_argument("--limit", type=int, default=100)

    sp = add("users", cmd_users, "search users on the instance")
    sp.add_argument("--search", required=True)

    sp = add("call", cmd_call, "raw API call: METHOD /path [--body JSON] [--query k=v]")
    sp.add_argument("method")
    sp.add_argument("path")
    sp.add_argument("--body")
    sp.add_argument("--query", action="append")

    jp = sub.add_parser(
        "journal", help="per-profile cross-run memory for scheduled runs"
    )
    jsub = jp.add_subparsers(dest="journal_command", required=True)
    sp = jsub.add_parser(
        "add",
        parents=[common],
        help=f"append an entry (entries older than {JOURNAL_KEEP_DAYS} days are dropped)",
    )
    sp.set_defaults(func=cmd_journal_add)
    sp.add_argument("source", help="who writes: pulse, groom, triage, unstick, ...")
    sp.add_argument(
        "action", help="short verb: nudged, applied, proposed, declined, ..."
    )
    sp.add_argument("--task", type=int, help="related task id")
    sp.add_argument("--note", help="one line of context")
    sp = jsub.add_parser("recent", parents=[common], help="list entries, newest first")
    sp.set_defaults(func=cmd_journal_recent)
    sp.add_argument("--days", type=int, default=30)
    sp.add_argument("--source", help="filter by source")
    sp.add_argument("--task", type=int, help="filter by task id")
    sp.add_argument("--limit", type=int, default=50)
    return parser


def main() -> int:
    """Entry point: parse args, resolve config lazily, dispatch."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    if args.func in (cmd_configure, cmd_doctor, cmd_journal_add, cmd_journal_recent):
        args.func(args, None)
        return 0
    _, profile = resolve_profile(args.profile)
    ctx = {"client": make_client(profile), "profile": profile}
    args.func(args, ctx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
