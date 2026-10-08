"""htmldiff: generate an HTML diff page from two versions of a text file

Given two text files, this script generates an HTML page modeled after
VS Code's diff viewer. It supports side-by-side or one-column layout,
word-level highlighting, wrapped paragraphs that stay aligned, Prev/Next
navigation, and the ability to collapse unchanged sections.

This script embeds both texts in the output page, with the diff getting
computed by the browser at runtime.

Usage:
    htmldiff ORIGINAL REVISED [-o OUT.html] [-t TITLE]
             [--left-label TEXT] [--right-label TEXT] [--open]

To change the page, edit TEMPLATE at the bottom of this file.
It is ordinary HTML/CSS/JS; __TITLE__ and __DATA__ are filled in here.
"""
import argparse
import html
import json
import os
import sys
import webbrowser


def read_text(path):
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as e:
        sys.exit(f"htmldiff: cannot read {path}: {e.strerror}")
    if b"\0" in raw[:8192]:
        sys.exit(f"htmldiff: {path} looks like a binary file, not text")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        print(f"htmldiff: warning: {path} is not valid UTF-8; "
              "some characters may show as �", file=sys.stderr)
        return raw.decode("utf-8", errors="replace")


def stem(path):
    return os.path.splitext(os.path.basename(path))[0]


def main():
    ap = argparse.ArgumentParser(
        prog="htmldiff",
        description="Make a shareable, VS Code-style diff page from two text files.")
    ap.add_argument("original", help="the older version")
    ap.add_argument("revised", help="the newer version")
    ap.add_argument("-o", "--output",
                    help="output file (default: ORIGINAL-vs-REVISED.html in the current folder)")
    ap.add_argument("-t", "--title", default="Compare versions",
                    help='page title (default: "%(default)s")')
    ap.add_argument("--left-label", default="Original version",
                    help='heading for the original (default: "%(default)s")')
    ap.add_argument("--right-label", default="Revised version",
                    help='heading for the revision (default: "%(default)s")')
    ap.add_argument("--open", action="store_true", help="open the page in a browser afterwards")
    args = ap.parse_args()

    left, right = read_text(args.original), read_text(args.revised)
    out = args.output or f"{stem(args.original)}-vs-{stem(args.revised)}.html"

    # The browser compares the files line by line with an algorithm whose
    # time and memory grow with (lines in one) x (lines in the other).
    cells = left.count("\n") * right.count("\n")
    if cells > 25_000_000:
        print("htmldiff: warning: these files are large; the page may take a "
              "while to load and use a lot of memory", file=sys.stderr)

    data = {
        "left": {"name": os.path.basename(args.original), "label": args.left_label, "text": left},
        "right": {"name": os.path.basename(args.revised), "label": args.right_label, "text": right},
    }
    # "</" is escaped so text containing "</script>" cannot end the data block.
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.replace("__TITLE__", html.escape(args.title)).replace("__DATA__", blob, 1)
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(os.path.abspath(out))
    if args.open:
        webbrowser.open("file://" + os.path.abspath(out))


