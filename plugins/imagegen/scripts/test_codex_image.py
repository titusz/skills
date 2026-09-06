#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pillow>=10.0",
#   "pytest>=8.0",
# ]
# ///
"""
Tests for codex_image.py — the pure parts (prompt assembly, event parsing,
harvesting, storage, post-processing). Nothing here calls codex.

Run:  uv run test_codex_image.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import codex_image as ci  # noqa: E402


def make_png(path: Path, size=(40, 20), mode="RGBA") -> Path:
    """Write a small solid image for tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new(mode, size, (200, 30, 30, 255) if mode == "RGBA" else (200, 30, 30)).save(
        path
    )
    return path


def test_slugify_normalizes():
    assert ci.slugify("Hero Banner v2!") == "hero-banner-v2"
    assert ci.slugify("///") == "image"


def test_split_frontmatter_handles_both_forms():
    assert ci.split_frontmatter("plain body") == ("", "plain body")
    fm, body = ci.split_frontmatter("---\nname: x\n---\nStyle/medium: ink\n")
    assert fm == "name: x"
    assert body == "Style/medium: ink\n"


def test_load_style_reads_body_and_absolute_refs(tmp_path, monkeypatch):
    card = tmp_path / "styles" / "ink.md"
    card.parent.mkdir()
    card.write_text(
        "---\nname: ink\n---\nStyle/medium: ink wash\nAvoid: neon\n", encoding="utf-8"
    )
    ref = make_png(tmp_path / "styles" / "ink" / "refs" / "a.png")
    (tmp_path / "styles" / "ink" / "refs" / "notes.txt").write_text("skip me")
    monkeypatch.chdir(tmp_path)
    block, refs = ci.load_style(
        Path("styles/ink.md")
    )  # relative, as the skill invokes it
    assert block == "Style/medium: ink wash\nAvoid: neon"
    assert refs == [ref.resolve()]
    assert refs[0].is_absolute()


def test_collect_refs_labels_roles_and_caps_at_five(tmp_path):
    imgs = [make_png(tmp_path / f"{i}.png") for i in range(6)]
    labelled = ci.collect_refs([str(imgs[0])], [str(imgs[1])], [imgs[2]])
    assert [p for p, _ in labelled] == imgs[:3]
    assert "edit target" in labelled[0][1]
    assert "art-style" in labelled[2][1]
    with pytest.raises(SystemExit, match="at most 5"):
        ci.collect_refs([], [str(p) for p in imgs], [])


def test_collect_refs_rejects_missing_file(tmp_path):
    with pytest.raises(SystemExit, match="image not found"):
        ci.collect_refs([], [str(tmp_path / "nope.png")], [])


def test_build_prompt_contains_guardrails_spec_refs_and_style(tmp_path):
    ref = make_png(tmp_path / "ref.png")
    prompt = ci.build_prompt(
        "Subject: a crane", [(ref, "edit target")], "Style/medium: origami", 2
    )
    assert "built-in `image_gen`" in prompt
    assert "Do NOT copy, move" in prompt
    assert "exactly 2 image(s)" in prompt and "distinct variant" in prompt
    assert f"Image 1: edit target\n  path: {ref}" in prompt
    assert "referenced_image_paths" in prompt
    assert "## Image spec\n\nSubject: a crane" in prompt
    assert "## Art style" in prompt and "origami" in prompt


def test_build_prompt_without_refs_or_style():
    prompt = ci.build_prompt("Subject: x", [], "", 1)
    assert "referenced_image_paths" not in prompt
    assert "## Art style" not in prompt
    assert "distinct variant" not in prompt


def test_parse_events_extracts_thread_messages_errors():
    lines = [
        "Reading additional input from stdin...",
        json.dumps({"type": "thread.started", "thread_id": "t-1"}),
        json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "type": "error",
                    "message": "Skill descriptions were shortened",
                },
            }
        ),
        json.dumps(
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "DONE: 1 image(s)"},
            }
        ),
        json.dumps({"type": "turn.failed", "error": {"message": "boom"}}),
        "not json {",
    ]
    thread_id, messages, errors = ci.parse_events("\n".join(lines))
    assert thread_id == "t-1"
    assert messages == ["DONE: 1 image(s)"]
    assert errors == [
        "Skill descriptions were shortened",
        json.dumps({"message": "boom"}),
    ]


