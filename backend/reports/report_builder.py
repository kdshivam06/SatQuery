"""Report builder – generates JSON + optional HTML report per run."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def build_report(run_result: dict, run_dir: str | Path) -> dict[str, str]:
    """Generate a downloadable report from the final run result.

    Returns dict with paths: {"json": ..., "html": ...}
    """
    out_dir = Path(run_dir) / "report"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── JSON report ───────────────────────────────────────
    json_path = out_dir / "report.json"
    report_data = {
        "generated_at": datetime.now(UTC).isoformat(),
        "run_id": run_result.get("run_id", ""),
        "query": run_result.get("query", ""),
        "workflow": run_result.get("workflow", ""),
        "answer": run_result.get("answer", ""),
        "confidence": run_result.get("confidence"),
        "evidence": run_result.get("evidence", []),
        "visual_outputs": run_result.get("visual_outputs", []),
        "tool_results": run_result.get("tool_results", {}),
        "trace": run_result.get("trace", {}),
    }
    json_path.write_text(json.dumps(report_data, indent=2, default=str), encoding="utf-8")

    # ── HTML report ───────────────────────────────────────
    html_path = out_dir / "report.html"
    html_path.write_text(_build_html(report_data), encoding="utf-8")

    return {"json": str(json_path), "html": str(html_path)}


def _build_html(data: dict) -> str:
    """Generate a standalone HTML report."""
    evidence_items = "".join(f"<li>{_esc(e)}</li>" for e in data.get("evidence", []))
    visual_items = "".join(
        f'<div class="visual"><img src="../{v.get("url","")}" alt="{_esc(v.get("label",""))}" '
        f'onerror="this.style.display=\'none\'"><p>{_esc(v.get("label",""))}</p></div>'
        for v in data.get("visual_outputs", [])
    )

    tool_rows = ""
    for name, result in data.get("tool_results", {}).items():
        status = result.get("status", "?")
        badge = {"success": "✅", "skipped": "⏭️", "failed": "❌"}.get(status, "❓")
        conf = result.get("confidence")
        conf_str = f"{conf:.0%}" if conf is not None else "–"
        runtime = result.get("runtime_ms", 0)
        summary = result.get("summary", "")
        tool_rows += f"<tr><td>{badge} {_esc(name)}</td><td>{_esc(status)}</td><td>{conf_str}</td><td>{runtime}ms</td><td>{_esc(summary[:120])}</td></tr>"

    trace = data.get("trace", {})
    groups = trace.get("parallel_groups", [])
    groups_html = ""
    for i, group in enumerate(groups):
        groups_html += f'<span class="group">Group {i+1}: {", ".join(group)}</span> '

    confidence = data.get("confidence", 0)
    conf_pct = f"{confidence:.0%}" if confidence else "–"
    conf_color = "#4ade80" if confidence and confidence > 0.7 else "#fbbf24" if confidence and confidence > 0.5 else "#f87171"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SatQuery Report – {_esc(data.get("run_id",""))}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter','Segoe UI',sans-serif;background:#0a0e1a;color:#e2e8f0;padding:2rem;max-width:1100px;margin:0 auto}}
h1{{font-size:1.8rem;margin-bottom:.5rem;color:#fff}}
h2{{font-size:1.2rem;margin:1.5rem 0 .5rem;color:#94a3b8;border-bottom:1px solid #1e293b;padding-bottom:.3rem}}
.meta{{color:#64748b;font-size:.85rem;margin-bottom:1rem}}
.answer-box{{background:#1e293b;border-left:4px solid #3b82f6;padding:1rem;border-radius:8px;margin:1rem 0;line-height:1.6}}
.confidence{{display:inline-flex;align-items:center;gap:.5rem;background:#1e293b;padding:.4rem 1rem;border-radius:20px;font-weight:600;color:{conf_color}}}
.confidence .bar{{width:80px;height:8px;background:#334155;border-radius:4px;overflow:hidden}}
.confidence .fill{{height:100%;background:{conf_color};width:{confidence*100 if confidence else 0}%}}
ul{{padding-left:1.2rem;line-height:1.8}}
li{{font-size:.9rem}}
table{{width:100%;border-collapse:collapse;margin:.5rem 0;font-size:.85rem}}
th,td{{padding:.5rem .6rem;text-align:left;border-bottom:1px solid #1e293b}}
th{{color:#94a3b8;font-weight:600}}
tr:hover{{background:#1e293b33}}
.visuals{{display:flex;flex-wrap:wrap;gap:1rem;margin:.5rem 0}}
.visual{{background:#1e293b;border-radius:8px;padding:.5rem;max-width:280px}}
.visual img{{width:100%;border-radius:6px}}
.visual p{{font-size:.8rem;color:#94a3b8;margin-top:.3rem;text-align:center}}
.group{{background:#1e293b;padding:.2rem .6rem;border-radius:12px;font-size:.8rem;display:inline-block;margin:.2rem}}
</style>
</head>
<body>
<h1>🛰️ SatQuery AI Report</h1>
<p class="meta">Run: {_esc(data.get("run_id",""))} • Workflow: {_esc(data.get("workflow",""))} • {_esc(data.get("generated_at",""))}</p>

<h2>Query</h2>
<p style="font-style:italic;color:#cbd5e1">"{_esc(data.get("query",""))}"</p>

<h2>Answer</h2>
<div class="answer-box">{_esc(data.get("answer",""))}</div>
<div class="confidence"><span>Confidence: {conf_pct}</span><div class="bar"><div class="fill"></div></div></div>

<h2>Evidence</h2>
<ul>{evidence_items if evidence_items else "<li>No evidence collected.</li>"}</ul>

<h2>Visual Outputs</h2>
<div class="visuals">{visual_items if visual_items else "<p style='color:#64748b'>No visual outputs.</p>"}</div>

<h2>Tool Execution</h2>
<div style="margin-bottom:.5rem">{groups_html if groups_html else "<span class='group'>No parallel groups</span>"}</div>
<table>
<tr><th>Tool</th><th>Status</th><th>Confidence</th><th>Runtime</th><th>Summary</th></tr>
{tool_rows if tool_rows else "<tr><td colspan='5' style='color:#64748b'>No tools executed.</td></tr>"}
</table>

<p style="margin-top:2rem;color:#475569;font-size:.75rem">Generated by SatQuery AI • ISRO/SAC Smart India Hackathon</p>
</body>
</html>"""


def _esc(text: str) -> str:
    """Escape HTML special characters."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
