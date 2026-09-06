#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pillow>=10.0",
# ]
# ///
"""
codex_image - drive Codex CLI's built-in image_gen tool from the command line.

Standalone helper shipped with the `imagegen` plugin. It wraps `codex exec` so an
agent never has to remember the gotchas: the prompt is piped via stdin (a bare
positional prompt hangs on non-TTY stdin), API-key variables are stripped and ChatGPT
auth is verified so billing stays on the subscription, the sandbox is read-only (Codex only calls the
tool, this script does all file handling), and outputs are harvested by thread id
from $CODEX_HOME/generated_images instead of trusting Codex to copy files.

Usage:
    uv run codex_image.py doctor
    uv run codex_image.py generate --prompt-file spec.md --name hero [options]
    uv run codex_image.py fit --fit 1920x1080 in.png -o out.jpg

`generate` prints a JSON result on stdout; progress goes to stderr.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
MAX_REFS = 5
DEFAULT_TIMEOUT = 900
DEFAULT_OUT = Path("cauldron") / "images"

GUARDRAILS = """\
You are being driven by an external tool. Follow these rules exactly:
- Use your built-in `image_gen` tool to produce the image(s) described below.
- Call `image_gen` directly. Do NOT write scripts, do NOT run shell commands,
  do NOT use curl, the OpenAI API, or any API key.
- Do NOT copy, move, rename, or save files. The caller harvests outputs itself.
- Do not ask questions; if something is ambiguous, make a sensible choice.
- Produce exactly {count} image(s): one `image_gen` call per image{variants}.
- End with a single line `DONE: <n> image(s)` or `FAILED: <reason>`.
"""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def log(message: str) -> None:
    """Print a progress line to stderr."""
    print(message, file=sys.stderr, flush=True)


def codex_home() -> Path:
    """Return the Codex home directory ($CODEX_HOME or ~/.codex)."""
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def find_codex() -> str | None:
    """Locate the codex executable on PATH (resolves .cmd shims on Windows)."""
    return shutil.which("codex")


API_KEY_VARS = ("OPENAI_API_KEY", "CODEX_API_KEY")


def codex_env() -> dict[str, str]:
    """Environment for codex with API-key variables removed (subscription billing)."""
    return {k: v for k, v in os.environ.items() if k not in API_KEY_VARS}


def kill_tree(proc: subprocess.Popen) -> None:
    """Terminate a process and all its descendants (the npm shim spawns node + codex)."""
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True
        )
    else:
        import signal

        os.killpg(proc.pid, signal.SIGKILL)


def run_codex(
    args: list[str], stdin_text: str | None, timeout: int, cwd: Path | None = None
):
    """Run `codex <args>` with stdin text and return a CompletedProcess.

    On timeout the whole process tree is killed and TimeoutExpired is raised.
    """
    exe = find_codex()
    if not exe:
        raise SystemExit(
            "codex not found on PATH - install with `npm i -g @openai/codex`"
        )
    proc = subprocess.Popen(
        [exe, *args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=codex_env(),
        cwd=str(cwd) if cwd else None,
        start_new_session=os.name != "nt",
    )
    try:
        stdout, stderr = proc.communicate(stdin_text or "", timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        try:
            proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        raise
    return subprocess.CompletedProcess([exe, *args], proc.returncode, stdout, stderr)


def chatgpt_auth() -> tuple[bool, str]:
    """Return (is ChatGPT-subscription auth, status line) from `codex login status`."""
    login = run_codex(["login", "status"], None, 60)
    text = (login.stdout + login.stderr).strip()
    first = text.splitlines()[0] if text else "unknown"
    return "chatgpt" in text.lower(), first


def slugify(text: str) -> str:
    """Lowercase, hyphenated filename-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "image"


def utc_stamp() -> str:
    """Current UTC time as RFC 3339 with second precision."""
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Style cards
# ---------------------------------------------------------------------------


def split_frontmatter(text: str) -> tuple[str, str]:
    """Split a markdown document into (frontmatter, body); frontmatter may be empty."""
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", text, re.DOTALL)
    return (match.group(1), match.group(2)) if match else ("", text)


def load_style(path: Path) -> tuple[str, list[Path]]:
    """Return (style prompt block, style reference images) for a style card.

    The card is `<dir>/<name>.md`; reference images live in `<dir>/<name>/refs/`.
    """
    if not path.is_file():
        raise SystemExit(f"style card not found: {path}")
    _, body = split_frontmatter(path.read_text(encoding="utf-8"))
    refs_dir = path.resolve().with_suffix("") / "refs"
    refs = (
        sorted(p for p in refs_dir.glob("*") if p.suffix.lower() in IMAGE_SUFFIXES)
        if refs_dir.is_dir()
        else []
    )
    return body.strip(), refs


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------


