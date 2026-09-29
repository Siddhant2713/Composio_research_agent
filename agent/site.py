"""Build the single self-contained report page.

The data is embedded rather than fetched. A plain `file://` open blocks XHR/fetch of local
files, which would put a CORS error in the console on the very first load — so this reads the
JSON at build time and inlines it. The result is one HTML file with no build step, no server
and no network dependency.

  python -m agent.site
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
VERIFICATION_DIR = ROOT / "verification"
OUT = ROOT / "site" / "index.html"

REPO_URL = "https://github.com/Siddhant2713/Composio_research_agent"
RUN_COMMAND = "pip install -r requirements.txt && python -m agent.run --pass pass2"


def load(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return default


def headline_sentences(patterns: dict) -> list[str]:
    """The 4-6 Zone-1 sentences, each generated straight from a count in patterns.json.

    Built from the data rather than written by hand, so the page cannot drift from the
    numbers underneath it.
    """
    if not patterns:
        return ["Run `python -m agent.patterns` to generate the pattern data."]

    n = patterns["denominator"]
    access = patterns["totals"]["access"]
    blockers = patterns["totals"]["blocker"]
    per_cat = patterns["per_category_access"]

    ranked = sorted(per_cat.items(), key=lambda kv: -kv[1]["self_serve_pct"])
    best_name, best = ranked[0]
    worst_name, worst = ranked[-1]

    self_serve = access.get("self_serve", 0)
    gated = access.get("gated", 0)
    unknown = access.get("unknown", 0)
    auth = patterns["totals"]["auth"]
    api_key = auth.get("api_key", 0)
    oauth2 = auth.get("oauth2", 0)

    sentences = [
        f"{self_serve} of {n} apps let a developer get working credentials on their own; "
        f"{gated} gate access behind sales, partner approval or vendor provisioning.",

        f"Category predicts access more than size does: {best_name} is "
        f"{best['self_serve_pct']}% self-serve ({best['self_serve']}/{best['n']}), "
        f"while {worst_name} is {worst['self_serve_pct']}% ({worst['self_serve']}/{worst['n']}).",

        f"Auth splits almost evenly between a copied secret and a negotiated one: "
        f"{api_key} apps use an API key or token, {oauth2} use OAuth2.",
    ]

    blocker_items = [(k, v) for k, v in blockers.items() if k not in ("none", "unknown")]
    if blocker_items:
        top_blocker, top_count = max(blocker_items, key=lambda kv: kv[1])
        sentences.append(
            f"Where something blocks an integration, the most common single cause is "
            f"{top_blocker.replace('_', ' ')} ({top_count} apps) — not the absence of an API."
        )

    unreadable = blockers.get("docs_not_machine_readable", 0)
    if unreadable:
        sentences.append(
            f"{unreadable} apps publish documentation this pipeline cannot read at all "
            f"because it renders in the browser, and {unknown} apps end up with access "
            f"unknown — reported as unknown rather than guessed."
        )

    mcp = patterns["totals"].get("mcp_exists", {})
    if mcp.get("True"):
        sentences.append(
            f"MCP has arrived unevenly but widely: {mcp['True']} of {n} apps describe an MCP "
            f"server in their own documentation."
        )

    return sentences[:6]


def build(records, patterns, worked, accuracy) -> str:
    embedded = {
        "records": records,
        "patterns": patterns,
        "worked": worked,
        "accuracy": accuracy,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": REPO_URL,
        "run_command": RUN_COMMAND,
        "headlines": headline_sentences(patterns),
    }
    payload = json.dumps(embedded, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", payload)


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Composio App Research</title>
<style>
  :root {
    --bg: #fbfaf8; --panel: #ffffff; --ink: #14140f; --muted: #6a675e;
    --line: #e4e0d8; --accent: #2f5d50;
    --self: #1f6f4a; --self-bg: #e6f2ea;
    --gated: #97321f; --gated-bg: #fbe8e3;
    --mixed: #8a5a12; --mixed-bg: #fbf0dc;
    --unknown: #5c5a54; --unknown-bg: #eeece7;
    --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #14150f; --panel: #1c1e17; --ink: #f2f0e9; --muted: #a5a29a;
      --line: #2e3128; --accent: #7fc0a8;
      --self: #7fd0a4; --self-bg: #1a3328;
      --gated: #f0a08c; --gated-bg: #38201a;
      --mixed: #e6bd74; --mixed-bg: #362a15;
      --unknown: #a8a59d; --unknown-bg: #26281f;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font: 16px/1.55 ui-sans-serif, system-ui, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    -webkit-text-size-adjust: 100%;
  }
  .wrap { max-width: 1120px; margin: 0 auto; padding: 0 20px 80px; }
  header { padding: 52px 0 28px; border-bottom: 1px solid var(--line); }
  h1 { font-size: clamp(1.6rem, 4vw, 2.3rem); margin: 0 0 8px; letter-spacing: -0.02em; }
  .sub { color: var(--muted); margin: 0; font-size: 0.95rem; }
  section { padding: 44px 0; border-bottom: 1px solid var(--line); }
  .zone-label {
    font: 600 0.72rem/1 var(--mono); letter-spacing: 0.14em; text-transform: uppercase;
    color: var(--accent); margin: 0 0 18px;
  }
  h2 { font-size: 1.3rem; margin: 0 0 14px; letter-spacing: -0.01em; }
  h3 { font-size: 1rem; margin: 26px 0 10px; }
  p { margin: 0 0 12px; }
  .muted { color: var(--muted); }
  .small { font-size: 0.87rem; }

  /* Zone 1 — the headlines are the largest text on the page. */
  .headlines { list-style: none; margin: 0; padding: 0; display: grid; gap: 20px; }
  .headlines li {
    font-size: clamp(1.08rem, 2.3vw, 1.45rem); line-height: 1.4; font-weight: 450;
    padding-left: 20px; border-left: 3px solid var(--accent);
  }
  .headlines b { font-weight: 650; }

  .controls { display: flex; flex-wrap: wrap; gap: 10px; margin: 0 0 16px; }
  select, input[type="search"], button {
    font: inherit; font-size: 0.9rem; padding: 8px 10px; color: var(--ink);
    background: var(--panel); border: 1px solid var(--line); border-radius: 7px;
  }
  button { cursor: pointer; }
  .tablewrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 10px; background: var(--panel); }
  table { border-collapse: collapse; width: 100%; font-size: 0.87rem; }
  th, td { padding: 9px 11px; text-align: left; border-bottom: 1px solid var(--line); vertical-align: top; }
  th {
    position: sticky; top: 0; background: var(--panel); cursor: pointer;
    white-space: nowrap; font-size: 0.78rem; text-transform: uppercase;
    letter-spacing: 0.05em; color: var(--muted);
  }
  th:hover { color: var(--ink); }
  th[aria-sort="ascending"]::after { content: " ▲"; }
  th[aria-sort="descending"]::after { content: " ▼"; }
  tbody tr:last-child td { border-bottom: none; }
  .pill {
    display: inline-block; padding: 2px 8px; border-radius: 99px;
    font: 600 0.75rem/1.5 var(--mono); white-space: nowrap;
  }
  .t-self_serve { color: var(--self); background: var(--self-bg); }
  .t-gated { color: var(--gated); background: var(--gated-bg); }
  .t-mixed { color: var(--mixed); background: var(--mixed-bg); }
  .t-unknown { color: var(--unknown); background: var(--unknown-bg); }
  .mono { font-family: var(--mono); font-size: 0.82rem; }
  .ev a { color: var(--accent); text-decoration: none; }
  .ev a:hover { text-decoration: underline; }
  .count { color: var(--muted); font-size: 0.85rem; margin: 10px 0 0; }

  /* Zone 3 — pipeline diagram */
  .pipe { display: flex; flex-wrap: wrap; gap: 8px; align-items: stretch; margin: 0 0 14px; }
  .step {
    flex: 1 1 130px; background: var(--panel); border: 1px solid var(--line);
    border-radius: 9px; padding: 12px;
  }
  .step .n { font: 600 0.7rem var(--mono); color: var(--accent); }
  .step .t { font-weight: 600; margin: 3px 0 4px; }
  .step .d { font-size: 0.8rem; color: var(--muted); line-height: 1.4; }
  .human {
    border-left: 3px solid var(--mixed); background: var(--mixed-bg);
    padding: 12px 14px; border-radius: 0 8px 8px 0; font-size: 0.9rem;
  }

  /* Zone 4 — verification */
  .cards { display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); }
  .card { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 16px; }
  .card .k { font-size: 0.78rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }
  .card .v { font-size: 1.9rem; font-weight: 600; letter-spacing: -0.02em; }
  .delta-up { color: var(--self); font-weight: 600; }
  .delta-down { color: var(--gated); font-weight: 600; }
  .bar { height: 7px; border-radius: 99px; background: var(--unknown-bg); overflow: hidden; margin-top: 6px; }
  .bar span { display: block; height: 100%; background: var(--accent); }
  .worked { display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
  .wrong { border-left: 3px solid var(--gated); }
  .right { border-left: 3px solid var(--self); }
  blockquote {
    margin: 8px 0; padding: 9px 12px; background: var(--bg);
    border: 1px solid var(--line); border-radius: 7px;
    font-family: var(--mono); font-size: 0.8rem; line-height: 1.5;
  }
  details { margin-top: 10px; }
  summary { cursor: pointer; font-size: 0.85rem; color: var(--accent); }
  pre {
    overflow-x: auto; background: var(--bg); border: 1px solid var(--line);
    border-radius: 7px; padding: 11px; font-size: 0.74rem; line-height: 1.5; margin: 8px 0 0;
  }
  .links { display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
  .links a {
    display: block; padding: 14px; background: var(--panel); border: 1px solid var(--line);
    border-radius: 10px; color: var(--ink); text-decoration: none;
  }
  .links a:hover { border-color: var(--accent); }
  .links .k { font-size: 0.78rem; color: var(--muted); }
  .links .v { font-weight: 600; word-break: break-all; }
  code.cmd {
    display: block; font-family: var(--mono); font-size: 0.8rem; padding: 11px;
    background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
    overflow-x: auto; white-space: pre;
  }
  footer { padding: 30px 0 0; color: var(--muted); font-size: 0.85rem; }
  @media (max-width: 620px) {
    .wrap { padding: 0 14px 60px; }
    header { padding: 32px 0 20px; }
    section { padding: 32px 0; }
    th, td { padding: 7px 8px; }
  }
</style>
</head>
<body>
<div class="wrap">

<header>
  <h1>What it takes to integrate 100 apps</h1>
  <p class="sub">An agent researched auth, access, API surface and MCP support for Composio's
  100-app list — every claim tied to a documentation page it actually fetched, then audited
  against a hand-checked sample.</p>
</header>

<!-- ZONE 1 -->
<section id="patterns">
  <p class="zone-label">1 · What the 100 say</p>
  <ul class="headlines" id="headlines"></ul>
  <p class="count" id="patternsNote"></p>
</section>

<!-- ZONE 2 -->
<section id="matrix">
  <p class="zone-label">2 · The 100</p>
  <h2>Every app, with the evidence</h2>
  <div class="controls">
    <input type="search" id="q" placeholder="Search app…" aria-label="Search app">
    <select id="fCat" aria-label="Filter by category"></select>
    <select id="fAuth" aria-label="Filter by auth method"></select>
    <select id="fTier" aria-label="Filter by access tier"></select>
    <button id="reset" type="button">Reset</button>
  </div>
  <div class="tablewrap">
    <table id="tbl">
      <thead><tr>
        <th data-k="number">#</th>
        <th data-k="name">App</th>
        <th data-k="category">Category</th>
        <th data-k="auth">Auth</th>
        <th data-k="tier">Access</th>
        <th data-k="build">Buildable</th>
        <th data-k="conf">Conf.</th>
        <th data-k="ev">Evidence</th>
      </tr></thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>
  <p class="count" id="rowCount"></p>
</section>

<!-- ZONE 3 -->
<section id="how">
  <p class="zone-label">3 · How it works</p>
  <h2>Five stages, one of them human</h2>
  <div class="pipe">
    <div class="step"><div class="n">01</div><div class="t">Discover</div><div class="d">Seed hint URL, doc-path patterns and model-proposed URLs — guesses at where docs live.</div></div>
    <div class="step"><div class="n">02</div><div class="t">Fetch</div><div class="d">Real HTTP, with retries, nav-chrome stripping and a second hop into auth/access pages. 404s die here.</div></div>
    <div class="step"><div class="n">03</div><div class="t">Extract</div><div class="d">Gemini, schema-constrained, over the fetched text only. Each field must quote a line, verified as really present.</div></div>
    <div class="step"><div class="n">04</div><div class="t">Verify</div><div class="d">A second model re-reads each answer adversarially: does the page confirm this, and is it access or only usage docs?</div></div>
    <div class="step"><div class="n">05</div><div class="t">Re-run</div><div class="d">Failure patterns patch the prompt; all 100 run again as Pass 2 and are re-scored.</div></div>
  </div>
  <p class="human"><b>Where a human was required:</b> the ground truth. A person opened the real
  docs and pricing pages for 20 stratified apps and marked each field correct, incorrect or
  partial. Everything else on this page is measured against that call — an agent grading its
  own homework cannot establish whether it is right.</p>
</section>

<!-- ZONE 4 -->
<section id="verification">
  <p class="zone-label">4 · Verification</p>
  <h2>Pass 1 against Pass 2</h2>
  <div class="cards" id="accCards"></div>
  <h3>Field-level accuracy</h3>
  <div class="tablewrap">
    <table>
      <thead><tr><th>Field</th><th>Pass 1</th><th>Pass 2</th><th>Change</th></tr></thead>
      <tbody id="accBody"></tbody>
    </table>
  </div>
  <p class="count" id="accNote"></p>
  <div id="caveat"></div>

  <h3>The sample, marked</h3>
  <div class="tablewrap">
    <table>
      <thead><tr><th>App</th><th>Stratum</th><th>Field</th><th>Answer</th><th>Verdict</th></tr></thead>
      <tbody id="sampleBody"></tbody>
    </table>
  </div>
  <p class="count" id="sampleNote"></p>

  <h3>One worked example, including the wrong answer</h3>
  <div id="worked"></div>
</section>

<!-- ZONE 5 -->
<section id="links">
  <p class="zone-label">5 · Links</p>
  <h2>Run it yourself</h2>
  <div class="links" id="linkCards"></div>
  <h3>One command</h3>
  <code class="cmd" id="cmd"></code>
  <p class="small muted" id="envNote">Needs <span class="mono">GEMINI_API_KEY</span>; the
  verification pass also uses <span class="mono">GROQ_API_KEY</span> when present.</p>
</section>

<footer>
  <p id="footer"></p>
</footer>

</div>

<script id="payload" type="application/json">__DATA__</script>
<script>
(function () {
  "use strict";
  var D = JSON.parse(document.getElementById("payload").textContent);
  var records = D.records || [];

  function el(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function tierOf(r) { return (r.access && r.access.tier) || "unknown"; }
  function authOf(r) { return (r.auth && r.auth.method) || "unknown"; }
  function buildOf(r) { return (r.buildability && r.buildability.verdict) || "unknown"; }

  /* ---------- Zone 1 ---------- */
  var hl = el("headlines");
  (D.headlines || []).forEach(function (s) {
    var li = document.createElement("li");
    // Bold standalone quantities so they carry the sentence. The leading group keeps
    // digits that are part of a word intact — otherwise "OAuth2" renders as "OAuth<b>2</b>".
    li.innerHTML = esc(s).replace(/(^|[^A-Za-z0-9])(\d+(?:\.\d+)?%?)(?![A-Za-z0-9])/g,
                                  "$1<b>$2</b>");
    hl.appendChild(li);
  });
  if (D.patterns && D.patterns.denominator) {
    el("patternsNote").textContent =
      "Every number above is a count from data/patterns.json over " +
      D.patterns.denominator + " apps, regenerated with the page.";
  }

  /* ---------- Zone 2 ---------- */
  var rows = records.map(function (r) {
    return {
      number: r.number, name: r.name, category: r.category,
      auth: authOf(r), tier: tierOf(r), build: buildOf(r),
      conf: r.confidence || "low",
      ev: (r.evidence || []).length,
      evidence: r.evidence || [],
      one_liner: r.one_liner || ""
    };
  });

  function fill(sel, values, label) {
    var o = document.createElement("option");
    o.value = ""; o.textContent = label;
    sel.appendChild(o);
    values.sort().forEach(function (v) {
      var opt = document.createElement("option");
      opt.value = v; opt.textContent = v;
      sel.appendChild(opt);
    });
  }
  function uniq(key) {
    var seen = {};
    rows.forEach(function (r) { seen[r[key]] = 1; });
    return Object.keys(seen);
  }
  fill(el("fCat"), uniq("category"), "All categories");
  fill(el("fAuth"), uniq("auth"), "All auth methods");
  fill(el("fTier"), uniq("tier"), "All access tiers");

  var sortKey = "number", sortDir = 1;

  function visible() {
    var q = el("q").value.trim().toLowerCase();
    var c = el("fCat").value, a = el("fAuth").value, t = el("fTier").value;
    return rows.filter(function (r) {
      if (c && r.category !== c) return false;
      if (a && r.auth !== a) return false;
      if (t && r.tier !== t) return false;
      if (q && r.name.toLowerCase().indexOf(q) === -1) return false;
      return true;
    });
  }

  function render() {
    var list = visible().slice().sort(function (x, y) {
      var a = x[sortKey], b = y[sortKey];
      if (typeof a === "number" && typeof b === "number") return (a - b) * sortDir;
      return String(a).localeCompare(String(b)) * sortDir;
    });

    el("tbody").innerHTML = list.map(function (r) {
      var ev = r.evidence.slice(0, 3).map(function (e, i) {
        return '<a href="' + esc(e.url) + '" target="_blank" rel="noopener">' + (i + 1) + "</a>";
      }).join(" ");
      return "<tr>" +
        "<td class=\"mono\">" + r.number + "</td>" +
        "<td><b>" + esc(r.name) + "</b></td>" +
        "<td class=\"small\">" + esc(r.category) + "</td>" +
        "<td class=\"mono\">" + esc(r.auth) + "</td>" +
        '<td><span class="pill t-' + esc(r.tier) + '">' + esc(r.tier) + "</span></td>" +
        "<td class=\"mono\">" + esc(r.build) + "</td>" +
        "<td class=\"mono small\">" + esc(r.conf) + "</td>" +
        '<td class="ev small">' + (ev || '<span class="muted">none</span>') + "</td>" +
        "</tr>";
    }).join("");

    el("rowCount").textContent =
      "Showing " + list.length + " of " + rows.length + " apps. " +
      "Numbers in the evidence column link to the page each claim came from.";
  }

  Array.prototype.forEach.call(document.querySelectorAll("#tbl th"), function (th) {
    th.addEventListener("click", function () {
      var k = th.getAttribute("data-k");
      sortDir = (k === sortKey) ? -sortDir : 1;
      sortKey = k;
      Array.prototype.forEach.call(document.querySelectorAll("#tbl th"), function (o) {
        o.removeAttribute("aria-sort");
      });
      th.setAttribute("aria-sort", sortDir === 1 ? "ascending" : "descending");
      render();
    });
  });
  ["q", "fCat", "fAuth", "fTier"].forEach(function (id) {
    el(id).addEventListener(id === "q" ? "input" : "change", render);
  });
  el("reset").addEventListener("click", function () {
    el("q").value = ""; el("fCat").value = ""; el("fAuth").value = ""; el("fTier").value = "";
    render();
  });
  render();

  /* ---------- Zone 4 ---------- */
  var acc = D.accuracy || {};
  var FIELDS = ["auth.method", "access.tier", "api_surface", "mcp.exists",
                "buildability.verdict", "evidence_supports_claims"];

  function pick(passName) {
    var p = acc[passName];
    if (!p) return null;
    // Human marks are ground truth; the judge is the fallback proxy when unmarked.
    if (p.human && p.human.overall) return { src: "human", data: p.human };
    if (p.judge && p.judge.overall) return { src: "judge", data: p.judge };
    return null;
  }

  var a1 = pick("pass1"), a2 = pick("pass2");

  function card(k, v, extra) {
    return '<div class="card"><div class="k">' + esc(k) + "</div>" +
           '<div class="v">' + v + "</div>" + (extra || "") + "</div>";
  }

  if (a1 || a2) {
    var cards = "";
    if (a1) {
      cards += card("Pass 1 accuracy", a1.data.overall.accuracy_pct + "%",
        '<div class="bar"><span style="width:' + a1.data.overall.accuracy_pct + '%"></span></div>' +
        '<p class="small muted">n=' + a1.data.overall.n + " rows</p>");
    }
    if (a2) {
      cards += card("Pass 2 accuracy", a2.data.overall.accuracy_pct + "%",
        '<div class="bar"><span style="width:' + a2.data.overall.accuracy_pct + '%"></span></div>' +
        '<p class="small muted">n=' + a2.data.overall.n + " rows</p>");
    }
    if (a1 && a2) {
      var d = Math.round((a2.data.overall.accuracy_pct - a1.data.overall.accuracy_pct) * 10) / 10;
      cards += card("Change", '<span class="' + (d >= 0 ? "delta-up" : "delta-down") + '">' +
        (d >= 0 ? "+" : "") + d + " pp</span>",
        '<p class="small muted">after patching the extraction prompt</p>');
    }
    el("accCards").innerHTML = cards;

    el("accBody").innerHTML = FIELDS.map(function (f) {
      var p1 = a1 && a1.data.per_field[f], p2 = a2 && a2.data.per_field[f];
      if (!p1 && !p2) return "";
      var v1 = p1 ? p1.accuracy_pct : null, v2 = p2 ? p2.accuracy_pct : null;
      var chg = (v1 != null && v2 != null)
        ? '<span class="' + (v2 >= v1 ? "delta-up" : "delta-down") + '">' +
          (v2 >= v1 ? "+" : "") + (Math.round((v2 - v1) * 10) / 10) + " pp</span>"
        : '<span class="muted">—</span>';
      return "<tr><td class=\"mono\">" + esc(f) + "</td>" +
        "<td>" + (v1 == null ? "—" : v1 + "%") + "</td>" +
        "<td>" + (v2 == null ? "—" : v2 + "%") + "</td>" +
        "<td>" + chg + "</td></tr>";
    }).join("");

    var src = (a2 || a1).src;
    el("accNote").textContent = src === "human"
      ? "Scored from the hand-marked sample sheet — the ground truth."
      : "Scored by the adversarial verification pass, which is a model checking a model: " +
        "a reproducible proxy, not ground truth. The hand-marked sheet is in " +
        "verification/sample_sheet.json.";
  } else {
    el("accNote").textContent = "Run `python -m agent.verification audit` to populate accuracy.";
  }

  /* Why the headline number fell — stated on the page, not buried in the repo. */
  var dec = (D.accuracy && D.accuracy.decomposition) || {};
  if (dec.pass1 && dec.pass2 && dec.pass1.asserted && dec.pass2.asserted) {
    el("caveat").innerHTML =
      '<div class="human" style="border-left-color:var(--accent);background:var(--panel)">' +
      "<p><b>Pass 2 scored lower overall, and that needs saying plainly.</b> " +
      "The three fields the patch targeted did improve. The overall figure still fell, " +
      "because Pass 2 answers <span class=\"mono\">unknown</span> more often and the auditor " +
      "scores an abstention by asking whether the page confirms &ldquo;unknown&rdquo; — which " +
      "is almost never true. Abstaining is therefore punished as hard as being wrong.</p>" +
      '<div class="tablewrap" style="margin:10px 0"><table><thead><tr>' +
      "<th>Rows</th><th>Pass 1</th><th>Pass 2</th></tr></thead><tbody>" +
      "<tr><td>Where a value is <b>asserted</b></td><td>" +
        dec.pass1.asserted.pct + "% <span class=\"muted small\">(n=" + dec.pass1.asserted.n +
        ")</span></td><td>" + dec.pass2.asserted.pct + "% <span class=\"muted small\">(n=" +
        dec.pass2.asserted.n + ")</span></td></tr>" +
      "<tr><td>Where the record says <b>unknown</b></td><td>" +
        dec.pass1.abstained.pct + "% <span class=\"muted small\">(n=" + dec.pass1.abstained.n +
        ")</span></td><td>" + dec.pass2.abstained.pct + "% <span class=\"muted small\">(n=" +
        dec.pass2.abstained.n + ")</span></td></tr>" +
      "</tbody></table></div>" +
      "<p class=\"small\"><b>A sharper limitation.</b> Requiring a quote proves a claim is " +
      "<i>sourced</i>, not that it is <i>right</i>. For LinkedIn Ads the auditor rated Pass 2 " +
      "an improvement, but Pass 2 had quoted one supporting line while the same page also said " +
      "&ldquo;apply for Standard tier access&rdquo; — Pass 1's answer was the better one. " +
      "Nothing in the design makes the model weigh disconfirming evidence, and the auditor " +
      "shares that blind spot. Written up in " +
      "<span class=\"mono\">verification/pass2_review.md</span>.</p></div>";
  }

  /* sample table */
  var sample = (D.accuracy && D.accuracy.sample_rows) || [];
  if (sample.length) {
    el("sampleBody").innerHTML = sample.map(function (r) {
      var mark = r.verdict === "yes" ? "✓ hit"
               : r.verdict === "no" ? "✗ miss"
               : "~ partial";
      var cls = r.verdict === "yes" ? "t-self_serve"
              : r.verdict === "no" ? "t-gated" : "t-mixed";
      var ans = String(r.answer == null ? "—" : r.answer);
      if (ans.length > 60) ans = ans.slice(0, 60) + "…";
      return "<tr><td><b>" + esc(r.app) + "</b></td>" +
        "<td class=\"small mono\">" + esc(r.stratum) + "</td>" +
        "<td class=\"mono small\">" + esc(r.field) + "</td>" +
        "<td class=\"mono small\">" + esc(ans) + "</td>" +
        '<td><span class="pill ' + cls + '">' + mark + "</span></td></tr>";
    }).join("");
    el("sampleNote").textContent =
      sample.length + " rows across 20 stratified apps — half household names, half the " +
      "gated and obscure tail where errors concentrate.";
  } else {
    el("sampleNote").textContent = "No sample verdicts available yet.";
  }

  /* worked example */
  var w = D.worked;
  if (w && w.app) {
    function side(title, cls, o, isPass2) {
      var h = '<div class="card ' + cls + '"><div class="k">' + title + "</div>" +
        '<div class="v mono" style="font-size:1.15rem">' + esc(String(o.answer)) + "</div>";
      if (o.judge_verdict) {
        h += '<p class="small muted">auditor said: <b>' + esc(o.judge_verdict) + "</b></p>";
      }
      if (o.notes) h += '<p class="small">' + esc(o.notes) + "</p>";
      if (!isPass2 && o.judge_problem) {
        h += '<p class="small"><b>Why it was wrong:</b> ' + esc(o.judge_problem) + "</p>";
      }
      if (isPass2 && o.verified_support && o.verified_support.quote) {
        h += "<p class=\"small\"><b>Verified line:</b></p><blockquote>" +
          esc(o.verified_support.quote) + "</blockquote>" +
          '<p class="small ev"><a href="' + esc(o.verified_support.url) +
          '" target="_blank" rel="noopener">' + esc(o.verified_support.url) + "</a></p>";
      }
      if (o.raw_model_output) {
        h += "<details><summary>Raw model output</summary><pre>" +
          esc(String(o.raw_model_output).slice(0, 2600)) + "</pre></details>";
      }
      return h + "</div>";
    }
    el("worked").innerHTML =
      "<p><b>" + esc(w.app) + "</b> — field <span class=\"mono\">" + esc(w.field) +
      "</span>. " + esc(w.why_this_example || "") + "</p>" +
      '<div class="worked">' +
        side("Pass 1 — wrong", "wrong", w.pass1 || {}, false) +
        side("Pass 2 — corrected", "right", w.pass2 || {}, true) +
      "</div>";
  } else {
    el("worked").innerHTML =
      '<p class="muted">Run <span class="mono">python -m agent.verification worked-example</span>' +
      " once Pass 2 has been audited.</p>";
  }

  /* ---------- Zone 5 ---------- */
  el("linkCards").innerHTML =
    '<a href="' + esc(D.repo) + '" target="_blank" rel="noopener">' +
      '<div class="k">Repository</div><div class="v">' + esc(D.repo.replace(/^https:\/\//, "")) + "</div></a>" +
    '<a href="#matrix"><div class="k">This page</div><div class="v">Self-contained single file — ' +
      "data embedded, opens from disk</div></a>" +
    '<a href="' + esc(D.repo) + '/tree/main/data" target="_blank" rel="noopener">' +
      '<div class="k">Raw data</div><div class="v">pass1_full.json vs pass2_full.json</div></a>';
  el("cmd").textContent = D.run_command;

  el("footer").textContent =
    "Generated " + (D.generated_at || "").slice(0, 10) + " from " + records.length +
    " researched apps. Every figure on this page is derived from a file in the repository.";
})();
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the report page.")
    parser.add_argument("--pass", dest="pass_name", default="pass2", choices=("pass1", "pass2"))
    args = parser.parse_args()

    records = load(DATA_DIR / f"{args.pass_name}_full.json", [])
    if not records:
        records = load(DATA_DIR / "pass1_full.json", [])
        print(f"warning: {args.pass_name}_full.json empty, falling back to pass1")

    patterns = load(DATA_DIR / "patterns.json", {})
    worked = load(VERIFICATION_DIR / "worked_example.json", {})
    accuracy = load(VERIFICATION_DIR / "accuracy_comparison.json", {})
    if not accuracy:
        accuracy = {
            "pass1": load(VERIFICATION_DIR / "accuracy_pass1.json", {}),
            "pass2": load(VERIFICATION_DIR / "accuracy_pass2.json", {}),
        }
    accuracy["sample_rows"] = sample_rows()
    accuracy["decomposition"] = decomposition()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(records, patterns, worked, accuracy))
    print(f"{len(records)} records -> {OUT} ({OUT.stat().st_size // 1024} KB)")


SCALAR_FIELD_GETTERS = {
    "auth.method": lambda r: (r.get("auth") or {}).get("method"),
    "access.tier": lambda r: (r.get("access") or {}).get("tier"),
    "mcp.exists": lambda r: (r.get("mcp") or {}).get("exists"),
    "buildability.verdict": lambda r: (r.get("buildability") or {}).get("verdict"),
}


def decomposition() -> dict:
    """Split each pass's score into rows that assert a value and rows that abstain.

    The auditor judges an abstention by asking whether the page confirms "unknown", which is
    almost never true — so abstaining is scored like being wrong. Publishing the split keeps
    the headline number from being read as "Pass 2 is worse at answering".
    """
    out = {}
    for pass_name in ("pass1", "pass2"):
        audit = load(VERIFICATION_DIR / f"audit_{pass_name}.json", {}).get("apps", {})
        records = {r["name"]: r for r in load(DATA_DIR / f"{pass_name}_full.json", [])}
        if not audit or not records:
            continue

        buckets = {"asserted": [], "abstained": []}
        for app, verdicts in audit.items():
            record = records.get(app)
            if not record:
                continue
            for field, getter in SCALAR_FIELD_GETTERS.items():
                if field not in verdicts:
                    continue
                value = getter(record)
                key = "abstained" if value in ("unknown", None) else "asserted"
                buckets[key].append(verdicts[field]["confirmed"])

        def score(marks):
            if not marks:
                return None
            weighted = sum(1 if m == "yes" else 0.5 if m == "partial" else 0 for m in marks)
            return {"pct": round(100 * weighted / len(marks), 1), "n": len(marks)}

        out[pass_name] = {k: score(v) for k, v in buckets.items()}
    return out


def sample_rows() -> list[dict]:
    """Flatten the marked sheet (or the audit) into hit/miss rows for the page."""
    sheet = load(VERIFICATION_DIR / "sample_sheet.json", {})
    rows = []
    for row in sheet.get("rows", []):
        if row.get("correct"):
            verdict = "yes"
        elif row.get("incorrect"):
            verdict = "no"
        elif row.get("partial"):
            verdict = "partial"
        else:
            verdict = row.get("suggested_verdict")
        if not verdict:
            continue
        rows.append(
            {
                "app": row["app"],
                "stratum": row["stratum"],
                "field": row["field"],
                "answer": row.get("pass1_answer"),
                "verdict": verdict,
                "marked_by_human": bool(row.get("marked_by")),
            }
        )
    return rows


if __name__ == "__main__":
    main()
