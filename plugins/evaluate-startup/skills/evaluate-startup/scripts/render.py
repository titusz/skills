#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jinja2>=3.1",
#   "jsonschema>=4.21",
#   "rfc3339-validator>=0.1.4",
# ]
# ///
"""
evaluate-startup renderer
=========================

Standalone tool shipped with the `evaluate-startup` skill. Converts a
schema-conforming `analysis.json` into a self-contained, light/dark themed
HTML report, and maintains a searchable `index.html` across all evaluations.

Usage:
    uv run render.py validate <analysis.json>
    uv run render.py render   <analysis.json> [-o report.html]
    uv run render.py index    <ideas-root-dir>
    uv run render.py all      <analysis.json>       # validate + render + index

No CDN dependencies in the output. Reports work offline and print cleanly.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, select_autoescape
from jsonschema import Draft7Validator

# Console output contains non-ASCII glyphs (✓, →); piped stdout on Windows may
# default to a legacy codepage that cannot encode them.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

SKILL_VERSION = "0.1.0"  # keep in sync with .claude-plugin/plugin.json
CONFIDENCE_VALUE = {"high": 1.0, "medium": 0.6, "low": 0.3}

# The six scoring categories methodology.md fixes the model at.
STANDARD_CATEGORY_IDS = (
    "problem",
    "market",
    "leverage",
    "moat",
    "economics",
    "execution",
)

# methodology.md's verdict table, ordered by descending composite floor:
# (composite floor, band when conviction >= threshold, band when below).
BAND_TABLE = (
    (7.5, "pursue", "validate"),
    (6.5, "prototype", "validate"),
    (5.5, "explore", "explore"),
    (4.0, "monitor", "monitor"),
    (0.0, "avoid", "monitor"),
)
CONVICTION_THRESHOLD = 0.5

# Bands from least to most committed. methodology.md lets verdict.recommendation
# deviate at most one step from the mechanical band.
BAND_ORDER = ("avoid", "monitor", "explore", "validate", "prototype", "pursue")

# Composite and conviction are stored to two decimals, so anything beyond one
# unit in the last place is a real arithmetic error, not a rounding artifact.
SCORE_TOLERANCE = 0.011

BAND_META = {
    "pursue": {
        "label": "Pursue",
        "color": "#10b981",
        "desc": "Strong signal, strong evidence — commit resources.",
    },
    "prototype": {
        "label": "Prototype",
        "color": "#14b8a6",
        "desc": "Build the smallest thing that tests the core loop.",
    },
    "validate": {
        "label": "Validate",
        "color": "#8b5cf6",
        "desc": "Attractive but under-evidenced — de-risk assumptions first.",
    },
    "explore": {
        "label": "Explore",
        "color": "#3b82f6",
        "desc": "Interesting; keep investigating before committing.",
    },
    "monitor": {
        "label": "Monitor",
        "color": "#f59e0b",
        "desc": "Not now — watch for the conditions to change.",
    },
    "avoid": {
        "label": "Avoid",
        "color": "#ef4444",
        "desc": "Evidence says no — spend your time elsewhere.",
    },
}

SEVERITY_COLOR = {
    "low": "#3b82f6",
    "medium": "#f59e0b",
    "high": "#f97316",
    "critical": "#ef4444",
}


# --------------------------------------------------------------------------- #
# Data helpers
# --------------------------------------------------------------------------- #


def load_json(path: Path) -> dict:
    """Read a UTF-8 JSON file into a dict."""
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_schema() -> dict | None:
    """Load the analysis schema shipped next to this script, or None if absent."""
    candidate = Path(__file__).resolve().parent / "analysis.schema.json"
    if candidate.exists():
        return load_json(candidate)
    return None


def compute_composite(data: dict) -> float:
    """Weighted attractiveness score (0-10) across the assessment categories."""
    cats = data["assessment"]["categories"]
    return round(sum(c["weight"] * c["score"] for c in cats), 2)


def compute_conviction(data: dict) -> float:
    """Weight-normalized evidence strength (0-1) across the assessment categories."""
    cats = data["assessment"]["categories"]
    total_w = sum(c["weight"] for c in cats) or 1.0
    return round(
        sum(c["weight"] * CONFIDENCE_VALUE[c["confidence"]] for c in cats) / total_w, 2
    )


def derive_band(composite: float, conviction: float) -> str:
    """Mechanical verdict band for a score pair, per methodology.md's verdict table."""
    for floor, high_conviction, low_conviction in BAND_TABLE:
        if composite >= floor:
            return (
                high_conviction
                if conviction >= CONVICTION_THRESHOLD
                else low_conviction
            )
    return "avoid"