def resolve_image(path_str: str) -> Path:
    """Resolve an image path and verify it exists."""
    path = Path(path_str).expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"image not found: {path}")
    return path


def collect_refs(
    edits: list[str], refs: list[str], style_refs: list[Path]
) -> list[tuple[Path, str]]:
    """Build the ordered (path, role) list of images to pass to image_gen."""
    labelled = [
        (resolve_image(p), "edit target - preserve everything not explicitly changed")
        for p in edits
    ]
    labelled += [
        (resolve_image(p), "reference for subject, composition, or mood") for p in refs
    ]
    labelled += [
        (p, "art-style reference - match its look, do NOT copy its content")
        for p in style_refs
    ]
    if len(labelled) > MAX_REFS:
        raise SystemExit(
            f"image_gen accepts at most {MAX_REFS} reference images, got {len(labelled)}"
        )
    return labelled


def build_prompt(
    spec: str, images: list[tuple[Path, str]], style_block: str, count: int
) -> str:
    """Compose the full instruction sent to codex exec."""
    variants = ", each a distinct variant of the same spec" if count > 1 else ""
    parts = [GUARDRAILS.format(count=count, variants=variants)]
    if images:
        lines = [
            f"Image {i}: {role}\n  path: {path}"
            for i, (path, role) in enumerate(images, 1)
        ]
        parts.append(
            "Pass ALL of these local files to `image_gen` via `referenced_image_paths`, "
            "in this order, and refer to them by index in the prompt:\n"
            + "\n".join(lines)
        )
    parts.append("## Image spec\n\n" + spec.strip())
    if style_block:
        parts.append(
            "## Art style (apply consistently to the whole image)\n\n" + style_block
        )
    return "\n\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# codex exec + harvesting
# ---------------------------------------------------------------------------


def parse_events(stdout: str) -> tuple[str | None, list[str], list[str]]:
    """Extract (thread_id, agent messages, errors) from codex --json output."""
    thread_id, messages, errors = None, [], []
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type", "")
        if kind == "thread.started":
            thread_id = event.get("thread_id")
        elif kind.endswith(".failed"):
            errors.append(json.dumps(event.get("error") or event))
        elif kind == "item.completed":
            item = event.get("item") or {}
            if item.get("type") == "agent_message":
                messages.append(item.get("text", ""))
            elif item.get("type") == "error":
                errors.append(item.get("message", ""))
    return thread_id, messages, errors


def harvest(thread_id: str, started_at: float) -> list[Path]:
    """List images Codex generated for a thread, oldest first."""
    folder = codex_home() / "generated_images" / thread_id
    if not folder.is_dir():
        return []
    fresh = [
        p
        for p in folder.iterdir()
        if p.suffix.lower() in IMAGE_SUFFIXES and p.stat().st_mtime >= started_at - 5
    ]
    return sorted(fresh, key=lambda p: p.stat().st_mtime)


def next_index(target_dir: Path, slug: str) -> int:
    """First unused numeric suffix for `<slug>-<n>.<ext>` in target_dir."""
    pattern = re.compile(rf"^{re.escape(slug)}-(\d+)\.\w+$")
    used = [
        int(m.group(1)) for p in target_dir.iterdir() if (m := pattern.match(p.name))
    ]
    return max(used, default=0) + 1


def store_outputs(sources: list[Path], target_dir: Path, slug: str) -> list[Path]:
    """Copy harvested images into target_dir with stable numbered names."""
    target_dir.mkdir(parents=True, exist_ok=True)
    start = next_index(target_dir, slug)
    stored = []
    for offset, src in enumerate(sources):
        dst = target_dir / f"{slug}-{start + offset}{src.suffix.lower()}"
        shutil.copy2(src, dst)
        stored.append(dst)
    return stored


def append_sidecar(target_dir: Path, slug: str, run: dict) -> Path:
    """Append a run record to `<slug>.json` next to the images."""
    sidecar = target_dir / f"{slug}.json"
    data = (
        json.loads(sidecar.read_text(encoding="utf-8"))
        if sidecar.is_file()
        else {"slug": slug, "runs": []}
    )
    data["runs"].append(run)
    sidecar.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return sidecar


def batch_ok(produced: int, requested: int, returncode: int) -> bool:
    """A run succeeds only if codex exited cleanly and every requested image exists."""
    return returncode == 0 and produced >= requested


def codex_exec_args(reasoning: str) -> list[str]:
    """Flags for a hands-off, read-only, ephemeral codex exec run."""
    return [
        "exec",
        "--json",
        "--color",
        "never",
        "--ephemeral",
        "--skip-git-repo-check",
        "-s",
        "read-only",
        "-c",
        f"model_reasoning_effort={reasoning}",
        "-",
    ]


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------


