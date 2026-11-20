#!/usr/bin/env python3
"""Convert a MineOps maintenance export into a self-contained, offline HTML report.

Requires Python 3.9+ and no third-party dependencies. Example:
    python dashboard.py --input demo/maintenance_report.csv --output dashboard.html
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
from html import escape
from pathlib import Path

COLUMNS = {
    "id", "name", "category", "last_serviced", "service_due",
    "days_remaining", "hours_remaining", "status",
}
STATUS_LABELS = {"OVERDUE": "Overdue", "DUE_SOON": "Due soon", "OK": "On track"}


def load_report(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = COLUMNS.difference(reader.fieldnames or [])
        if missing:
            raise ValueError("Missing report fields: " + ", ".join(sorted(missing)))
        rows = list(reader)
    for row in rows:
        if row["status"] not in STATUS_LABELS:
            raise ValueError(f"Unknown status: {row['status']}")
        for field in ("days_remaining", "hours_remaining"):
            int(row[field])
    return rows


def build_html(rows: list[dict[str, str]], as_of: str) -> str:
    # These are presentation statuses based on synthetic operating data, not safety certifications.
    counts = {key: sum(r["status"] == key for r in rows) for key in STATUS_LABELS}
    total = len(rows)
    percentages = {key: 100 * count / total if total else 0 for key, count in counts.items()}
    ordered = sorted(rows, key=lambda r: (
        {"OVERDUE": 0, "DUE_SOON": 1, "OK": 2}[r["status"]],
        int(r["days_remaining"]), r["id"]
    ))
    items = "\n".join(
        '<tr data-status="{status}">'
        '<td class="mono">{id}</td><td><strong>{name}</strong></td>'
        '<td>{category}</td><td class="mono">{due}</td>'
        '<td class="numeric">{days}</td><td class="numeric">{hours}</td>'
        '<td><span class="pill {cls}">{label}</span></td></tr>'.format(
            id=escape(r["id"]), name=escape(r["name"]), category=escape(r["category"]),
            due=escape(r["service_due"]), days=escape(r["days_remaining"]),
            hours=escape(r["hours_remaining"]), status=escape(r["status"]),
            cls=r["status"].lower(), label=STATUS_LABELS[r["status"]],
        ) for r in ordered
    )
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MineOps | Asset Maintenance Overview</title>
  <style>
    :root {{ color-scheme: light; --ink:#162236; --sub:#687589; --border:#e6eaf0; --bg:#f3f5f9; }}
    * {{ box-sizing:border-box; }}
    body {{ font:15px/1.5 system-ui,-apple-system,Segoe UI,Arial,sans-serif; color:var(--ink); margin:0; background:var(--bg); }}
    header {{ background:#142237; color:#fff; padding:28px max(24px,calc((100vw - 1150px)/2)); }}
    header .brand {{ letter-spacing:.14em; text-transform:uppercase; font-weight:750; font-size:12px; color:#9cc8ed; }}
    header h1 {{ font-size:28px; letter-spacing:-.8px; margin:8px 0 3px; }}
    header p {{ color:#bac6d6; margin:0; font-size:14px; }}
    main {{ max-width:1198px; margin:auto; padding:26px 24px 44px; }}
    .meta {{ display:flex; flex-wrap:wrap; gap:12px; align-items:center; margin-bottom:20px; color:var(--sub); font-size:13px; }}
    .dot {{ background:#d8dee7; width:4px; height:4px; border-radius:100%; }}
    .cards {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; }}
    .card, .panel {{ background:white; border:1px solid var(--border); border-radius:15px; box-shadow:0 3px 15px rgba(15,37,68,.035); }}
    .card {{ padding:20px 22px; }} .card-label {{ font-weight:700; font-size:13px; color:#66758b; }}
    .card-number {{ font-size:35px; font-weight:780; letter-spacing:-1.4px; margin:7px 0 0; }}
    .card-desc {{ font-size:12px; color:#8b95a5; margin-top:1px; }}
    .card.over .card-number {{ color:#b63442; }} .card.soon .card-number {{ color:#b97213; }} .card.good .card-number {{ color:#218265; }}
    .panel {{ margin-top:16px; padding:22px; }}
    h2 {{ margin:0 0 5px; font-size:17px; letter-spacing:-.3px; }}
    .sub {{ color:var(--sub); font-size:13px; margin:0; }}
    .rail {{ display:flex; overflow:hidden; width:100%; background:#e8edf2; border-radius:50px; height:18px; margin:20px 0 14px; }}
    .rail div {{ height:100%; }} .r1 {{ background:#c54a57; }} .r2 {{ background:#dda64c; }} .r3 {{ background:#349477; }}
    .legend {{ display:flex; flex-wrap:wrap; gap:18px; color:#5f6e80; font-size:13px; }}
    .key {{ display:inline-block; width:9px; height:9px; border-radius:3px; margin-right:6px; }}
    .filters {{ display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:10px; margin:19px 0 13px; }}
    input, select {{ border:1px solid #dbe1e8; padding:10px 12px; border-radius:9px; font:inherit; background:white; color:var(--ink); }}
    input {{ min-width:250px; }}
    table {{ border-collapse:collapse; width:100%; font-size:13px; }}
    th {{ padding:12px; text-align:left; background:#f6f8fb; color:#5d6b7f; text-transform:uppercase; letter-spacing:.05em; font-size:11px; }}
    td {{ border-top:1px solid #edf0f4; padding:14px 12px; }}
    .numeric {{ text-align:right; font-variant-numeric:tabular-nums; }}
    th.numeric {{ text-align:right; }}
    .mono {{ font-variant-numeric:tabular-nums; }}
    .pill {{ padding:5px 9px; border-radius:6px; font-weight:700; display:inline-block; font-size:12px; white-space:nowrap; }}
    .pill.overdue {{ background:#fde9eb; color:#a52e40; }}
    .pill.due_soon {{ background:#fff1d5; color:#8c5c10; }}
    .pill.ok {{ background:#e0f4eb; color:#176d52; }}
    .table-scroll {{ overflow-x:auto; }}
    .foot {{ padding-top:16px; color:#8a96a7; font-size:12px; }}
    @media(max-width:700px) {{ .cards {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} header h1 {{ font-size:22px; }} input {{ min-width:100%; }} .card {{ padding:15px; }} }}
  </style>
</head>
<body>
  <header><div class="brand">MineOps / Software Engineering Demo</div>
    <h1>Asset Maintenance Overview</h1>
    <p>Preventive maintenance tracking with C++ data processing and a Python-generated dashboard</p>
  </header>
  <main>
    <div class="meta"><span>Reference date: <b>{escape(as_of)}</b></span><span class="dot"></span><span>Sample dataset: synthetic</span><span class="dot"></span><span>Offline report</span></div>
    <section class="cards" aria-label="Key performance indicators">
      <div class="card"><div class="card-label">Total assets</div><div class="card-number">{total}</div><div class="card-desc">Monitored in this demo</div></div>
      <div class="card over"><div class="card-label">Overdue</div><div class="card-number">{counts['OVERDUE']}</div><div class="card-desc">Past time or usage threshold</div></div>
      <div class="card soon"><div class="card-label">Due soon</div><div class="card-number">{counts['DUE_SOON']}</div><div class="card-desc">Within 14 days or 50 hours</div></div>
      <div class="card good"><div class="card-label">On track</div><div class="card-number">{counts['OK']}</div><div class="card-desc">Outside warning thresholds</div></div>
    </section>
    <section class="panel"><h2>Maintenance workload</h2><p class="sub">Status distribution across the current equipment register</p>
      <div class="rail" aria-label="Status distribution">
        <div class="r1" style="width:{percentages['OVERDUE']:.1f}%" title="Overdue"></div>
        <div class="r2" style="width:{percentages['DUE_SOON']:.1f}%" title="Due soon"></div>
        <div class="r3" style="width:{percentages['OK']:.1f}%" title="On track"></div>
      </div>
      <div class="legend"><span><i class="key r1"></i>Overdue ({counts['OVERDUE']})</span><span><i class="key r2"></i>Due soon ({counts['DUE_SOON']})</span><span><i class="key r3"></i>On track ({counts['OK']})</span></div>
    </section>
    <section class="panel">
      <h2>Asset register</h2><p class="sub">Search equipment names, categories, and IDs, or filter by priority</p>
      <div class="filters">
        <input id="search" type="search" placeholder="Search assets..." aria-label="Search assets" />
        <select id="filter" aria-label="Filter by status"><option value="ALL">All statuses</option><option value="OVERDUE">Overdue</option><option value="DUE_SOON">Due soon</option><option value="OK">On track</option></select>
      </div>
      <div class="table-scroll"><table>
        <thead><tr><th>ID</th><th>Equipment</th><th>Category</th><th>Next service date</th><th class="numeric">Days left</th><th class="numeric">Hours left</th><th>Status</th></tr></thead>
        <tbody id="rows">{items}</tbody>
      </table></div>
      <p class="foot" id="display-count">Showing {total} assets</p>
    </section>
    <p class="foot">Portfolio prototype only. All sample data is fictional. Not for real equipment maintenance or safety-critical decision-making.</p>
  </main>
  <script>
    const search=document.getElementById('search');
    const filter=document.getElementById('filter');
    const rows=[...document.querySelectorAll('#rows tr')];
    function applyFilters() {{
      const query=search.value.trim().toLowerCase();
      let shown=0;
      for (const row of rows) {{
        const visible=(filter.value==='ALL'||row.dataset.status===filter.value) && row.textContent.toLowerCase().includes(query);
        row.hidden=!visible; if(visible) shown++;
      }}
      document.getElementById('display-count').textContent=`Showing ${{shown}} of ${{rows.length}} assets`;
    }}
    search.addEventListener('input',applyFilters);
    filter.addEventListener('change',applyFilters);
  </script>
</body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("demo/maintenance_report.csv"))
    parser.add_argument("--output", type=Path, default=Path("demo/dashboard.html"))
    parser.add_argument("--as-of", default="2026-11-19")
    args = parser.parse_args()
    date.fromisoformat(args.as_of)
    rows = load_report(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_html(rows, args.as_of), encoding="utf-8")
    print(f"Dashboard created: {args.output} ({len(rows)} assets)")


if __name__ == "__main__":
    main()