def band_distance(a: str, b: str) -> int:
    """Number of steps between two bands on the avoid-to-pursue scale."""
    if a not in BAND_ORDER or b not in BAND_ORDER:
        return 0  # unknown band: schema validation already reported it
    return abs(BAND_ORDER.index(a) - BAND_ORDER.index(b))


def score_color(score: float) -> str:
    """Color for a 0-10 score; boundaries mirror methodology.md's band floors."""
    if score < 4.0:
        return "#ef4444"
    if score < 5.5:
        return "#f59e0b"
    if score < 6.5:
        return "#3b82f6"
    if score < 7.5:
        return "#14b8a6"
    return "#10b981"


def validate_analysis(data: dict) -> list[str]:
    """Return a list of problems (empty list == valid)."""
    problems: list[str] = []

    schema = load_schema()
    if schema is not None:
        # format_checker is required for `format` annotations (e.g. date-time) to
        # be enforced rather than treated as documentation.
        validator = Draft7Validator(
            schema, format_checker=Draft7Validator.FORMAT_CHECKER
        )
        for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
            loc = ".".join(str(p) for p in err.path) or "<root>"
            # Array/object errors embed the whole offending instance in the message.
            message = err.message
            if len(message) > 200:
                message = message[:200] + "… (truncated)"
            problems.append(f"schema: {loc}: {message}")
    else:
        problems.append(
            "warning: analysis.schema.json not found next to render.py — schema check skipped"
        )

    # Semantic checks (only if structurally plausible)
    try:
        cats = data["assessment"]["categories"]
        weight_sum = sum(c["weight"] for c in cats)
        if abs(weight_sum - 1.0) > 0.011:
            problems.append(
                f"weights: category weights sum to {weight_sum:.3f}, expected 1.0"
            )

        missing = [i for i in STANDARD_CATEGORY_IDS if i not in {c["id"] for c in cats}]
        if missing:
            problems.append(
                f"categories: missing required categor{'y' if len(missing) == 1 else 'ies'} "
                f"{', '.join(missing)} — methodology.md fixes the model at six"
            )

        composite = compute_composite(data)
        declared = data["scores"]["composite"]
        if abs(composite - declared) > SCORE_TOLERANCE:
            problems.append(
                f"scores: declared composite {declared} != weighted recomputation {composite}"
            )

        conviction = compute_conviction(data)
        declared_conv = data["scores"]["conviction"]
        if abs(conviction - declared_conv) > SCORE_TOLERANCE:
            problems.append(
                f"scores: declared conviction {declared_conv} != recomputation {conviction}"
            )

        # Band is fully mechanical: derive it from the recomputed scores, which are
        # authoritative even when the declared ones drifted.
        expected_band = derive_band(composite, conviction)
        if data["scores"]["band"] != expected_band:
            problems.append(
                f"scores: declared band '{data['scores']['band']}' != '{expected_band}' "
                f"required by the verdict table for composite {composite} / "
                f"conviction {conviction}"
            )

        recommendation = data["verdict"]["recommendation"]
        if band_distance(recommendation, expected_band) > 1:
            problems.append(
                f"verdict: recommendation '{recommendation}' deviates more than one step "
                f"from band '{expected_band}' — methodology.md forbids this"
            )

        for cat in cats:
            if cat.get("dimensions"):
                mean = sum(d["score"] for d in cat["dimensions"]) / len(
                    cat["dimensions"]
                )
                if abs(mean - cat["score"]) > 1.5:
                    problems.append(
                        f"scores: category '{cat['id']}' score {cat['score']} deviates >1.5 "
                        f"from dimension mean {mean:.1f} — double-check reasoning"
                    )
    except (KeyError, TypeError, ZeroDivisionError):
        pass  # structural errors already reported by schema validation

    return problems


# --------------------------------------------------------------------------- #
# Jinja environment
# --------------------------------------------------------------------------- #


def jinja_env() -> Environment:
    """Jinja environment for the inline templates, with report-specific filters.

    Autoescape is on for the string templates, so trusted static blocks (CSS, JS,
    pre-built SVG) must be passed through the `safe` filter at their use sites.
    """
    env = Environment(autoescape=select_autoescape(["html"]))
    env.filters["score_color"] = score_color
    env.filters["band_color"] = lambda b: BAND_META.get(b, {}).get("color", "#64748b")
    env.filters["band_label"] = lambda b: BAND_META.get(b, {}).get("label", b)
    env.filters["sev_color"] = lambda s: SEVERITY_COLOR.get(s, "#64748b")
    env.filters["pct"] = lambda x: f"{round(x * 100)}%"
    env.filters["fmt_date"] = lambda s: (s or "")[:10]
    return env