def parse_size(text: str) -> tuple[int, int]:
    """Parse `WIDTHxHEIGHT` into a tuple."""
    match = re.fullmatch(r"(\d+)x(\d+)", text.strip().lower())
    if not match:
        raise SystemExit(f"invalid size {text!r}; expected WIDTHxHEIGHT")
    return int(match.group(1)), int(match.group(2))


def fit_image(src: Path, dst: Path, size: tuple[int, int] | None, mode: str) -> Path:
    """Resize/convert an image; `cover` crops to exact size, `contain` fits inside.

    JPEG output has no alpha channel, so transparent areas are flattened onto white.
    """
    from PIL import Image, ImageOps

    with Image.open(src) as img:
        out = img
        if size:
            out = (
                ImageOps.fit(img, size, Image.LANCZOS)
                if mode == "cover"
                else ImageOps.contain(img, size, Image.LANCZOS)
            )
        if dst.suffix.lower() in {".jpg", ".jpeg"} and out.mode != "RGB":
            rgba = out.convert("RGBA")
            out = Image.alpha_composite(
                Image.new("RGBA", rgba.size, "white"), rgba
            ).convert("RGB")
        dst.parent.mkdir(parents=True, exist_ok=True)
        out.save(dst)
    return dst


def postprocess(
    stored: list[Path], size: tuple[int, int] | None, mode: str, fmt: str | None
) -> list[Path]:
    """Apply --fit/--format to stored images in place (format change replaces the file)."""
    if not size and not fmt:
        return stored
    results = []
    for path in stored:
        dst = path.with_suffix(f".{fmt}") if fmt else path
        fit_image(path, dst, size, mode)
        if dst != path:
            path.unlink()
        results.append(dst)
    return results


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_doctor(_: argparse.Namespace) -> int:
    """Check codex install, auth mode, feature flag, and billing hazards."""
    checks: list[tuple[str, bool, str]] = []
    exe = find_codex()
    checks.append(("codex on PATH", bool(exe), exe or "not found"))
    if not exe:
        return report_doctor(checks)
    version = run_codex(["--version"], None, 60).stdout.strip()
    checks.append(("codex version", True, version))
    checks.append(("ChatGPT subscription auth", *chatgpt_auth()))
    features = run_codex(["features", "list"], None, 60).stdout
    flag = next(
        (line for line in features.splitlines() if line.startswith("image_generation")),
        "",
    )
    checks.append(
        (
            "image_generation feature",
            flag.split()[-1] == "true" if flag else False,
            flag.strip() or "flag not listed",
        )
    )
    leaked = [v for v in API_KEY_VARS if v in os.environ]
    checks.append(
        (
            "API key variables unset",
            not leaked,
            f"{', '.join(leaked)} set - stripped at runtime, but check your shell"
            if leaked
            else "ok",
        )
    )
    checks.append(
        ("generated_images dir", True, str(codex_home() / "generated_images"))
    )
    return report_doctor(checks)