TEMPLATE = r'''<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root {
  --bg: #1e1e1e; --fg: #d4d4d4; --muted: #858585; --border: #3c3c3c;
  --bar: #252526; --btn: #333337; --btn-hover: #45454b; --accent: #3794ff;
  --del-line: rgba(255, 0, 0, 0.16); --del-word: rgba(255, 70, 70, 0.42);
  --ins-line: rgba(155, 185, 85, 0.17); --ins-word: rgba(156, 204, 44, 0.42);
  --del-mark: #e05252; --ins-mark: #81b88b;
  --filler: rgba(204, 204, 204, 0.11);
  --collapsed: #2a2d3a;
  --lh: 1.6;
}
:root[data-theme="light"] {
  --bg: #ffffff; --fg: #1f1f1f; --muted: #6e7781; --border: #d0d7de;
  --bar: #f3f3f3; --btn: #e4e4e4; --btn-hover: #d4d4d4; --accent: #0969da;
  --del-line: rgba(255, 0, 0, 0.09); --del-word: rgba(255, 0, 0, 0.24);
  --ins-line: rgba(155, 185, 85, 0.16); --ins-word: rgba(120, 180, 20, 0.36);
  --del-mark: #d1242f; --ins-mark: #4c9a2a;
  --filler: rgba(34, 34, 34, 0.08);
  --collapsed: #e8eef8;
}
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--bg); color: var(--fg); }
body {
  font: 14px/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  padding-right: 16px; /* room for the overview ruler */
}

/* ---------- header ---------- */
#top { position: sticky; top: 0; z-index: 10; background: var(--bar); border-bottom: 1px solid var(--border); }
#toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 14px; padding: 8px 12px; }
#toolbar h1 { font-size: 15px; font-weight: 600; margin: 0 8px 0 0; }
.group { display: flex; align-items: center; gap: 4px; }
button, .seg label {
  font: inherit; color: var(--fg); background: var(--btn); border: 1px solid var(--border);
  border-radius: 4px; padding: 4px 10px; cursor: pointer; user-select: none;
}
button, .seg label { white-space: nowrap; }
button:hover, .seg label:hover { background: var(--btn-hover); }
.seg { display: inline-flex; }
.seg input { position: absolute; opacity: 0; pointer-events: none; }
.seg label { border-radius: 0; margin-left: -1px; }
.seg label:first-of-type { border-radius: 4px 0 0 4px; margin-left: 0; }
.seg label:last-of-type { border-radius: 0 4px 4px 0; }
.seg input:checked + label { background: var(--accent); border-color: var(--accent); color: #fff; }
.seg input:focus-visible + label, button:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.check { display: inline-flex; align-items: center; gap: 5px; cursor: pointer; user-select: none; }
#counter { min-width: 8.5em; text-align: center; font-variant-numeric: tabular-nums; }
.spacer { flex: 1; }

.help { padding: 10px 14px; background: var(--bar); border-bottom: 1px solid var(--border); font-size: 14px; line-height: 1.55; }
#helpdlg { max-width: 640px; background: var(--bar); color: var(--fg); border: 1px solid var(--border); border-radius: 8px; padding: 0; }
#helpdlg::backdrop { background: rgba(0, 0, 0, 0.45); }
#helpdlg .help { border: 0; background: none; }
#helpdlg form { text-align: right; padding: 0 14px 12px; }
.help p { margin: 0 0 4px; }
.help .swatch { display: inline-block; padding: 0 5px; border-radius: 3px; }
.help .sw-del { background: var(--del-word); }
.help .sw-ins { background: var(--ins-word); }
.help .sw-fill { background: repeating-linear-gradient(-45deg, var(--filler) 0 2px, transparent 2px 7px); border: 1px solid var(--border); }
.help kbd { border: 1px solid var(--border); border-radius: 3px; padding: 0 4px; font-size: 12px; background: var(--bg); }

#heads { position: sticky; z-index: 9; background: var(--bar); border-bottom: 1px solid var(--border); display: grid; grid-template-columns: 1fr 1fr; border-top: 1px solid var(--border); font-size: 13px; }
#heads div { padding: 5px 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#heads div + div { border-left: 1px solid var(--border); }
#heads .name { font-weight: 600; }
#heads .sub { color: var(--muted); margin-left: 6px; }
body.inline #heads { grid-template-columns: 1fr; }

/* ---------- diff body ---------- */
#diff { --ln: 3.6em; }
#diff { font: 16px/var(--lh) Georgia, "Iowan Old Style", "Palatino Linotype", "Times New Roman", serif; }
.row { display: grid; grid-template-columns: var(--ln) 1.4em minmax(0, 1fr); }
.inline .row { grid-template-columns: var(--ln) var(--ln) 1.4em minmax(0, 1fr); }
.ln {
  color: var(--muted); text-align: right; padding-right: 8px; user-select: none;
  font-family: Menlo, Consolas, "DejaVu Sans Mono", monospace; font-size: 0.8em;
  line-height: calc(var(--lh) * 1.25em); /* same line box as the text beside it */
}
.ind { color: var(--muted); user-select: none; text-align: center; }
.txt { min-height: calc(var(--lh) * 1em); padding-right: 14px; }
.wrap .txt { white-space: pre-wrap; overflow-wrap: anywhere; }
.nowrap .txt { white-space: pre; }

.row.del, .row.mod-l { background: var(--del-line); }
.row.ins, .row.mod-r { background: var(--ins-line); }
.row.del .ind, .row.mod-l .ind { color: var(--del-mark); }
.row.ins .ind, .row.mod-r .ind { color: var(--ins-mark); }
.row.fill { background: repeating-linear-gradient(-45deg, var(--filler) 0 2px, transparent 2px 9px); }
.w-del { background: var(--del-word); border-radius: 2px; }
.w-ins { background: var(--ins-word); border-radius: 2px; }
.row.flash { animation: flash 1.2s ease-out; }
@keyframes flash { from { box-shadow: inset 0 0 0 2px var(--accent); } to { box-shadow: inset 0 0 0 2px transparent; } }

.collapsed {
  background: var(--collapsed); color: var(--accent); cursor: pointer; text-align: center;
  padding: 4px; font: 13px/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);
}
.collapsed:hover { text-decoration: underline; }
#diff.nowrap .collapsed { text-align: left; padding-left: calc(var(--ln) + 1.6em); }

/* Side by side with wrapping: one CSS grid, so each row is as tall as the
   taller of its two sides and paragraphs stay aligned. */
#diff.sbs.wrap { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
#diff.sbs.wrap .pane, #diff.sbs.wrap .pane-inner { display: contents; }
#diff.sbs.wrap .right .collapsed { display: none; }
#diff.sbs.wrap .left .collapsed { grid-column: 1 / -1; }
#diff.sbs .right .row { border-left: 1px solid var(--border); }

/* Side by side without wrapping: two panes that each scroll sideways. Every
   row is a single line, so they line up without a shared grid. */
#diff.sbs.nowrap { display: flex; }
#diff.sbs.nowrap .pane { flex: 1 1 0; min-width: 0; overflow-x: auto; }
#diff.sbs.nowrap .pane-inner { width: max-content; min-width: 100%; }
#diff.nowrap .ln { position: sticky; left: 0; background: var(--bg); z-index: 1; }
#diff.inline.nowrap { overflow-x: auto; }
#diff.inline.nowrap .pane-inner { width: max-content; min-width: 100%; }

/* ---------- overview ruler ---------- */
#ruler { position: fixed; right: 0; bottom: 0; width: 16px; background: var(--bar); border-left: 1px solid var(--border); cursor: pointer; z-index: 5; }
#ruler .mk { position: absolute; width: 6px; min-height: 3px; }
#ruler .mk.d { left: 1px; background: var(--del-mark); }
#ruler .mk.i { right: 1px; background: var(--ins-mark); }
#ruler .view { position: absolute; left: 0; right: 0; background: rgba(128, 128, 128, 0.22); border: 1px solid rgba(128, 128, 128, 0.4); pointer-events: none; }

@media (max-width: 700px) {
  /* On phones the toolbar scrolls away and Prev/Next float at the bottom. */
  #top, #heads { position: static; }
  #toolbar h1 { width: 100%; }
  #nav {
    position: fixed; bottom: 14px; left: 50%; transform: translateX(-50%); z-index: 20;
    background: var(--bar); border: 1px solid var(--border); border-radius: 8px; padding: 6px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
  }
  #diff { padding-bottom: 70px; }
  #diff { font-size: 15px; }
  #diff { --ln: 2.6em; }
}
</style>
</head>
<body>
<div id="top">
  <div id="toolbar">
    <h1>__TITLE__</h1>
    <div class="group" id="nav" title="Jump between changes (keyboard: N / P)">
      <button id="prev" aria-label="Previous change">&#9650; Prev</button>
      <span id="counter"></span>
      <button id="next" aria-label="Next change">Next &#9660;</button>
    </div>
    <div class="seg" title="Show the two versions next to each other, or merged into one column">
      <input type="radio" name="layout" id="lay-sbs" value="sbs"><label for="lay-sbs">Side by side</label>
      <input type="radio" name="layout" id="lay-inline" value="inline"><label for="lay-inline">One column</label>
    </div>
    <label class="check" title="Wrap long lines so you don't need to scroll sideways"><input type="checkbox" id="wrap"> Wrap lines</label>
    <label class="check" title="Hide long stretches of text that did not change"><input type="checkbox" id="hide"> Only show changed parts</label>
    <span class="spacer"></span>
    <button id="theme" title="Switch between dark and light colours">Light / dark</button>
    <button id="helpbtn" title="What do the colours mean?">Help</button>
  </div>
</div>
<div id="help" class="help" hidden>
    <p>This page compares two versions of the same text. <span id="help-layout"></span></p>
    <p><span class="swatch sw-del">Red</span> marks text that was removed, and <span class="swatch sw-ins">green</span> marks text that was added. Lines with a pale tint were edited; the brighter highlight inside them picks out the exact words that changed. <span class="swatch sw-fill">&nbsp;&nbsp;&nbsp;&nbsp;</span> Striped space means that version has nothing there, and it keeps the two sides lined up.</p>
    <p>Use <b>Prev</b> / <b>Next</b> (or the <kbd>P</kbd> and <kbd>N</kbd> keys) to jump from change to change. The coloured marks in the thin strip on the far right show where every change is; click the strip to jump there.</p>
</div>
<div id="heads"></div>
<dialog id="helpdlg"><div></div><form method="dialog"><button>Close</button></form></dialog>
<div id="diff"></div>
<div id="ruler"></div>

<script id="diff-data" type="application/json">__DATA__</script>
<script>
(function () {
  "use strict";
  const DATA = JSON.parse(document.getElementById("diff-data").textContent);
  const CONTEXT = 3; // unchanged lines kept around each change when hiding

  function splitLines(t) {
    const lines = t.replace(/\r\n?/g, "\n").split("\n");
    if (lines.length > 1 && lines[lines.length - 1] === "") lines.pop();
    return lines;
  }
  const A = splitLines(DATA.left.text), B = splitLines(DATA.right.text);

  // ---------- generic LCS diff ----------
  // Returns ops: ["=", i, j], ["-", i], ["+", j]. Deletions come before
  // insertions within a changed stretch.
  function diffSeq(a, b) {
    let s = 0;
    while (s < a.length && s < b.length && a[s] === b[s]) s++;
    let ea = a.length, eb = b.length;
    while (ea > s && eb > s && a[ea - 1] === b[eb - 1]) { ea--; eb--; }
    const n = ea - s, m = eb - s, W = m + 1;
    const dp = new Uint32Array((n + 1) * (m + 1));
    for (let i = n - 1; i >= 0; i--)
      for (let j = m - 1; j >= 0; j--)
        dp[i * W + j] = a[s + i] === b[s + j] ? dp[(i + 1) * W + j + 1] + 1
          : Math.max(dp[(i + 1) * W + j], dp[i * W + j + 1]);
    const ops = [];
    for (let k = 0; k < s; k++) ops.push(["=", k, k]);
    let i = 0, j = 0;
    while (i < n || j < m) {
      if (i < n && j < m && a[s + i] === b[s + j]) { ops.push(["=", s + i, s + j]); i++; j++; }
      else if (i < n && (j === m || dp[(i + 1) * W + j] >= dp[i * W + j + 1])) { ops.push(["-", s + i]); i++; }
      else { ops.push(["+", s + j]); j++; }
    }
    for (let k = 0; ea + k < a.length; k++) ops.push(["=", ea + k, eb + k]);
    return ops;
  }

  const TOKEN = /\s+|[\p{L}\p{N}_]+(?:['’][\p{L}\p{N}_]+)*|[^\s]/gu;
  const tokens = s => s.match(TOKEN) || [];

  // Share of words two lines have in common (0..1), used to decide which
  // removed line corresponds to which added line.
  function similarity(a, b) {
    const ta = tokens(a).filter(t => t.trim()), tb = tokens(b).filter(t => t.trim());
    if (!ta.length && !tb.length) return 1;
    if (!ta.length || !tb.length) return 0;
    let same = 0;
    for (const op of diffSeq(ta, tb)) if (op[0] === "=") same++;
    return (2 * same) / (ta.length + tb.length);
  }

  // Word-level diff of two lines -> list of chunks {eq} or {del, ins}.
  function wordDiff(a, b) {
    const ta = tokens(a), tb = tokens(b);
    const chunks = [];
    for (const op of diffSeq(ta, tb)) {
      const last = chunks[chunks.length - 1];
      if (op[0] === "=") {
        if (last && last.eq !== undefined) last.eq += ta[op[1]];
        else chunks.push({ eq: ta[op[1]] });
      } else {
        const c = last && last.eq === undefined ? last : (chunks.push({ del: "", ins: "" }), chunks[chunks.length - 1]);
        if (op[0] === "-") c.del += ta[op[1]]; else c.ins += tb[op[1]];
      }
    }
    // Fold tiny unchanged bits (a space, a comma, "a") that sit between two
    // changes into the change, so the highlight reads as one phrase.
    let merged = true;
    while (merged) {
      merged = false;
      for (let k = 1; k < chunks.length - 1; k++) {
        const e = chunks[k], p = chunks[k - 1], n = chunks[k + 1];
        if (e.eq === undefined || p.eq !== undefined || n.eq !== undefined) continue;
        if (e.eq.trim().length > 3) continue;
        chunks.splice(k - 1, 3, { del: p.del + e.eq + n.del, ins: p.ins + e.eq + n.ins });
        merged = true;
        break;
      }
    }
    // Within a change, peel off characters shared at the start or end when
    // they form a whole word or a long run, e.g. "accusations" -> "accusations1"
    // highlights only the "1".
    for (let k = chunks.length - 1; k >= 0; k--) {
      const c = chunks[k];
      if (c.eq !== undefined || !c.del || !c.ins) continue;
      let pre = 0;
      while (pre < c.del.length && pre < c.ins.length && c.del[pre] === c.ins[pre]) pre++;
      if (pre < 4 && !(pre && /\s/.test(c.del[pre - 1]))) pre = 0;
      let suf = 0;
      while (suf < c.del.length - pre && suf < c.ins.length - pre &&
             c.del[c.del.length - 1 - suf] === c.ins[c.ins.length - 1 - suf]) suf++;
      if (suf < 4 && !(suf && /\s/.test(c.del[c.del.length - suf]))) suf = 0;
      if (!pre && !suf) continue;
      const parts = [];
      if (pre) parts.push({ eq: c.del.slice(0, pre) });
      parts.push({ del: c.del.slice(pre, c.del.length - suf), ins: c.ins.slice(pre, c.ins.length - suf) });
      if (suf) parts.push({ eq: c.del.slice(c.del.length - suf) });
      chunks.splice(k, 1, ...parts);
    }
    return chunks;
  }

  // ---------- build aligned rows ----------
  // Row: {o, n} = old/new line index or null; kind = eq | mod | del | ins;
  // h = index of the change it belongs to.
  const rows = [];
  const hunks = [];
  {
    const ops = diffSeq(A, B);
    let k = 0;
    while (k < ops.length) {
      if (ops[k][0] === "=") { rows.push({ kind: "eq", o: ops[k][1], n: ops[k][2], h: -1 }); k++; continue; }
      const dels = [], inss = [];
      while (k < ops.length && ops[k][0] !== "=") {
        if (ops[k][0] === "-") dels.push(ops[k][1]); else inss.push(ops[k][1]);
        k++;
      }
      const h = hunks.length;
      hunks.push({ dels: dels.length, inss: inss.length });
      for (const r of alignHunk(dels, inss)) { r.h = h; rows.push(r); }
    }
  }

  // Pair up removed and added lines inside one change, keeping order and
  // maximising total similarity. Unpaired lines get striped filler opposite.
  function alignHunk(dels, inss) {
    const p = dels.length, q = inss.length, W = q + 1;
    const sim = new Float64Array(p * q);
    for (let i = 0; i < p; i++) for (let j = 0; j < q; j++) {
      const s = similarity(A[dels[i]], B[inss[j]]);
      const blankA = !A[dels[i]].trim(), blankB = !B[inss[j]].trim();
      sim[i * q + j] = blankA !== blankB ? 0 : s >= 0.35 ? s : 0;
    }
    const best = new Float64Array((p + 1) * (q + 1));
    for (let i = p - 1; i >= 0; i--) for (let j = q - 1; j >= 0; j--) {
      let v = Math.max(best[(i + 1) * W + j], best[i * W + j + 1]);
      if (sim[i * q + j] > 0) v = Math.max(v, best[(i + 1) * W + j + 1] + sim[i * q + j]);
      best[i * W + j] = v;
    }
    const out = [];
    let i = 0, j = 0;
    while (i < p || j < q) {
      if (i < p && j < q && sim[i * q + j] > 0 && best[i * W + j] === best[(i + 1) * W + j + 1] + sim[i * q + j]) {
        out.push({ kind: "mod", o: dels[i], n: inss[j] }); i++; j++;
      } else if (i < p && (j === q || best[i * W + j] === best[(i + 1) * W + j])) {
        out.push({ kind: "del", o: dels[i], n: null }); i++;
      } else {
        out.push({ kind: "ins", o: null, n: inss[j] }); j++;
      }
    }
    return out;
  }

  // ---------- HTML for one side of a row ----------
  const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const wdCache = new Map();
  function sideHtml(r, side) {
    if (r.kind === "eq") return esc(side === "l" ? A[r.o] : B[r.n]);
    if (r.kind === "del") return A[r.o] ? `<span class="w-del">${esc(A[r.o])}</span>` : "";
    if (r.kind === "ins") return B[r.n] ? `<span class="w-ins">${esc(B[r.n])}</span>` : "";
    let chunks = wdCache.get(r);
    if (!chunks) { chunks = wordDiff(A[r.o], B[r.n]); wdCache.set(r, chunks); }
    let html = "";
    for (const c of chunks) {
      if (c.eq !== undefined) html += esc(c.eq);
      else if (side === "l" && c.del) html += `<span class="w-del">${esc(c.del)}</span>`;
      else if (side === "r" && c.ins) html += `<span class="w-ins">${esc(c.ins)}</span>`;
    }
    return html;
  }

  // ---------- which unchanged stretches to hide ----------
  const expanded = new Set();
  function visibleItems() {
    // Returns a list of rows and {gap: id, count, rows} placeholders.
    if (!settings.hide) return rows.slice();
    const items = [];
    let k = 0;
    while (k < rows.length) {
      if (rows[k].kind !== "eq") { items.push(rows[k++]); continue; }
      let e = k;
      while (e < rows.length && rows[e].kind === "eq") e++;
      const keepTop = k === 0 ? 0 : CONTEXT, keepBottom = e === rows.length ? 0 : CONTEXT;
      const hidden = e - k - keepTop - keepBottom;
      const id = "g" + k;
      if (hidden > 1 && !expanded.has(id)) {
        for (let x = k; x < k + keepTop; x++) items.push(rows[x]);
        items.push({ gap: id, count: hidden });
        for (let x = e - keepBottom; x < e; x++) items.push(rows[x]);
      } else {
        for (let x = k; x < e; x++) items.push(rows[x]);
      }
      k = e;
    }
    return items;
  }

  // ---------- rendering ----------
  const diffEl = document.getElementById("diff");
  let hunkRows = []; // per change: the row elements to scroll to / flash

  function rowEl(cls, lns, ind, html, gridRow, h) {
    let s = `<div class="row ${cls}"${gridRow ? ` style="grid-row:${gridRow}"` : ""}${h >= 0 ? ` data-h="${h}"` : ""}>`;
    for (const n of lns) s += `<div class="ln">${n == null ? "" : n + 1}</div>`;
    return s + `<div class="ind">${ind}</div><div class="txt">${html}</div></div>`;
  }
  const gapEl = (it, gridRow) =>
    `<div class="collapsed" data-gap="${it.gap}"${gridRow ? ` style="grid-row:${gridRow}"` : ""}>&#8943; ${it.count} unchanged lines hidden. Click to show them.</div>`;

  function render() {
    const items = visibleItems();
    diffEl.className = `${settings.layout} ${settings.wrap ? "wrap" : "nowrap"}`;
    document.body.classList.toggle("inline", settings.layout === "inline");
    let html = "";
    if (settings.layout === "sbs") {
      let L = "", R = "";
      items.forEach((it, idx) => {
        const g = idx + 1;
        if (it.gap) { L += gapEl(it, g); R += gapEl(it, g); return; }
        const lc = { eq: "", mod: "mod-l", del: "del", ins: "fill" }[it.kind];
        const rc = { eq: "", mod: "mod-r", del: "fill", ins: "ins" }[it.kind];
        L += rowEl(lc, [it.o], it.kind === "del" || it.kind === "mod" ? "−" : "", it.o == null ? "" : sideHtml(it, "l"), g, it.h);
        R += rowEl(rc, [it.n], it.kind === "ins" || it.kind === "mod" ? "+" : "", it.n == null ? "" : sideHtml(it, "r"), g, it.h);
      });
      html = `<div class="pane left"><div class="pane-inner">${L}</div></div><div class="pane right"><div class="pane-inner">${R}</div></div>`;
    } else {
      // One column: all removed lines of a change, then all added lines.
      let out = "", k = 0;
      while (k < items.length) {
        const it = items[k];
        if (it.gap) { out += gapEl(it); k++; continue; }
        if (it.kind === "eq") { out += rowEl("", [it.o, it.n], "", sideHtml(it, "l")); k++; continue; }
        let e = k;
        while (e < items.length && !items[e].gap && items[e].h === it.h) e++;
        const group = items.slice(k, e);
        for (const r of group) if (r.o != null) out += rowEl("del", [r.o, null], "−", sideHtml(r, "l"), 0, it.h);
        for (const r of group) if (r.n != null) out += rowEl("ins", [null, r.n], "+", sideHtml(r, "r"), 0, it.h);
        k = e;
      }
      html = `<div class="pane"><div class="pane-inner">${out}</div></div>`;
    }
    diffEl.innerHTML = html;
    hunkRows = hunks.map(() => []);
    for (const el of diffEl.querySelectorAll(".row[data-h]")) hunkRows[+el.dataset.h].push(el);
    renderHeads();
    layoutRuler();
    updateCounter();
  }

  function renderHeads() {
    const L = DATA.left, R = DATA.right;
    const head = f => `<span class="name">${esc(f.label)}:</span> ${esc(f.name)}`;
    document.getElementById("heads").innerHTML = settings.layout === "sbs"
      ? `<div>${head(L)}</div><div>${head(R)}</div>`
      : `<div>${head(L)} &nbsp;→&nbsp; ${head(R)}</div>`;
    const l = L.label.toLowerCase(), r = R.label.toLowerCase();
    document.getElementById("help-layout").textContent = settings.layout === "sbs"
      ? `The ${l} is on the left and the ${r} is on the right.`
      : `Each change shows the wording from the ${l} (red) directly above the wording from the ${r} (green).`;
  }

  // ---------- navigation ----------
  const topEl = document.getElementById("top");
  const headsEl = document.getElementById("heads");
  const headerH = () => getComputedStyle(topEl).position === "sticky"
    ? topEl.getBoundingClientRect().height + headsEl.getBoundingClientRect().height : 0;
  const refLine = () => headerH() + (innerHeight - headerH()) / 3;
  const hunkTop = h => hunkRows[h][0].getBoundingClientRect().top;

  function currentHunk() {
    // The change at or just above the reading line (a third of the way down).
    const ref = refLine() + 4;
    let cur = -1;
    for (let h = 0; h < hunks.length; h++) if (hunkTop(h) <= ref) cur = h; else break;
    return cur;
  }
  function goTo(h) {
    if (h < 0 || h >= hunks.length) return;
    scrollTo({ top: scrollY + hunkTop(h) - refLine(), behavior: "smooth" });
    for (const el of hunkRows[h]) { el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash"); }
  }
  function step(dir) {
    const ref = refLine();
    if (dir > 0) { for (let h = 0; h < hunks.length; h++) if (hunkTop(h) > ref + 6) return goTo(h); }
    else { for (let h = hunks.length - 1; h >= 0; h--) if (hunkTop(h) < ref - 6) return goTo(h); }
  }
  function updateCounter() {
    const c = currentHunk();
    document.getElementById("counter").textContent =
      c < 0 ? `${hunks.length} changes` : `Change ${c + 1} of ${hunks.length}`;
  }

  // ---------- overview ruler ----------
  const ruler = document.getElementById("ruler");
  let viewBox;
  function layoutRuler() {
    headsEl.style.top = topEl.getBoundingClientRect().height + "px";
    const top = headerH();
    ruler.style.top = top + "px";
    const H = ruler.clientHeight, docH = document.documentElement.scrollHeight;
    const diffTop = diffEl.getBoundingClientRect().top + scrollY;
    const scale = H / Math.max(1, docH - diffTop);
    let html = "";
    hunks.forEach((hk, h) => {
      const els = hunkRows[h];
      const y0 = els[0].getBoundingClientRect().top + scrollY - diffTop;
      const y1 = els[els.length - 1].getBoundingClientRect().bottom + scrollY - diffTop;
      const st = `top:${(y0 * scale).toFixed(1)}px;height:${Math.max(3, (y1 - y0) * scale).toFixed(1)}px`;
      if (hk.dels) html += `<div class="mk d" style="${st}"></div>`;
      if (hk.inss) html += `<div class="mk i" style="${st}"></div>`;
    });
    ruler.innerHTML = html + `<div class="view"></div>`;
    viewBox = ruler.querySelector(".view");
    ruler._scale = scale; ruler._diffTop = diffTop;
    updateViewBox();
  }
  function updateViewBox() {
    if (!viewBox) return;
    const s = ruler._scale, visTop = scrollY + headerH() - ruler._diffTop;
    viewBox.style.top = Math.max(0, visTop * s) + "px";
    viewBox.style.height = Math.max(6, (innerHeight - headerH()) * s) + "px";
  }
  ruler.addEventListener("click", e => {
    const y = e.clientY - ruler.getBoundingClientRect().top;
    scrollTo({ top: ruler._diffTop + y / ruler._scale - (innerHeight - headerH()) / 2 - headerH(), behavior: "smooth" });
  });

  // ---------- settings & events ----------
  // Every visit starts from these defaults.
  const settings = { layout: "sbs", wrap: true, hide: true, theme: "light" };
  function applyChrome() {
    document.documentElement.dataset.theme = settings.theme;
    document.getElementById("lay-" + settings.layout).checked = true;
    document.getElementById("wrap").checked = settings.wrap;
    document.getElementById("hide").checked = settings.hide;
  }
  // Re-render while keeping the change nearest the reading line in place.
  function rerender() {
    const h = currentHunk();
    const before = h >= 0 ? hunkTop(h) : null;
    render();
    if (before != null) scrollTo({ top: scrollY + hunkTop(h) - before });
  }
  for (const el of document.querySelectorAll("input[name=layout]")) el.addEventListener("change", () => { settings.layout = el.value; rerender(); });
  document.getElementById("wrap").addEventListener("change", e => { settings.wrap = e.target.checked; rerender(); });
  document.getElementById("hide").addEventListener("change", e => { settings.hide = e.target.checked; expanded.clear(); rerender(); });
  document.getElementById("theme").addEventListener("click", () => { settings.theme = settings.theme === "dark" ? "light" : "dark"; applyChrome(); });
  document.getElementById("helpbtn").addEventListener("click", () => {
    const dlg = document.getElementById("helpdlg");
    dlg.firstElementChild.innerHTML = `<div class="help">${document.getElementById("help").innerHTML.replace(/ id="[^"]*"/g, "")}</div>`;
    dlg.showModal();
  });
  document.getElementById("prev").addEventListener("click", () => step(-1));
  document.getElementById("next").addEventListener("click", () => step(1));
  diffEl.addEventListener("click", e => {
    const g = e.target.closest(".collapsed");
    if (!g) return;
    expanded.add(g.dataset.gap); // revealed lines open downward from the bar
    render();
  });
  document.addEventListener("keydown", e => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === "n" || e.key === "j" || (e.key === "F7" && !e.shiftKey)) { e.preventDefault(); step(1); }
    else if (e.key === "p" || e.key === "k" || (e.key === "F7" && e.shiftKey)) { e.preventDefault(); step(-1); }
  });
  let raf = 0;
  addEventListener("scroll", () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; updateCounter(); updateViewBox(); }); }, { passive: true });
  let rt = 0;
  addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(layoutRuler, 100); });

  applyChrome();
  render();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(layoutRuler);
})();
</script>
</body>
</html>
'''

if __name__ == "__main__":
    main()