def test_harvest_filters_by_thread_and_freshness(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    folder = tmp_path / "generated_images" / "t-1"
    old = make_png(folder / "old.png")
    new = make_png(folder / "new.png")
    (folder / "ignore.txt").write_text("x")
    stale = time.time() - 3600
    import os

    os.utime(old, (stale, stale))
    assert ci.harvest("t-1", time.time() - 60) == [new]
    assert ci.harvest("missing", 0) == []


def test_store_outputs_numbers_without_overwriting(tmp_path):
    src = make_png(tmp_path / "src" / "exec-abc.png")
    target = tmp_path / "out" / "crane"
    first = ci.store_outputs([src], target, "crane")
    second = ci.store_outputs([src, src], target, "crane")
    assert [p.name for p in first] == ["crane-1.png"]
    assert [p.name for p in second] == ["crane-2.png", "crane-3.png"]
    assert all(p.is_file() for p in first + second)


def test_append_sidecar_accumulates_runs(tmp_path):
    sidecar = ci.append_sidecar(tmp_path, "crane", {"at": "t1"})
    ci.append_sidecar(tmp_path, "crane", {"at": "t2"})
    data = json.loads(sidecar.read_text(encoding="utf-8"))
    assert data["slug"] == "crane"
    assert [r["at"] for r in data["runs"]] == ["t1", "t2"]


def test_parse_size():
    assert ci.parse_size("1920x1080") == (1920, 1080)
    with pytest.raises(SystemExit, match="invalid size"):
        ci.parse_size("big")


def test_fit_cover_contain_and_jpeg_conversion(tmp_path):
    src = make_png(tmp_path / "src.png", size=(400, 200))
    cover = ci.fit_image(src, tmp_path / "cover.png", (100, 100), "cover")
    contain = ci.fit_image(src, tmp_path / "contain.png", (100, 100), "contain")
    jpeg = ci.fit_image(src, tmp_path / "out.jpg", None, "cover")
    with Image.open(cover) as im:
        assert im.size == (100, 100)
    with Image.open(contain) as im:
        assert im.size == (100, 50)
    with Image.open(jpeg) as im:
        assert im.mode == "RGB" and im.size == (400, 200)


def test_fit_flattens_transparency_onto_white_for_jpeg(tmp_path):
    src = tmp_path / "clear.png"
    Image.new("RGBA", (8, 8), (255, 0, 0, 0)).save(src)
    jpeg = ci.fit_image(src, tmp_path / "clear.jpg", None, "cover")
    with Image.open(jpeg) as im:
        assert im.getpixel((0, 0)) == (255, 255, 255)


def test_postprocess_replaces_file_on_format_change(tmp_path):
    src = make_png(tmp_path / "a-1.png", size=(64, 64))
    out = ci.postprocess([src], (32, 32), "cover", "webp")
    assert out == [tmp_path / "a-1.webp"]
    assert not src.exists() and out[0].is_file()
    assert ci.postprocess([out[0]], None, "cover", None) == out


def test_codex_env_strips_all_api_key_vars(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("CODEX_API_KEY", "sk-codex")
    monkeypatch.setenv("KEEP_ME", "1")
    env = ci.codex_env()
    assert "OPENAI_API_KEY" not in env and "CODEX_API_KEY" not in env
    assert env["KEEP_ME"] == "1"


def test_batch_ok_requires_full_count_and_clean_exit():
    assert ci.batch_ok(2, 2, 0)
    assert ci.batch_ok(3, 2, 0)
    assert not ci.batch_ok(1, 2, 0)
    assert not ci.batch_ok(2, 2, 1)
    assert not ci.batch_ok(0, 1, 0)


def test_run_codex_timeout_kills_process_tree(monkeypatch):
    # A child that spawns a grandchild holding the stdout pipe for 30s. Without
    # tree-kill, draining the pipe would block until the grandchild exits.
    grandchild = "import time; time.sleep(30)"
    child = f"import subprocess, sys; subprocess.run([sys.executable, '-c', {grandchild!r}])"
    monkeypatch.setattr(ci, "find_codex", lambda: sys.executable)
    started = time.time()
    with pytest.raises(ci.subprocess.TimeoutExpired):
        ci.run_codex(["-c", child], "", timeout=1)
    assert time.time() - started < 15


def test_count_must_be_positive():
    parser = ci.build_parser()
    assert parser.parse_args(["generate", "--name", "x", "--count", "2"]).count == 2
    with pytest.raises(SystemExit):
        parser.parse_args(["generate", "--name", "x", "--count", "0"])


def test_main_reports_codex_timeout_as_json(monkeypatch, capsys):
    def timeout(args, stdin_text, timeout, cwd=None):
        raise ci.subprocess.TimeoutExpired(["codex", *args], timeout)

    monkeypatch.setattr(ci, "find_codex", lambda: "codex")
    monkeypatch.setattr(ci, "run_codex", timeout)
    assert ci.main(["doctor"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is False and "timed out" in result["error"]


def test_codex_exec_args_are_hands_off_and_read_only():
    args = ci.codex_exec_args("low")
    assert args[:2] == ["exec", "--json"]
    assert "--ephemeral" in args and "read-only" in args
    assert "model_reasoning_effort=low" in args
    assert args[-1] == "-"  # prompt via stdin


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