# --------------------------------------------------------------------------- #
# Shared CSS / JS (self-contained, no CDN)
# --------------------------------------------------------------------------- #

BASE_CSS = """
:root {
  --bg: #f6f7f9; --panel: #ffffff; --panel-2: #eef1f5;
  --text: #16202c; --muted: #5b6b7d; --border: #dde3ea;
  --accent: #2563eb; --shadow: 0 1px 3px rgba(16,32,44,.08);
  --mono: ui-monospace, "SF Mono", "Cascadia Code", Menlo, Consolas, monospace;
  --sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
[data-theme="dark"] {
  --bg: #0d1117; --panel: #161c26; --panel-2: #1d2530;
  --text: #e6ebf2; --muted: #94a3b8; --border: #29323f;
  --accent: #60a5fa; --shadow: 0 1px 3px rgba(0,0,0,.4);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font-family: var(--sans); font-size: 15px; line-height: 1.55;
  transition: background .2s, color .2s;
}
.wrap { max-width: 980px; margin: 0 auto; padding: 28px 20px 64px; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
h1 { font-size: 26px; margin: 0 0 4px; letter-spacing: -.01em; }
h2 { font-size: 17px; margin: 0 0 12px; letter-spacing: -.01em; }
h3 { font-size: 14px; margin: 0 0 6px; }
.muted { color: var(--muted); }
.small { font-size: 12.5px; }
.mono { font-family: var(--mono); }
.panel {
  background: var(--panel); border: 1px solid var(--border);
  border-radius: 12px; padding: 18px 20px; margin-bottom: 18px; box-shadow: var(--shadow);
}
.badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 12px; border-radius: 999px; font-weight: 700;
  font-size: 13px; color: #fff; letter-spacing: .02em; text-transform: uppercase;
}
.chip {
  display: inline-block; padding: 1px 9px; border-radius: 999px;
  background: var(--panel-2); border: 1px solid var(--border);
  font-size: 12px; color: var(--muted); margin: 2px 3px 2px 0;
}
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
@media (max-width: 720px) { .grid2 { grid-template-columns: 1fr; } }
.topbar { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 20px; }
.theme-toggle {
  cursor: pointer; border: 1px solid var(--border); background: var(--panel);
  color: var(--text); border-radius: 999px; padding: 6px 14px; font-size: 13px;
  box-shadow: var(--shadow); white-space: nowrap;
}
table { width: 100%; border-collapse: collapse; }
th { text-align: left; font-size: 12px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); padding: 6px 10px; border-bottom: 1px solid var(--border); }
td { padding: 8px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }
tr:last-child td { border-bottom: none; }
.scorebar { position: relative; height: 8px; border-radius: 999px; background: var(--panel-2); overflow: hidden; }
.scorebar > span { position: absolute; inset: 0 auto 0 0; border-radius: 999px; }
.scorechip {
  display: inline-block; min-width: 34px; text-align: center; font-family: var(--mono);
  font-weight: 700; font-size: 12.5px; color: #fff; border-radius: 6px; padding: 2px 6px;
}
details { border: 1px solid var(--border); border-radius: 10px; margin-bottom: 10px; background: var(--panel); }
details > summary { cursor: pointer; padding: 10px 14px; font-weight: 600; list-style: none; display: flex; align-items: center; gap: 10px; }
details > summary::-webkit-details-marker { display: none; }
details > summary::before { content: "▸"; color: var(--muted); transition: transform .15s; }
details[open] > summary::before { transform: rotate(90deg); }
details > .body { padding: 4px 16px 14px; }
ul.tight { margin: 6px 0; padding-left: 20px; }
ul.tight li { margin-bottom: 5px; }
.footer { margin-top: 30px; text-align: center; }
@media print {
  :root { --bg:#fff; --panel:#fff; --panel-2:#f2f4f7; --text:#111; --muted:#555; --border:#ccc; --shadow:none; }
  .theme-toggle, .no-print { display: none !important; }
  .panel, details { break-inside: avoid; }
  details > summary::before { display: none; }
  body { font-size: 12px; }
}
"""

THEME_JS = """
(function () {
  var saved = null;
  try { saved = localStorage.getItem('es-theme'); } catch (e) {}
  var prefers = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  var theme = saved || (prefers ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', theme);
  window.esToggleTheme = function () {
    var cur = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', cur);
    try { localStorage.setItem('es-theme', cur); } catch (e) {}
    var btn = document.getElementById('theme-btn');
    if (btn) btn.textContent = cur === 'dark' ? '\\u2600 Light' : '\\u263E Dark';
  };
  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.getElementById('theme-btn');
    if (btn) btn.textContent = theme === 'dark' ? '\\u2600 Light' : '\\u263E Dark';
  });
  // Closed <details> keep their bodies hidden on paper, which would drop most of
  // the rationale and sources from a printed report. Open them for the print job
  // only, then restore whatever the reader had expanded.
  var reopened = [];
  window.addEventListener('beforeprint', function () {
    reopened = [];
    Array.prototype.forEach.call(document.querySelectorAll('details'), function (el) {
      if (!el.open) { reopened.push(el); el.open = true; }
    });
  });
  window.addEventListener('afterprint', function () {
    reopened.forEach(function (el) { el.open = false; });
    reopened = [];
  });
})();
"""