def report_doctor(checks: list[tuple[str, bool, str]]) -> int:
    """Print doctor results as JSON and return the exit code."""
    ok = all(passed for _, passed, _ in checks)
    print(
        json.dumps(
            {
                "ok": ok,
                "checks": [{"name": n, "ok": p, "detail": d} for n, p, d in checks],
            },
            indent=2,
        )
    )
    return 0 if ok else 1


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate or edit images via codex exec and store them under --out/<name>/."""
    spec = (
        Path(args.prompt_file).read_text(encoding="utf-8")
        if args.prompt_file
        else args.prompt
    )
    if not spec or not spec.strip():
        raise SystemExit("provide --prompt-file or --prompt")
    style_block, style_refs = load_style(Path(args.style)) if args.style else ("", [])
    images = collect_refs(args.edit, args.ref, style_refs)
    prompt = build_prompt(spec, images, style_block, args.count)
    slug = slugify(args.name)
    target_dir = Path(args.out) / slug
    target_dir.mkdir(parents=True, exist_ok=True)
    size = parse_size(args.fit) if args.fit else None
    is_chatgpt, auth_line = chatgpt_auth()
    if not is_chatgpt:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"codex is not using ChatGPT subscription auth ({auth_line}); run `codex logout && codex login`",
                }
            )
        )
        return 1

    log(
        f"codex exec → {args.count} image(s), {len(images)} reference(s), out={target_dir}"
    )
    started = time.time()
    # A neutral cwd keeps the project's AGENTS.md and repo-level Codex config out of the turn.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as neutral_cwd:
        proc = run_codex(
            codex_exec_args(args.reasoning), prompt, args.timeout, cwd=Path(neutral_cwd)
        )
    elapsed = round(time.time() - started, 1)
    thread_id, messages, errors = parse_events(proc.stdout)
    errors = [
        e for e in errors if "shortened" not in e
    ]  # skills-budget notice is noise
    if args.keep_log:
        (target_dir / "codex-last-run.jsonl").write_text(
            proc.stdout + proc.stderr, encoding="utf-8"
        )

    sources = harvest(thread_id, started) if thread_id else []
    stored = postprocess(
        store_outputs(sources, target_dir, slug), size, args.fit_mode, args.format
    )
    if len(stored) < args.count:
        errors.append(f"requested {args.count} image(s), harvested {len(stored)}")
    run = {
        "at": utc_stamp(),
        "thread_id": thread_id,
        "elapsed_s": elapsed,
        "spec": spec.strip(),
        "style": args.style,
        "style_text": style_block,
        "images": [{"path": str(p), "role": r} for p, r in images],
        "requested": args.count,
        "outputs": [str(p) for p in stored],
        "final_message": messages[-1] if messages else "",
        "errors": errors,
        "exit_code": proc.returncode,
    }
    sidecar = append_sidecar(target_dir, slug, run)
    ok = batch_ok(len(stored), args.count, proc.returncode)
    result = {
        "ok": ok,
        "requested": args.count,
        "outputs": run["outputs"],
        "sidecar": str(sidecar),
        "thread_id": thread_id,
        "elapsed_s": elapsed,
        "final_message": run["final_message"],
        "errors": errors,
    }
    if not ok:
        result["stderr_tail"] = proc.stderr[-2000:]
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if ok else 1


def cmd_fit(args: argparse.Namespace) -> int:
    """Resize/convert an existing image."""
    src = resolve_image(args.image)
    dst = Path(args.output) if args.output else src
    fit_image(src, dst, parse_size(args.fit) if args.fit else None, args.fit_mode)
    print(json.dumps({"ok": True, "output": str(dst)}))
    return 0


def positive_int(text: str) -> int:
    """argparse type for integers >= 1."""
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


def build_parser() -> argparse.ArgumentParser:
    """Define the CLI."""
    parser = argparse.ArgumentParser(
        prog="codex_image", description=__doc__.split("\n\n")[0]
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "doctor", help="check codex install, auth mode, and feature flag"
    ).set_defaults(func=cmd_doctor)

    gen = sub.add_parser(
        "generate", help="generate or edit images via Codex's built-in image_gen"
    )
    gen.add_argument("--prompt-file", help="file containing the image spec (preferred)")
    gen.add_argument("--prompt", help="inline image spec (short prompts only)")
    gen.add_argument(
        "--name", required=True, help="slug for the output folder and filenames"
    )
    gen.add_argument(
        "--out", default=str(DEFAULT_OUT), help=f"output root (default: {DEFAULT_OUT})"
    )
    gen.add_argument(
        "--edit",
        action="append",
        default=[],
        metavar="IMAGE",
        help="edit target image (repeatable)",
    )
    gen.add_argument(
        "--ref",
        action="append",
        default=[],
        metavar="IMAGE",
        help="subject/composition reference (repeatable)",
    )
    gen.add_argument(
        "--style",
        help="path to a style card (.md); its refs/ images are attached as style references",
    )
    gen.add_argument(
        "--count",
        type=positive_int,
        default=1,
        help="number of variants (one image_gen call each)",
    )
    gen.add_argument("--fit", metavar="WxH", help="post-resize outputs to exact size")
    gen.add_argument(
        "--fit-mode",
        choices=["cover", "contain"],
        default="cover",
        help="cover = crop to exact size, contain = fit inside",
    )
    gen.add_argument(
        "--format",
        choices=["png", "jpeg", "webp"],
        help="convert outputs to this format",
    )
    gen.add_argument(
        "--reasoning",
        default="low",
        help="codex model_reasoning_effort for the run (default: low)",
    )
    gen.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"seconds before giving up (default: {DEFAULT_TIMEOUT})",
    )
    gen.add_argument(
        "--keep-log",
        action="store_true",
        help="save the raw codex JSONL next to the outputs",
    )
    gen.set_defaults(func=cmd_generate)

    fit = sub.add_parser("fit", help="resize or convert an existing image")
    fit.add_argument("image")
    fit.add_argument("--fit", metavar="WxH")
    fit.add_argument("--fit-mode", choices=["cover", "contain"], default="cover")
    fit.add_argument("-o", "--output", help="destination (default: overwrite in place)")
    fit.set_defaults(func=cmd_fit)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point: UTF-8 JSON on stdout, codex timeouts reported as JSON errors."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except subprocess.TimeoutExpired as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"codex {exc.cmd[1]} timed out after {exc.timeout:.0f}s",
                }
            )
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
