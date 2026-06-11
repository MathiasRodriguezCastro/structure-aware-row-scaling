"""Estilos HTML compartidos para reportes técnicos del proyecto."""

from __future__ import annotations

import html
from datetime import datetime


ACADEMIC_CSS = """
:root {
  --bg:          #f4f6fa;
  --paper:       #ffffff;
  --paper-soft:  #f8fafc;
  --ink:         #0f172a;
  --muted:       #64748b;
  --line:        #d4dae6;
  --line-soft:   #e6ecf4;
  --accent:      #1d4f91;
  --accent-soft: #e8f1fb;
  --ok:          #166534;
  --ok-soft:     #dcfce7;
  --ok-mid:      #bbf7d0;
  --warn:        #92400e;
  --warn-soft:   #fef3c7;
  --bad:         #991b1b;
  --bad-soft:    #fee2e2;
  --mono:        #0f172a;
}

/* ── Reset ── */
* { box-sizing: border-box; }
html { background: var(--bg); }
body {
  margin: 0;
  color: var(--ink);
  background: var(--bg);
  font-family: "Inter", "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 14px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

/* ── Layout ── */
main {
  max-width: 1440px;
  margin: 0 auto;
  padding: 28px 32px 56px;
}

/* ── Header ── */
.report-header {
  background: #ffffff;
  border-bottom: 1px solid var(--line);
  box-shadow: 0 1px 3px rgba(15,23,42,.06);
}
.report-header-inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 32px 32px 26px;
}
.eyebrow {
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .1em;
  text-transform: uppercase;
  margin-bottom: 8px;
}
h1 {
  margin: 0 0 8px;
  color: var(--ink);
  font-size: 26px;
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: -.01em;
}
.subtitle {
  max-width: 820px;
  margin: 0;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.5;
}

/* ── Meta-grid ── */
.meta-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(150px, 1fr));
  gap: 10px;
  margin-top: 22px;
}
.meta-item {
  border: 1px solid var(--line-soft);
  background: var(--paper-soft);
  border-radius: 8px;
  padding: 10px 14px;
}
.meta-item span {
  display: block;
  color: var(--muted);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .07em;
}
.meta-item strong {
  display: block;
  margin-top: 3px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
  overflow-wrap: anywhere;
}

/* ── Cards ── */
.card {
  margin: 16px 0;
  border: 1px solid var(--line);
  background: var(--paper);
  border-radius: 10px;
  padding: 20px 20px 16px;
  box-shadow: 0 1px 3px rgba(15,23,42,.05);
}
.summary {
  border-color: #c3d5ec;
  background: linear-gradient(160deg, #fbfdff 0%, #f4f8fe 100%);
}

/* ── Headings ── */
h2 {
  margin: 0 0 10px;
  color: var(--ink);
  font-size: 16px;
  font-weight: 600;
  line-height: 1.3;
}
h3 {
  margin: 14px 0 6px;
  color: #374151;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .05em;
}
p {
  margin: 0 0 12px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}

/* ── Notes ── */
.note {
  border: 1px solid #f0c070;
  background: var(--warn-soft);
  color: #78340f;
  border-radius: 8px;
  padding: 12px 16px;
  margin: 14px 0;
  font-size: 13px;
  line-height: 1.5;
}
.info-note {
  border: 1px solid #c3d8ef;
  background: #f0f6fd;
  color: #1e3a5f;
  border-radius: 8px;
  padding: 12px 16px;
  margin: 14px 0;
  font-size: 13px;
  line-height: 1.5;
}
.note code, .info-note code { background: rgba(255,255,255,.6); }

/* ── Metric grid ── */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(150px, 1fr));
  gap: 12px;
  margin: 16px 0;
}
.metric {
  border: 1px solid var(--line-soft);
  background: var(--paper-soft);
  border-radius: 8px;
  padding: 14px 16px;
}
.metric span {
  display: block;
  color: var(--muted);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .07em;
  line-height: 1.3;
}
.metric strong {
  display: block;
  margin-top: 6px;
  color: var(--ink);
  font-size: 21px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -.01em;
}

/* ── Tables ── */
.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
  /* webkit scrollbar */
}
.table-wrap::-webkit-scrollbar { height: 6px; }
.table-wrap::-webkit-scrollbar-track { background: var(--paper-soft); }
.table-wrap::-webkit-scrollbar-thumb { background: var(--line); border-radius: 3px; }

table {
  width: 100%;
  min-width: 900px;
  border-collapse: collapse;
  background: var(--paper);
}
th, td {
  padding: 9px 13px;
  border-bottom: 1px solid var(--line-soft);
  text-align: right;
  font-variant-numeric: tabular-nums;
  vertical-align: middle;
  font-size: 13px;
}
th:first-child, td:first-child,
th:nth-child(2), td:nth-child(2),
th:nth-child(3), td:nth-child(3) { text-align: left; }
th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #edf2f9;
  color: #475569;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .05em;
  white-space: nowrap;
}
tbody tr:nth-child(even) td { background: #fafbfd; }
tbody tr:hover td { background: #eef3fc !important; transition: background .1s; }
tr.ok td   { background: #f0fdf4; }
tr.bad td  { background: #fef2f2; }

/* Small variant table (comparar_preprocesamiento) */
.variant-table { min-width: 540px; }

/* Best-column highlight */
th.best-col { background: #d1fae5; color: #065f46; }
td.best-col { background: #f0fdf6; color: #065f46; font-weight: 600; }
tr.best-row td { background: #f6fef9; }

/* ── Status badges ── */
.badge {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .05em;
  white-space: nowrap;
}
.badge-ok   { background: var(--ok-mid);   color: var(--ok); }
.badge-warn { background: var(--warn-soft); color: var(--warn); }
.badge-bad  { background: var(--bad-soft);  color: var(--bad); }

/* ── Inline tags / pills ── */
.tag {
  display: inline-block;
  margin-left: 5px;
  padding: 1px 7px;
  background: var(--accent-soft);
  color: var(--accent);
  border-radius: 20px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .04em;
}
.best-pill {
  display: inline-block;
  margin-left: 5px;
  padding: 1px 7px;
  background: var(--ok-mid);
  color: var(--ok);
  border-radius: 20px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .04em;
}

/* ── Value classes ── */
.nd       { color: var(--muted); font-style: italic; }
.positive { color: var(--ok);   font-weight: 600; }
.negative { color: var(--bad);  font-weight: 600; }

/* ── Variant note (comparar_preprocesamiento) ── */
.variant-note {
  font-size: 13px;
  color: #374151;
  background: #f8fafc;
  border-left: 3px solid var(--accent-soft);
  border-radius: 0 6px 6px 0;
  padding: 8px 12px;
  margin: 10px 0;
  line-height: 1.5;
}

/* ── Code / Pre ── */
code, pre {
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
}
code {
  color: #1d4f91;
  background: #edf4fc;
  border: 1px solid #d6e4f5;
  border-radius: 5px;
  padding: 1px 5px;
  font-size: 12px;
}
pre {
  margin: 0;
  padding: 14px 16px;
  overflow: auto;
  color: #dbeafe;
  background: var(--mono);
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.5;
}

/* ── Status text ── */
.status-ok, .status-base { color: var(--ok);  font-weight: 700; }
.status-bad               { color: var(--bad); font-weight: 700; }

/* ── Responsive ── */
@media (max-width: 900px) {
  main, .report-header-inner { padding-left: 16px; padding-right: 16px; }
  .meta-grid, .metric-grid   { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 480px) {
  .meta-grid, .metric-grid { grid-template-columns: 1fr; }
}

/* ── Print ── */
@media print {
  body, html    { background: #fff; }
  .report-header { box-shadow: none; border-bottom-color: #ccc; }
  .card         { box-shadow: none; break-inside: avoid; border-color: #ccc; }
  th            { position: static; background: #f0f0f0 !important; color: #000 !important; }
  .table-wrap   { border: none; overflow: visible; }
}
"""


def render_meta(items: list[tuple[str, object]]) -> str:
    if not items:
        return ""
    cells = []
    for label, value in items:
        cells.append(
            "<div class=\"meta-item\">"
            f"<span>{html.escape(str(label))}</span>"
            f"<strong>{html.escape(str(value))}</strong>"
            "</div>"
        )
    return f"<div class=\"meta-grid\">{''.join(cells)}</div>"


def report_document(title: str, subtitle: str, body: str,
                    meta: list[tuple[str, object]] | None = None,
                    eyebrow: str = "Sistema Eléctrico") -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    meta_items = [("Generado", generated)]
    if meta:
        meta_items.extend(meta)
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html.escape(title)}</title>
<style>{ACADEMIC_CSS}</style>
</head>
<body>
<header class="report-header">
  <div class="report-header-inner">
    <div class="eyebrow">{html.escape(eyebrow)}</div>
    <h1>{html.escape(title)}</h1>
    <p class="subtitle">{html.escape(subtitle)}</p>
    {render_meta(meta_items)}
  </div>
</header>
<main>
{body}
</main>
</body>
</html>
"""