# --------------------------------------------------------------------------- #
# Report template
# --------------------------------------------------------------------------- #

REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ d.meta.name }} — Startup Evaluation</title>
<style>{{ base_css | safe }}</style>
<script>{{ theme_js | safe }}</script>
</head>
<body>
<div class="wrap">

  <div class="topbar">
    <div>
      {% if has_index %}<div class="small muted"><a href="../index.html">← All evaluations</a></div>{% endif %}
      <h1>{{ d.meta.name }}</h1>
      <div class="muted">{{ d.meta.one_liner }}</div>
      <div class="small muted" style="margin-top:6px">
        Evaluated {{ d.meta.evaluated_at | fmt_date }}
        {% if d.meta.evaluator %} · {{ d.meta.evaluator }}{% endif %}
        {% for t in d.meta.get('tags', []) %}<span class="chip">{{ t }}</span>{% endfor %}
      </div>
    </div>
    <button id="theme-btn" class="theme-toggle" onclick="esToggleTheme()">Theme</button>
  </div>

  <!-- Verdict hero -->
  <div class="panel" style="border-left: 5px solid {{ d.verdict.recommendation | band_color }}">
    <div style="display:flex; flex-wrap:wrap; gap:24px; align-items:center;">
      <div style="flex:0 0 auto; text-align:center;">
        <div class="badge" style="background: {{ d.verdict.recommendation | band_color }}">{{ d.verdict.recommendation | band_label }}</div>
        {% if d.verdict.recommendation != d.scores.band %}
        <div class="small muted" style="margin-top:5px">score band: {{ d.scores.band | band_label }}</div>
        {% endif %}
        <div class="mono" style="font-size:46px; font-weight:800; line-height:1.1; margin-top:6px;">{{ '%.1f' % d.scores.composite }}</div>
        <div class="small muted">composite / 10</div>
        <div class="small" style="margin-top:6px;">conviction <b class="mono">{{ d.scores.conviction | pct }}</b></div>
      </div>
      <div style="flex:1 1 320px;">
        <p style="margin:0 0 8px;">{{ d.verdict.summary }}</p>
        <div class="small muted">{{ band_desc }} · Verdict confidence: <b>{{ d.verdict.confidence }}</b></div>
      </div>
      <div style="flex:0 0 auto;">{{ matrix_svg | safe }}</div>
    </div>
  </div>

  <!-- Score overview -->
  <div class="panel">
    <h2>Score overview</h2>
    <table>
      <tr><th style="width:34%">Category</th><th style="width:8%">Wt</th><th>Score</th><th style="width:10%">Conf.</th></tr>
      {% for c in d.assessment.categories %}
      <tr>
        <td><a href="#cat-{{ c.id }}" style="color:inherit">{{ c.name }}</a></td>
        <td class="mono small muted">{{ (c.weight * 100) | round | int }}%</td>
        <td>
          <div style="display:flex; align-items:center; gap:10px;">
            <div class="scorebar" style="flex:1"><span style="width: {{ c.score * 10 }}%; background: {{ c.score | score_color }}"></span></div>
            <span class="scorechip" style="background: {{ c.score | score_color }}">{{ '%.1f' % c.score }}</span>
          </div>
        </td>
        <td class="small muted">{{ {'high':'●●●','medium':'●●○','low':'●○○'}[c.confidence] }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>

  <!-- Category details -->
  <div class="panel">
    <h2>Assessment detail</h2>
    {% for c in d.assessment.categories %}
    <details id="cat-{{ c.id }}" {{ 'open' if loop.index <= 2 else '' }}>
      <summary>
        <span class="scorechip" style="background: {{ c.score | score_color }}">{{ '%.1f' % c.score }}</span>
        {{ c.name }}
        <span class="small muted" style="margin-left:auto">weight {{ (c.weight * 100) | round | int }}% · confidence {{ c.confidence }}</span>
      </summary>
      <div class="body">
        <p class="small" style="margin-top:4px">{{ c.summary }}</p>
        <table>
          <tr><th style="width:28%">Dimension</th><th style="width:8%">Score</th><th>Rationale</th></tr>
          {% for dim in c.dimensions %}
          <tr>
            <td>{{ dim.name }}</td>
            <td><span class="scorechip" style="background: {{ dim.score | score_color }}">{{ '%.0f' % dim.score if dim.score == dim.score | round(0) else '%.1f' % dim.score }}</span></td>
            <td class="small">{{ dim.rationale }}</td>
          </tr>
          {% endfor %}
        </table>
        {% if c.get('sources') %}
        <div class="small muted" style="margin-top:10px"><b>Sources</b>
          <ul class="tight">
            {% for s in c.sources %}
            <li>{% if s.get('url') %}<a href="{{ s.url }}" target="_blank" rel="noopener">{{ s.title }}</a>{% else %}{{ s.title }}{% endif %}{% if s.get('note') %} — {{ s.note }}{% endif %}</li>
            {% endfor %}
          </ul>
        </div>
        {% endif %}
      </div>
    </details>
    {% endfor %}
  </div>

  <!-- Strengths / weaknesses -->
  <div class="grid2">
    <div class="panel">
      <h2 style="color:#10b981">Strengths</h2>
      <ul class="tight">{% for s in d.verdict.strengths %}<li>{{ s }}</li>{% endfor %}</ul>
    </div>
    <div class="panel">
      <h2 style="color:#ef4444">Weaknesses</h2>
      <ul class="tight">{% for w in d.verdict.weaknesses %}<li>{{ w }}</li>{% endfor %}</ul>
    </div>
  </div>

  <!-- Risks -->
  {% if d.verdict.risks %}
  <div class="panel">
    <h2>Risks</h2>
    <table>
      <tr><th>Risk</th><th style="width:11%">Severity</th><th style="width:11%">Likelihood</th><th style="width:34%">Mitigation</th></tr>
      {% for r in d.verdict.risks %}
      <tr>
        <td>{{ r.risk }}</td>
        <td><span class="scorechip" style="background: {{ r.severity | sev_color }}">{{ r.severity }}</span></td>
        <td class="small muted">{{ r.likelihood }}</td>
        <td class="small">{{ r.get('mitigation', '—') }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>
  {% endif %}

  <!-- Assumptions & kill criteria -->
  <div class="grid2">
    <div class="panel">
      <h2>Key assumptions</h2>
      <ul class="tight">
        {% for a in d.verdict.assumptions %}
        <li><b class="small" style="text-transform:uppercase; color: {{ {'high':'#ef4444','medium':'#f59e0b','low':'#3b82f6'}[a.criticality] }}">{{ a.criticality }}</b>
          — {{ a.assumption }}{% if a.get('current_evidence') %} <span class="small muted">({{ a.current_evidence }})</span>{% endif %}</li>
        {% endfor %}
      </ul>
    </div>
    <div class="panel">
      <h2>Kill criteria</h2>
      <p class="small muted" style="margin-top:-6px">If any of these turn out true, stop.</p>
      <ul class="tight">{% for k in d.verdict.kill_criteria %}<li>{{ k }}</li>{% endfor %}</ul>
    </div>
  </div>

  <!-- Validation plan -->
  {% if d.verdict.validation_plan %}
  <div class="panel">
    <h2>Validation plan</h2>
    <table>
      <tr><th>Question to answer</th><th style="width:26%">Method</th><th style="width:10%">Effort</th><th style="width:26%">Success signal</th></tr>
      {% for v in d.verdict.validation_plan %}
      <tr>
        <td>{{ v.question }}</td>
        <td class="small">{{ v.method }}</td>
        <td class="small muted">{{ v.get('effort', '—') }}</td>
        <td class="small">{{ v.success_signal }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>
  {% endif %}

  <!-- Next steps -->
  {% if d.verdict.next_steps %}
  <div class="panel">
    <h2>Next steps</h2>
    <ol style="margin:6px 0; padding-left:22px;">{% for n in d.verdict.next_steps %}<li style="margin-bottom:5px">{{ n }}</li>{% endfor %}</ol>
  </div>
  {% endif %}

  <!-- Custom sections -->
  {% for cs in d.get('custom_sections', []) %}
  <div class="panel">
    <h2>{{ cs.title }}</h2>
    {{ cs.html | safe }}
  </div>
  {% endfor %}

  <!-- Idea & interview appendix -->
  <div class="panel">
    <h2>Idea profile</h2>
    <p class="small">{{ d.idea.description }}</p>
    <table>
      <tr><td class="small muted" style="width:22%">Target customer</td><td class="small">{{ d.idea.target_customer }}</td></tr>
      <tr><td class="small muted">Value proposition</td><td class="small">{{ d.idea.value_proposition }}</td></tr>
      {% if d.idea.get('stage') %}<tr><td class="small muted">Stage</td><td class="small">{{ d.idea.stage }}</td></tr>{% endif %}
      {% if d.idea.get('founder_context') %}<tr><td class="small muted">Founder context</td><td class="small">{{ d.idea.founder_context }}</td></tr>{% endif %}
    </table>
    {% if d.idea.get('interview_notes') %}
    <details style="margin-top:12px">
      <summary class="small">Interview notes ({{ d.idea.interview_notes | length }})</summary>
      <div class="body">
        {% for qa in d.idea.interview_notes %}
        <p class="small" style="margin:6px 0"><b>Q:</b> {{ qa.q }}<br><b>A:</b> {{ qa.a }}</p>
        {% endfor %}
      </div>
    </details>
    {% endif %}
  </div>

  <!-- Research appendix -->
  <div class="panel">
    <h2>Research appendix</h2>
    {% for a in d.research.angles %}
    <details>
      <summary>{{ a.title }}</summary>
      <div class="body">
        <p class="small">{{ a.summary }}</p>
        <ul class="tight small">{% for f in a.findings %}<li>{{ f }}</li>{% endfor %}</ul>
        {% if a.get('sources') %}
        <div class="small muted"><b>Sources</b>
          <ul class="tight">
            {% for s in a.sources %}
            <li>{% if s.get('url') %}<a href="{{ s.url }}" target="_blank" rel="noopener">{{ s.title }}</a>{% else %}{{ s.title }}{% endif %}{% if s.get('note') %} — {{ s.note }}{% endif %}</li>
            {% endfor %}
          </ul>
        </div>
        {% endif %}
      </div>
    </details>
    {% endfor %}
  </div>

  <div class="footer small muted">
    Generated by <span class="mono">evaluate-startup v{{ skill_version }}</span> ·
    schema <span class="mono">{{ d.schema_version }}</span> ·
    {{ generated_at }}
  </div>

</div>
</body>
</html>
"""


def build_matrix_svg(composite: float, conviction: float, band: str) -> str:
    """2D position plot: x = composite score (0-10), y = conviction (0-1).

    Quadrant labels describe the two axes rather than naming verdict bands: a 2x2
    grid cannot represent six bands, so verdict-named quadrants would contradict
    the badge for any score between two boundaries.
    """
    w, h, pad = 240, 170, 26
    px = pad + (composite / 10) * (w - 2 * pad)
    py = (h - pad) - conviction * (h - 2 * pad)
    tx = pad + (6.5 / 10) * (w - 2 * pad)  # score threshold line
    ty = (h - pad) - 0.5 * (h - 2 * pad)  # conviction threshold line
    color = BAND_META.get(band, {}).get("color", "#64748b")
    return f"""
<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Verdict matrix">
  <style>.ml {{ font: 9px var(--mono, monospace); fill: var(--muted, #64748b); }}
         .qd {{ font: 8.5px var(--sans, sans-serif); fill: var(--muted, #64748b); opacity:.85 }}</style>
  <rect x="{pad}" y="{pad}" width="{w - 2 * pad}" height="{h - 2 * pad}" fill="none"
        stroke="var(--border, #cbd5e1)" rx="6"/>
  <line x1="{tx:.0f}" y1="{pad}" x2="{tx:.0f}" y2="{h - pad}" stroke="var(--border, #cbd5e1)" stroke-dasharray="3 3"/>
  <line x1="{pad}" y1="{ty:.0f}" x2="{w - pad}" y2="{ty:.0f}" stroke="var(--border, #cbd5e1)" stroke-dasharray="3 3"/>
  <text class="qd" x="{w - pad - 4}" y="{pad + 11}" text-anchor="end">attractive</text>
  <text class="qd" x="{w - pad - 4}" y="{pad + 21}" text-anchor="end">evidenced</text>
  <text class="qd" x="{w - pad - 4}" y="{h - pad - 14}" text-anchor="end">attractive</text>
  <text class="qd" x="{w - pad - 4}" y="{h - pad - 4}" text-anchor="end">unproven</text>
  <text class="qd" x="{pad + 4}" y="{pad + 11}">weak</text>
  <text class="qd" x="{pad + 4}" y="{pad + 21}">evidenced</text>
  <text class="qd" x="{pad + 4}" y="{h - pad - 14}">weak</text>
  <text class="qd" x="{pad + 4}" y="{h - pad - 4}">unproven</text>
  <circle cx="{px:.0f}" cy="{py:.0f}" r="7" fill="{color}" stroke="#fff" stroke-width="2"/>
  <text class="ml" x="{w / 2:.0f}" y="{h - 4}" text-anchor="middle">attractiveness (composite) →</text>
  <text class="ml" x="9" y="{h / 2:.0f}" text-anchor="middle" transform="rotate(-90 9 {h / 2:.0f})">conviction →</text>
</svg>"""


def render_report(
    analysis_path: Path, out_path: Path | None, has_index: bool | None = None
) -> Path:
    """Render an analysis to a standalone report.html and return the written path.

    `has_index` controls the back-link to the evaluations index; it defaults to
    probing for a sibling-of-parent index.html, which callers that are about to
    build one should override.
    """
    data = load_json(analysis_path)
    out = out_path or analysis_path.parent / "report.html"
    recommendation = data["verdict"]["recommendation"]
    env = jinja_env()
    html = env.from_string(REPORT_TEMPLATE).render(
        d=data,
        base_css=BASE_CSS,
        theme_js=THEME_JS,
        matrix_svg=build_matrix_svg(
            data["scores"]["composite"],
            data["scores"]["conviction"],
            recommendation,
        ),
        band_desc=BAND_META.get(recommendation, {}).get("desc", ""),
        has_index=(
            has_index
            if has_index is not None
            else (out.resolve().parent.parent / "index.html").exists()
        ),
        skill_version=SKILL_VERSION,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


# --------------------------------------------------------------------------- #
# Index
# --------------------------------------------------------------------------- #

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Startup Idea Evaluations</title>
<style>{{ base_css | safe }}
.searchbar { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:20px; }
.searchbar input, .searchbar select {
  background: var(--panel); color: var(--text); border: 1px solid var(--border);
  border-radius: 10px; padding: 9px 14px; font-size: 14px; box-shadow: var(--shadow);
}
.searchbar input { flex: 1 1 260px; }
.cards { display:grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap:16px; }
.card {
  display:block; background: var(--panel); border:1px solid var(--border); border-radius:12px;
  padding:16px 18px; box-shadow: var(--shadow); color: inherit; transition: transform .1s, border-color .1s;
}
.card:hover { transform: translateY(-2px); border-color: var(--accent); text-decoration:none; }
.card h3 { margin:0 0 4px; font-size:15.5px; }
.card .score { font-family: var(--mono); font-weight:800; font-size:22px; }
</style>
<script>{{ theme_js | safe }}</script>
</head>
<body>
<div class="wrap">
  <div class="topbar">
    <div>
      <h1>Startup Idea Evaluations</h1>
      <div class="muted small">{{ cards | length }} evaluation{{ 's' if cards | length != 1 else '' }} · generated {{ generated_at }}</div>
    </div>
    <button id="theme-btn" class="theme-toggle" onclick="esToggleTheme()">Theme</button>
  </div>

  <div class="searchbar no-print">
    <input id="q" type="search" placeholder="Search ideas, tags, verdicts…" autocomplete="off">
    <select id="sort">
      <option value="score">Sort: score ↓</option>
      <option value="date">Sort: newest</option>
      <option value="name">Sort: name</option>
    </select>
  </div>

  <div class="cards" id="cards"></div>
  <p class="muted small" id="empty" style="display:none">No evaluations match.</p>

  <div class="footer small muted">Maintained by <span class="mono">evaluate-startup v{{ skill_version }}</span></div>
</div>

<script>
var DATA = {{ cards_json | safe }};
var BAND_COLORS = {{ band_colors_json | safe }};

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
  });
}
function cardHtml(c) {
  var color = BAND_COLORS[c.recommendation] || '#64748b';
  var tags = (c.tags || []).map(function (t) { return '<span class="chip">' + esc(t) + '</span>'; }).join('');
  return '<a class="card" href="' + esc(c.href) + '">' +
    '<div style="display:flex; justify-content:space-between; align-items:baseline; gap:8px;">' +
      '<h3>' + esc(c.name) + '</h3>' +
      '<span class="score" style="color:' + color + '">' + c.composite.toFixed(1) + '</span>' +
    '</div>' +
    '<div class="badge" style="background:' + color + '; font-size:11px; padding:2px 10px;">' + esc(c.recommendation) + '</div>' +
    '<p class="small" style="margin:8px 0 6px; color:var(--muted)">' + esc(c.one_liner) + '</p>' +
    '<div class="small muted mono">' + esc(c.date) + ' · conviction ' + Math.round(c.conviction * 100) + '%</div>' +
    '<div style="margin-top:6px">' + tags + '</div>' +
  '</a>';
}
function refresh() {
  var q = document.getElementById('q').value.toLowerCase().trim();
  var sort = document.getElementById('sort').value;
  var items = DATA.filter(function (c) {
    if (!q) return true;
    var hay = (c.name + ' ' + c.one_liner + ' ' + c.recommendation + ' ' + (c.tags || []).join(' ')).toLowerCase();
    return q.split(/\\s+/).every(function (w) { return hay.indexOf(w) !== -1; });
  });
  items.sort(function (a, b) {
    if (sort === 'name') return a.name.localeCompare(b.name);
    if (sort === 'date') return b.date.localeCompare(a.date);
    return b.composite - a.composite;
  });
  document.getElementById('cards').innerHTML = items.map(cardHtml).join('');
  document.getElementById('empty').style.display = items.length ? 'none' : 'block';
}
document.getElementById('q').addEventListener('input', refresh);
document.getElementById('sort').addEventListener('change', refresh);
refresh();
</script>
</body>
</html>
"""


def build_index(root: Path) -> Path:
    """Rebuild root/index.html from every <root>/*/analysis.json and return its path."""
    cards = []
    for analysis in sorted(root.glob("*/analysis.json")):
        try:
            d = load_json(analysis)
            report = analysis.parent / "report.html"
            cards.append(
                {
                    "name": d["meta"]["name"],
                    "one_liner": d["meta"].get("one_liner", ""),
                    "recommendation": d["verdict"]["recommendation"],
                    "composite": float(d["scores"]["composite"]),
                    "conviction": float(d["scores"].get("conviction", 0)),
                    "date": (d["meta"].get("evaluated_at") or "")[:10],
                    "tags": d["meta"].get("tags", []),
                    "href": f"{analysis.parent.name}/{'report.html' if report.exists() else 'analysis.json'}",
                }
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            print(f"  ! skipping {analysis}: {exc}", file=sys.stderr)

    cards.sort(key=lambda c: c["composite"], reverse=True)
    env = jinja_env()

    def js_json(obj) -> str:
        return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")

    html = env.from_string(INDEX_TEMPLATE).render(
        cards=cards,
        cards_json=js_json(cards),
        band_colors_json=js_json({k: v["color"] for k, v in BAND_META.items()}),
        base_css=BASE_CSS,
        theme_js=THEME_JS,
        skill_version=SKILL_VERSION,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    out = root / "index.html"
    out.write_text(html, encoding="utf-8")
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def report_problems(problems: list[str]) -> bool:
    """Print validation problems; return True if any is a hard error, not a warning."""
    for p in problems:
        print(f"  - {p}")
    return any(not p.startswith("warning") for p in problems)


def main() -> int:
    """Parse arguments, dispatch the subcommand, and return a process exit code."""
    parser = argparse.ArgumentParser(description="evaluate-startup renderer")
    parser.add_argument(
        "--version", action="version", version=f"evaluate-startup {SKILL_VERSION}"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser(
        "validate", help="Validate analysis.json against schema + scoring rules"
    )
    p_val.add_argument("analysis", type=Path)

    p_ren = sub.add_parser(
        "render", help="Render analysis.json to a standalone report.html"
    )
    p_ren.add_argument("analysis", type=Path)
    p_ren.add_argument("-o", "--out", type=Path, default=None)

    p_idx = sub.add_parser(
        "index", help="Regenerate index.html by scanning <root>/*/analysis.json"
    )
    p_idx.add_argument("root", type=Path)

    p_all = sub.add_parser(
        "all", help="validate + render + rebuild index of the parent directory"
    )
    p_all.add_argument("analysis", type=Path)

    args = parser.parse_args()

    if args.cmd in ("validate", "render", "all") and not args.analysis.exists():
        print(f"error: {args.analysis} not found", file=sys.stderr)
        return 2

    if args.cmd == "validate":
        problems = validate_analysis(load_json(args.analysis))
        if report_problems(problems):
            print(f"INVALID — {len(problems)} problem(s)")
            return 1
        print("VALID ✓  (schema, weights, scores, and verdict band all consistent)")
        return 0

    if args.cmd == "render":
        if report_problems(validate_analysis(load_json(args.analysis))):
            print("aborting: fix validation problems first")
            return 1
        out = render_report(args.analysis, args.out)
        print(f"report → {out}")
        return 0

    if args.cmd == "index":
        if not args.root.is_dir():
            print(f"error: {args.root} is not a directory", file=sys.stderr)
            return 2
        out = build_index(args.root)
        print(f"index → {out}")
        return 0

    if args.cmd == "all":
        analysis = args.analysis.resolve()
        if report_problems(validate_analysis(load_json(analysis))):
            print("aborting: fix validation problems first")
            return 1
        # Render before indexing so the index links to report.html, but tell the
        # report the index is coming so its back-link is present on a first run.
        out = render_report(analysis, None, has_index=True)
        print(f"report → {out}")
        idx = build_index(analysis.parent.parent)
        print(f"index  → {idx}")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
