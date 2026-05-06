#!/usr/bin/env python3
import json
import re
from pathlib import Path

STRATEGY_ORDER = ["N", "A", "B", "C", "D", "E", "F", "G", "H"]
STRATEGY_COLORS = {
    "A": "#355c7d",
    "B": "#c06c84",
    "C": "#1f7a4d",
    "D": "#9e3a1f",
    "E": "#6b4c9a",
    "F": "#00798c",
    "G": "#8f5e15",
    "H": "#3f7f4c",
    "N": "#777777",
}


def _strategy_letter(strategy_text):
    m = re.search(r"Strategy\s+([A-Z])", strategy_text or "")
    return m.group(1) if m else None


def parse_log(log_text):
    data = {
        "inputs": {},
        "demand": {},
        "winner": {},
        "reasoning": "",
        "pareto": [],
    }

    m = re.search(r"Span=([0-9.]+)\s*ft,\s*Spacing=([0-9.]+)\s*in,\s*Wind=([0-9.]+)\s*mph", log_text)
    if m:
        data["inputs"] = {
            "span_ft": float(m.group(1)),
            "spacing_in": float(m.group(2)),
            "wind_mph": float(m.group(3)),
        }

    m = re.search(r"Uplift Demand:\s*([0-9.]+)\s*lbf\s*\(([0-9.]+)\s*N\)", log_text)
    if m:
        data["demand"] = {"lbf": float(m.group(1)), "n": float(m.group(2))}

    pareto_pattern = re.compile(
        r"^\d+\.\s*(Strategy [A-HN].*?)\s*\|\s*safety=([0-9.]+),\s*impact=([0-9.]+),\s*disp=([0-9.]+)\s*in$",
        re.MULTILINE,
    )
    for match in pareto_pattern.finditer(log_text):
        data["pareto"].append(
            {
                "strategy": match.group(1),
                "safety": float(match.group(2)),
                "impact": float(match.group(3)),
                "disp_in": float(match.group(4)),
            }
        )

    m = re.search(r"Selected\s+(Strategy [A-HN].*?)\.", log_text)
    if m:
        data["winner"]["strategy"] = m.group(1)
    m = re.search(r"Predicted displacement\s*=\s*([0-9.]+)\s*in\s*\(limit\s*=\s*([0-9.]+)\s*in\)", log_text)
    if m:
        data["winner"]["pred_disp_in"] = float(m.group(1))
        data["winner"]["limit_in"] = float(m.group(2))
    m = re.search(r"capacity margin\s*=\s*([0-9.\-]+)\s*lbf", log_text)
    if m:
        data["winner"]["capacity_margin_lbf"] = float(m.group(1))
    m = re.search(r"Historic impact score\s*=\s*([0-9.]+)", log_text)
    if m:
        data["winner"]["impact_score"] = float(m.group(1))
    m = re.search(r"Reasoning:\s*(.+)", log_text)
    if m:
        winner_strategy_name = data["winner"].get("strategy", "Unknown Strategy")
        
        # Extract the short letter name if possible to make it cleaner, eg: Strategy D (Hurricane...)
        short_name_match = re.search(r"(Strategy\s+[A-H])", winner_strategy_name)
        short_name = short_name_match.group(1) if short_name_match else winner_strategy_name
        
        data["reasoning"] = f"**{short_name}**: " + m.group(1).strip()

    return data


def _svg_pareto(data, width=500, height=280, pad=36):
    pts = data.get("pareto", [])
    all_pass = data.get("all_pass", [])
    if not pts and not all_pass:
        return f'<svg viewBox="0 0 {width} {height}"></svg>'
    cloud = all_pass if all_pass else pts

    # Clip extreme high-impact tail for readability using IQR (display only).
    if len(cloud) >= 8:
        impacts = sorted(p["impact"] for p in cloud)
        q1_idx = int(0.25 * (len(impacts) - 1))
        q3_idx = int(0.75 * (len(impacts) - 1))
        q1 = impacts[q1_idx]
        q3 = impacts[q3_idx]
        iqr = max(1e-9, q3 - q1)
        impact_cap = q3 + 1.5 * iqr
        cloud = [p for p in cloud if p["impact"] <= impact_cap]
        pts = [p for p in pts if p["impact"] <= impact_cap]
        if not pts:
            pts = cloud[:]
    xs = [p["impact"] for p in cloud]
    ys = [p["safety"] for p in cloud]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    def x(v):
        return pad + (v - xmin) * (width - 2 * pad) / max((xmax - xmin), 1e-6)

    def y(v):
        return height - pad - (v - ymin) * (height - 2 * pad) / max((ymax - ymin), 1e-6)

    ordered = sorted(pts, key=lambda p: p["impact"])
    path = " ".join([f"{'M' if i == 0 else 'L'} {x(p['impact']):.2f} {y(p['safety']):.2f}" for i, p in enumerate(ordered)])
    cloud_circles = []
    for p in all_pass:
        letter = _strategy_letter(p.get("strategy", ""))
        color = STRATEGY_COLORS.get(letter or "N", "#777777")
        cloud_circles.append(
            f'<circle cx="{x(p["impact"]):.2f}" cy="{y(p["safety"]):.2f}" r="3.0" fill="{color}" fill-opacity="0.28" stroke="none"/>'
        )
    circles = []
    winner_strategy = data.get("winner", {}).get("strategy", "")
    for p in pts:
        letter = _strategy_letter(p.get("strategy", ""))
        color = STRATEGY_COLORS.get(letter or "N", "#777777")
        is_winner = (p.get("strategy") == winner_strategy)
        circles.append(
            f'<circle cx="{x(p["impact"]):.2f}" cy="{y(p["safety"]):.2f}" r="4.8" fill="{color}" '
            f'stroke="{"#24211f" if is_winner else "#ffffff"}" stroke-width="{"1.5" if is_winner else "1.0"}"/>'
        )
    return f"""
<svg viewBox="0 0 {width} {height}">
  <rect x="0" y="0" width="{width}" height="{height}" fill="#fff" stroke="#d9d0c6"/>
  <path d="M {pad} {pad} L {pad} {height-pad} L {width-pad} {height-pad}" stroke="#cfc7be" fill="none"/>
  <text x="6" y="14" font-size="12" fill="#6a625b">Safety</text>
  <text x="{width-54}" y="{height-10}" font-size="12" fill="#6a625b">Impact</text>
  {''.join(cloud_circles)}
  <path d="{path}" stroke="#9e3a1f" stroke-width="2" fill="none"/>
  {''.join(circles)}
</svg>
"""


def _strategy_legend_html():
    items = []
    for s in [x for x in STRATEGY_ORDER if x != "N"]:
        color = STRATEGY_COLORS.get(s, "#777777")
        items.append(
            f'<span style="display:inline-flex; align-items:center; gap:6px; margin-right:10px;">'
            f'<span style="width:10px; height:10px; border-radius:50%; background:{color}; border:1px solid #24211f;"></span>'
            f'<span>Strategy {s}</span>'
            f"</span>"
        )
    return "".join(items)


def _full_population_summary(full_pop):
    if not full_pop:
        return None
    bins = {s: [] for s in STRATEGY_ORDER if s != "N"}
    for item in full_pop.get("candidates", []):
        strategy = item.get("candidate", {}).get("strategy", "")
        if strategy in bins:
            bins[strategy].append(item)
    def summarize(label, items):
        if not items:
            return f"<tr><td>{label}</td><td>0</td><td colspan='4' style='color:var(--muted)'>No candidates logged</td></tr>"
        safety = sum(i["fitness"]["safety_score"] for i in items) / len(items)
        impact = sum(i["fitness"]["impact_score"] for i in items if i["fitness"]["impact_score"] < 1e20) / max(1, sum(1 for i in items if i["fitness"]["impact_score"] < 1e20))
        disp = sum(i["fitness"]["displacement_in"] for i in items) / len(items)
        pass_rate = sum(1 for i in items if i["fitness"]["pass_fail"] >= 1.0) / len(items)
        return f"<tr><td>{label}</td><td>{len(items)}</td><td>{safety:.3f}</td><td>{impact:.3f}</td><td>{disp:.3f}</td><td>{pass_rate:.2%}</td></tr>"
    return "\n".join(
        [summarize(f"Strategy {s}", bins[s]) for s in bins]
    )


def _pareto_from_full_population(full_pop):
    if not full_pop:
        return [], []
    points = []
    for item in full_pop.get("candidates", []):
        fit = item.get("fitness", {})
        cand = item.get("candidate", {})
        if fit.get("pass_fail", 0.0) < 1.0:
            continue
        impact = fit.get("impact_score")
        safety = fit.get("safety_score")
        if not isinstance(impact, (int, float)) or not isinstance(safety, (int, float)):
            continue
        points.append(
            {
                "strategy": f"Strategy {cand.get('strategy', '?')}",
                "impact": impact,
                "safety": safety,
                "disp_in": fit.get("displacement_in", 0.0),
            }
        )

    frontier = []
    for i, pi in enumerate(points):
        dominated = False
        for j, pj in enumerate(points):
            if i == j:
                continue
            better_or_equal = (pj["safety"] >= pi["safety"]) and (pj["impact"] <= pi["impact"])
            strictly_better = (pj["safety"] > pi["safety"]) or (pj["impact"] < pi["impact"])
            if better_or_equal and strictly_better:
                dominated = True
                break
        if not dominated:
            frontier.append(pi)
    frontier.sort(key=lambda p: p["impact"])
    
    # --- NOVO: Cálculo TOPSIS Matemático (Rankeamento por Distância Euclidiana a Utopia) ---
    if frontier:
        max_safety = max(p["safety"] for p in frontier)
        min_safety = min(p["safety"] for p in frontier)
        max_impact = max(p["impact"] for p in frontier)
        min_impact = min(p["impact"] for p in frontier)
        
        best_topsis_dist = float('inf')
        topsis_winner = None
        
        for p in frontier:
            # Normalize impact and safety
            norm_impact = (p["impact"] - min_impact) / (max_impact - min_impact) if max_impact > min_impact else 0.0
            norm_safety = (max_safety - p["safety"]) / (max_safety - min_safety) if max_safety > min_safety else 0.0
            
            dist_to_utopia = (norm_impact**2 + norm_safety**2)**0.5
            p["topsis_score"] = dist_to_utopia
            
            if dist_to_utopia < best_topsis_dist:
                best_topsis_dist = dist_to_utopia
                topsis_winner = p
                
        if topsis_winner:
            topsis_winner["is_topsis_winner"] = True
            
    return points, frontier


def _normalize_sensitivity_rows(a_sweep=None, bc_sweep=None, baseline_sweep=None, de_sweep=None):
    rows = []
    if a_sweep:
        for r in a_sweep.get("results", []):
            job = r.get("job", "")
            if not job.startswith("retrofit_a_"):
                continue
            rows.append(
                {
                    "strategy": "A",
                    "case": job.replace("retrofit_a_", "", 1),
                    "status": r.get("status", "unknown"),
                    "max_u2": r.get("max_u2"),
                    "max_smax": r.get("max_smax"),
                }
            )
    if bc_sweep:
        for r in bc_sweep.get("results", []):
            job = r.get("job", "")
            # sens_b_case_h5
            parts = job.split("_")
            if len(parts) < 4 or parts[0] != "sens":
                continue
            strategy = parts[1].upper()
            case = "_".join(parts[2:-1])
            rows.append(
                {
                    "strategy": strategy,
                    "case": case,
                    "status": r.get("status", "unknown"),
                    "max_u2": r.get("max_u2"),
                    "max_smax": r.get("max_smax"),
                }
            )
    if baseline_sweep:
        for r in baseline_sweep.get("results", []):
            rows.append(
                {
                    "strategy": "N",
                    "case": r.get("job", "no_retrofit"),
                    "status": "ok",
                    "max_u2": r.get("max_u2"),
                    "max_smax": r.get("max_smax"),
                }
            )
    if de_sweep:
        for r in de_sweep.get("results", []):
            job = r.get("job", "")
            strat = "D" if "_d_" in job or job.startswith("retrofit_d") else "E"
            rows.append(
                {
                    "strategy": strat,
                    "case": "trial_h5",
                    "status": "ok",
                    "max_u2": r.get("max_u2"),
                    "max_smax": r.get("max_smax"),
                }
            )
    return rows


def _svg_tornado(strategy_rows, title, width=330, height=220):
    ok = [r for r in strategy_rows if r.get("status") == "ok" and isinstance(r.get("max_u2"), (int, float))]
    if not ok:
        return f'<svg viewBox="0 0 {width} {height}"><text x="14" y="24" font-size="12" fill="#6a625b">{title}: no valid runs</text></svg>'
    base = next((r for r in ok if r["case"] == "base"), None)
    if base is None:
        base = min(ok, key=lambda r: r["max_u2"])
    b = base["max_u2"]
    bars = []
    left = 130
    row_h = 20
    top = 28
    span = max(abs(r["max_u2"] - b) for r in ok) or 1e-9
    scale = (width - left - 20) / span
    for i, r in enumerate(sorted(ok, key=lambda x: abs(x["max_u2"] - b), reverse=True)[:8]):
        y = top + i * row_h
        delta = r["max_u2"] - b
        w = abs(delta) * scale
        color = "#9e3a1f" if delta > 0 else "#1f7a4d"
        bars.append(f'<text x="8" y="{y+11}" font-size="11" fill="#24211f">{r["case"]}</text>')
        bars.append(f'<rect x="{left}" y="{y}" width="{w:.2f}" height="12" fill="{color}"/>')
        bars.append(f'<text x="{left + w + 4:.2f}" y="{y+11}" font-size="10" fill="#6a625b">{r["max_u2"]:.4f} m</text>')
    return (
        f'<svg viewBox="0 0 {width} {height}">'
        f'<text x="8" y="14" font-size="12" fill="#6a625b">Baseline: {b:.4f} m (case={base["case"]})</text>'
        f'{"".join(bars)}'
        f"</svg>"
    )


def _sensitivity_table_rows(rows):
    if not rows:
        return "<tr><td colspan='6' style='color:var(--muted)'>No sensitivity results found.</td></tr>"
    out = []
    for i, r in enumerate(sorted(rows, key=lambda x: (x["strategy"], x["case"]))):
        status = "PASS" if r["status"] == "ok" and (r.get("max_u2") is not None and r["max_u2"] <= 0.0127) else ("N/A" if r["status"] != "ok" else "FAIL")
        max_u2_text = "" if r.get("max_u2") is None else "{:.6f}".format(r["max_u2"])
        max_smax_text = "" if r.get("max_smax") is None else "{:.2f}".format(r["max_smax"])
        out.append(
            "<tr>"
            f"<td>{i+1}</td>"
            f"<td>{r['strategy']}</td>"
            f"<td>{r['case']}</td>"
            f"<td>{r['status']}</td>"
            f"<td>{max_u2_text}</td>"
            f"<td>{max_smax_text}</td>"
            f"<td>{status}</td>"
            "</tr>"
        )
    return "".join(out)


def _robustness_rows(rows):
    if not rows:
        return "<tr><td colspan='5' style='color:var(--muted)'>No robustness data.</td></tr>"
    out = []
    ordered = STRATEGY_ORDER[:]
    for strat in ordered:
        s_rows = [r for r in rows if r["strategy"] == strat and r["status"] == "ok" and isinstance(r.get("max_u2"), (int, float))]
        if not s_rows:
            out.append(
                f"<tr><td>{strat}</td><td>0</td>"
                f"<td colspan='3' style='color:var(--muted)'>No sensitivity runs available</td></tr>"
            )
            continue
        mean_u2 = sum(r["max_u2"] for r in s_rows) / len(s_rows)
        worst_u2 = max(r["max_u2"] for r in s_rows)
        pass_rate = sum(1 for r in s_rows if r["max_u2"] <= 0.0127) / len(s_rows)
        out.append(
            f"<tr><td>{strat}</td><td>{len(s_rows)}</td><td>{mean_u2:.6f}</td><td>{worst_u2:.6f}</td><td>{pass_rate:.1%}</td></tr>"
        )
    return "".join(out)


def _fe_image_rows(manifest):
    if not manifest:
        return (
            "<tr><td colspan='5' style='color:var(--muted)'>No FE image manifest found. "
            "Run image export first.</td></tr>"
        )
    image_dir = manifest.get("image_dir", "fe_images")
    rows = manifest.get("strategies", [])
    if not rows:
        return "<tr><td colspan='5' style='color:var(--muted)'>No FE image records.</td></tr>"
    out = []
    for row in rows:
        strategy = row.get("strategy", "?")
        job = row.get("job", "")
        status = row.get("status", "unknown")
        if status != "ok":
            out.append(
                f"<tr><td>Strategy {strategy}</td><td>{job}</td>"
                f"<td colspan='3' style='color:var(--muted)'>No images ({status})</td></tr>"
            )
            continue

        def img_cell(name, label):
            src = f"{image_dir}/{name}"
            return (
                "<td>"
                f"<div style='font-size:12px; color:var(--muted); margin-bottom:4px'>{label}</div>"
                f"<img src='{src}' alt='Strategy {strategy} {label}' "
                "style='width:100%; max-width:260px; border:1px solid var(--line); border-radius:8px;'/>"
                "</td>"
            )

        out.append(
            "<tr>"
            f"<td>Strategy {strategy}</td>"
            f"<td>{job}</td>"
            f"{img_cell(row.get('before', ''), 'Before Load')}"
            f"{img_cell(row.get('u2', ''), 'After Load: Displacement')}"
            f"{img_cell(row.get('smax', ''), 'After Load: Stress')}"
            "</tr>"
        )
    return "".join(out)


def _verification_rows(report):
    if not report:
        return "<tr><td colspan='3' style='color:var(--muted)'>No verification report found. Run verification_suite.py first.</td></tr>"
    rows = report.get("tests", [])
    if not rows:
        return "<tr><td colspan='3' style='color:var(--muted)'>Verification report has no tests.</td></tr>"
    out = []
    for t in rows:
        status = "PASS" if t.get("passed") else "FAIL"
        color = "var(--safe)" if t.get("passed") else "var(--warn)"
        out.append(
            "<tr>"
            f"<td style='font-weight:600; color:{color}'>{status}</td>"
            f"<td>{t.get('name', 'unknown')}</td>"
            f"<td>{t.get('details', '')}</td>"
            "</tr>"
        )
    return "".join(out)


def build_html(
    data,
    full_pop=None,
    abaqus_results=None,
    a_sweep=None,
    bc_sweep=None,
    baseline_sweep=None,
    de_sweep=None,
    fe_manifest=None,
    verification_report=None,
):
    inputs = data.get("inputs", {})
    demand = data.get("demand", {})
    winner = data.get("winner", {})
    pareto_rows = "\n".join(
        [
            f"<tr><td>{i+1}</td><td>{p['strategy']}</td><td>{p['safety']:.3f}</td><td>{p['impact']:.3f}</td><td>{p['disp_in']:.3f}</td></tr>"
            for i, p in enumerate(data.get("pareto", []))
        ]
    )
    strategy_bins = {s: [] for s in STRATEGY_ORDER if s != "N"}
    for p in data.get("pareto", []):
        letter = _strategy_letter(p.get("strategy", ""))
        if letter in strategy_bins:
            strategy_bins[letter].append(p)
    def _summarize(label, items):
        if not items:
            return f"<tr><td>{label}</td><td>0</td><td colspan='3' style='color:var(--muted)'>No candidates on frontier</td></tr>"
        safety = sum(p["safety"] for p in items) / len(items)
        impact = sum(p["impact"] for p in items) / len(items)
        disp = sum(p["disp_in"] for p in items) / len(items)
        return f"<tr><td>{label}</td><td>{len(items)}</td><td>{safety:.3f}</td><td>{impact:.3f}</td><td>{disp:.3f}</td></tr>"
    strategy_rows = "\n".join([_summarize(f"Strategy {s}", strategy_bins[s]) for s in strategy_bins])
    full_rows = _full_population_summary(full_pop)
    plot_data = dict(data)
    all_pass, full_frontier = _pareto_from_full_population(full_pop)
    if full_frontier:
        plot_data["pareto"] = full_frontier
        plot_data["all_pass"] = all_pass
    sensitivity_rows = _normalize_sensitivity_rows(
        a_sweep=a_sweep, bc_sweep=bc_sweep, baseline_sweep=baseline_sweep, de_sweep=de_sweep
    )
    sens_a = [r for r in sensitivity_rows if r["strategy"] == "A"]
    sens_b = [r for r in sensitivity_rows if r["strategy"] == "B"]
    sens_c = [r for r in sensitivity_rows if r["strategy"] == "C"]
    pass_fail = (winner.get("pred_disp_in", 999) <= winner.get("limit_in", 0))
    pass_text = "PASS: Joist displacement remains below detachment threshold." if pass_fail else "FAIL: Joist exceeds detachment threshold."
    pass_class = "ok" if pass_fail else "warn"
    ver_summary = (verification_report or {}).get("summary", {})
    ver_passed = ver_summary.get("passed")
    ver_total = ver_summary.get("total")
    ver_failed = ver_summary.get("failed")
    ver_text = (
        f"{ver_passed}/{ver_total} checks passed"
        if isinstance(ver_passed, int) and isinstance(ver_total, int)
        else "Verification report not available"
    )
    ver_class = "ok" if isinstance(ver_failed, int) and ver_failed == 0 else "warn"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Retrofit Simulation Dashboard</title>
  <style>
    :root {{
      --bg: #f3f2ee;
      --card: #fffdf8;
      --ink: #24211f;
      --muted: #6a625b;
      --line: #d9d0c6;
      --accent: #9e3a1f;
      --safe: #1f7a4d;
      --warn: #a56a00;
    }}
    body {{
      margin: 0;
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 10% 10%, #efe5d8, transparent 45%),
        radial-gradient(circle at 90% 0%, #f1d9c9, transparent 30%),
        var(--bg);
    }}
    .wrap {{ max-width: 1100px; margin: 24px auto; padding: 0 16px; }}
    .title {{ font-size: 32px; font-weight: 700; letter-spacing: 0.3px; }}
    .sub {{ color: var(--muted); margin-top: 4px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 12px; margin-top: 16px; }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }}
    .k {{ font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; }}
    .v {{ margin-top: 4px; font-size: 22px; font-weight: 700; }}
    .split {{ display: grid; grid-template-columns: 1.1fr 1fr; gap: 12px; margin-top: 12px; }}
    .triple {{ display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 12px; margin-top: 12px; }}
    .retrofits {{ display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 12px; margin-top: 12px; }}
    .retrofits .card {{ position: relative; overflow: hidden; }}
    .retrofits svg {{ width: 100%; height: 220px; display: block; }}
    .ok {{ color: var(--safe); font-weight: 700; }}
    .warn {{ color: var(--warn); font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 8px; text-align: left; }}
    th {{ color: var(--muted); font-weight: 600; }}
    canvas {{ width: 100%; height: 280px; border: 1px solid var(--line); border-radius: 8px; background: #fff; }}
    .small canvas {{ height: 220px; }}
    @media (max-width: 900px) {{
      .grid {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
      .split {{ grid-template-columns: 1fr; }}
      .triple {{ grid-template-columns: 1fr; }}
      .retrofits {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="title">Masonry Retrofit Simulation Dashboard</div>
    <div class="sub">19th-century fire-cut joist uplift study • ROAR interactive run</div>

    <div class="grid">
      <div class="card"><div class="k">Span</div><div class="v">{inputs.get('span_ft', 0):.1f} ft</div></div>
      <div class="card"><div class="k">Joist Spacing</div><div class="v">{inputs.get('spacing_in', 0):.1f} in</div></div>
      <div class="card"><div class="k">Wind Speed</div><div class="v">{inputs.get('wind_mph', 0):.0f} mph</div></div>
      <div class="card"><div class="k">Design Uplift</div><div class="v">{demand.get('lbf', 0):.2f} lbf / {demand.get('n', 0):.2f} N</div></div>
    </div>

    <div class="split">
      <div class="card">
        <div class="k">Consultant Recommendation</div>
        <div class="v" style="font-size:20px">{winner.get('strategy', 'N/A')}</div>
        <div style="margin-top:8px">Predicted displacement: {winner.get('pred_disp_in', 0):.3f} in (limit {winner.get('limit_in', 0):.3f} in)</div>
        <div>Capacity margin: {winner.get('capacity_margin_lbf', 0):.1f} lbf</div>
        <div>Historic impact score: {winner.get('impact_score', 0):.2f}</div>
        <div style="margin-top:8px" class="{pass_class}">{pass_text}</div>
        <div style="margin-top:10px; color:var(--muted)">{data.get('reasoning', '')}</div>
      </div>
      <div class="card">
        <div class="k">Pareto Frontier</div>
        <div style="margin-top:6px; margin-bottom:8px; color:var(--muted)">x = historic impact (lower better), y = safety (higher better)</div>
        <div style="margin-top:-2px; margin-bottom:8px; font-size:12px; color:var(--muted)">{_strategy_legend_html()}</div>
        <div style="margin-top:-2px; margin-bottom:8px; font-size:12px; color:var(--muted)">Faint points = all passing candidates, solid points/line = Pareto frontier</div>
        {_svg_pareto(plot_data)}
      </div>
    </div>

    <div class="card" style="margin-top:12px">
      <div class="k">Model Verification</div>
      <div style="margin-top:6px" class="{ver_class}">{ver_text}</div>
      <table style="margin-top:8px">
        <thead>
          <tr><th>Status</th><th>Check</th><th>Details</th></tr>
        </thead>
        <tbody>{_verification_rows(verification_report)}</tbody>
      </table>
      <div style="margin-top:8px; color:var(--muted)">Source: verification_report.json (generated by verification_suite.py).</div>
    </div>

    <div class="retrofits">
      <div class="card">
        <div class="k">Strategy A: Gravity Anchor</div>
        <div style="margin-top:6px; margin-bottom:8px; font-size:12px; color:var(--muted)">Vertical core + threaded rod (hidden in wall)</div>
        <img src="strategy_assets/strat_a.png" alt="Strategy A schematic" style="width:100%; height:220px; object-fit:cover; border-radius:8px; border:1px solid var(--line);">
        <div style="margin-top:8px; font-size:12px; color:var(--muted)">Hidden rod transfers joist uplift into masonry mass</div>
      </div>
      <div class="card">
        <div class="k">Strategy B: Clamp Plate</div>
        <div style="margin-top:6px; margin-bottom:8px; font-size:12px; color:var(--muted)">Exterior plate + through-bolt (visible)</div>
        <img src="strategy_assets/strat_b.png" alt="Strategy B schematic" style="width:100%; height:220px; object-fit:cover; border-radius:8px; border:1px solid var(--line);">
        <div style="margin-top:8px; font-size:12px; color:var(--muted)">Through-bolt locks joist</div>
      </div>
      <div class="card">
        <div class="k">Strategy C: Friction Pin</div>
        <div style="margin-top:6px; margin-bottom:8px; font-size:12px; color:var(--muted)">Diagonal adhesive pin (low impact)</div>
        <img src="strategy_assets/strat_c.png" alt="Strategy C schematic" style="width:100%; height:220px; object-fit:cover; border-radius:8px; border:1px solid var(--line);">
        <div style="margin-top:8px; font-size:12px; color:var(--muted)">Epoxy bond + friction</div>
      </div>
      <div class="card">
        <div class="k">Strategy D: Hurricane Strap</div>
        <div style="margin-top:6px; margin-bottom:8px; font-size:12px; color:var(--muted)">Steel strap tying joist to wall core</div>
        <img src="strategy_assets/strat_d.png" alt="Strategy D schematic" style="width:100%; height:220px; object-fit:cover; border-radius:8px; border:1px solid var(--line);">
        <div style="margin-top:8px; font-size:12px; color:var(--muted)">Strap provides direct tension path</div>
      </div>
      <div class="card">
        <div class="k">Strategy E: Uplift Plate</div>
        <div style="margin-top:6px; margin-bottom:8px; font-size:12px; color:var(--muted)">Seat plate with screws into joist/wall</div>
        <img src="strategy_assets/strat_e.png" alt="Strategy E schematic" style="width:100%; height:220px; object-fit:cover; border-radius:8px; border:1px solid var(--line);">
        <div style="margin-top:8px; font-size:12px; color:var(--muted)">Plate + screws resists seat uplift</div>
      </div>
      <div class="card">
        <div class="k">Strategy F: Hybrid Rod + Holdown</div>
        <div style="margin-top:6px; margin-bottom:8px; font-size:12px; color:var(--muted)">22.5 deg epoxy rod + holdown + blocking</div>
        <img src="strategy_assets/strat_f.png" alt="Strategy F schematic" style="width:100%; height:220px; object-fit:cover; border-radius:8px; border:1px solid var(--line);">
        <div style="margin-top:8px; font-size:12px; color:var(--muted)">Rod + holdown create redundant uplift path</div>
      </div>
      <div class="card">
        <div class="k">Strategy G: Holdown</div>
        <div style="margin-top:6px; margin-bottom:8px; font-size:12px; color:var(--muted)">Discrete holdown bracket with anchor bolt</div>
        <img src="strategy_assets/strat_g.png" alt="Strategy G schematic" style="width:100%; height:220px; object-fit:cover; border-radius:8px; border:1px solid var(--line);">
        <div style="margin-top:8px; font-size:12px; color:var(--muted)">Holdown bracket transfers joist tension</div>
      </div>
      <div class="card">
        <div class="k">Strategy H: Hanger + Blocking</div>
        <div style="margin-top:6px; margin-bottom:8px; font-size:12px; color:var(--muted)">LU/HU-style hanger with seat blocking</div>
        <img src="strategy_assets/strat_h.png" alt="Strategy H schematic" style="width:100%; height:220px; object-fit:cover; border-radius:8px; border:1px solid var(--line);">
        <div style="margin-top:8px; font-size:12px; color:var(--muted)">Hanger and blocking reinforce joist seat</div>
      </div>
    </div>

    <div class="card" style="margin-top:12px">
      <div class="k">FE Visual Snapshots (Best Case Per Strategy)</div>
      <table>
        <thead>
          <tr><th>Strategy</th><th>Job</th><th>Before Load</th><th>After: Displacement</th><th>After: Stress</th></tr>
        </thead>
        <tbody>{_fe_image_rows(fe_manifest)}</tbody>
      </table>
      <div style="margin-top:8px; color:var(--muted)">Images are generated by Abaqus postprocessing from each strategy ODB.</div>
    </div>

    <div class="card" style="margin-top:12px">
      <div class="k">Frontier Candidates</div>
      <table id="paretoTable">
        <thead>
          <tr><th>#</th><th>Strategy</th><th>Safety</th><th>Impact</th><th>Disp. (in)</th></tr>
        </thead>
        <tbody>{pareto_rows}</tbody>
      </table>
    </div>

    <div class="card" style="margin-top:12px">
      <div class="k">Strategy Summary (Pareto Frontier)</div>
      <table>
        <thead>
          <tr><th>Strategy</th><th>Count</th><th>Avg Safety</th><th>Avg Impact</th><th>Avg Disp. (in)</th></tr>
        </thead>
        <tbody>{strategy_rows}</tbody>
      </table>
      <div style="margin-top:8px; color:var(--muted)">This summary is based on the Pareto frontier only.</div>
    </div>

    <div class="card" style="margin-top:12px">
      <div class="k">Strategy Summary (Full Population)</div>
      <table>
        <thead>
          <tr><th>Strategy</th><th>Count</th><th>Avg Safety</th><th>Avg Impact</th><th>Avg Disp. (in)</th><th>Pass Rate</th></tr>
        </thead>
        <tbody>{full_rows or "<tr><td colspan='6' style='color:var(--muted)'>Full-population file not found. Generate it by running the optimizer.</td></tr>"}</tbody>
      </table>
    </div>

    <div class="card" style="margin-top:12px">
      <div class="k">Abaqus Results (Extracted)</div>
      <table>
        <thead>
          <tr><th>Job</th><th>Max U2 (m)</th><th>Max Smax (Pa)</th><th>Min Smin (Pa)</th></tr>
        </thead>
        <tbody>
          {''.join([f"<tr><td>{r['job']}</td><td>{r['max_u2']:.6f}</td><td>{r['max_smax']:.6f}</td><td>{r['min_smin']:.6f}</td></tr>" for r in (abaqus_results or {}).get('results', [])]) if abaqus_results else "<tr><td colspan='4' style='color:var(--muted)'>Abaqus results file not found.</td></tr>"}
        </tbody>
      </table>
      <div style="margin-top:8px; color:var(--muted)">These are extracted FE outputs from the latest available Abaqus jobs in this workspace.</div>
    </div>

    <div class="triple" style="margin-top:12px">
      <div class="card small">
        <div class="k">Sensitivity Tornado A</div>
        <div style="margin-top:6px; margin-bottom:8px; color:var(--muted)">Hypothesis sweep impact on U2</div>
        {_svg_tornado(sens_a, "A")}
      </div>
      <div class="card small">
        <div class="k">Sensitivity Tornado B</div>
        <div style="margin-top:6px; margin-bottom:8px; color:var(--muted)">Mesh/friction/ramp impact on U2</div>
        {_svg_tornado(sens_b, "B")}
      </div>
      <div class="card small">
        <div class="k">Sensitivity Tornado C</div>
        <div style="margin-top:6px; margin-bottom:8px; color:var(--muted)">Mesh/friction/ramp impact on U2</div>
        {_svg_tornado(sens_c, "C")}
      </div>
    </div>

    <div class="card" style="margin-top:12px">
      <div class="k">Sensitivity Case Results</div>
      <table>
        <thead>
          <tr><th>#</th><th>Strategy</th><th>Case</th><th>Status</th><th>Max U2 (m)</th><th>Max Smax (Pa)</th><th>Pass/Fail</th></tr>
        </thead>
        <tbody>{_sensitivity_table_rows(sensitivity_rows)}</tbody>
      </table>
    </div>

    <div class="card" style="margin-top:12px">
      <div class="k">Robustness Ranking</div>
      <table>
        <thead>
          <tr><th>Strategy</th><th>Valid Runs</th><th>Mean U2 (m)</th><th>Worst-Case U2 (m)</th><th>Pass Rate (U2≤0.0127m)</th></tr>
        </thead>
        <tbody>{_robustness_rows(sensitivity_rows)}</tbody>
      </table>
      <div style="margin-top:8px; color:var(--muted)">Computed from sensitivity runs only; strategies without sensitivity cases are shown with zero runs.</div>
    </div>
  </div>

  <!-- Static HTML; no JS required -->
</body>
</html>
"""


def main():
    root = Path(__file__).resolve().parent
    log_path = root / "roar_interactive_run.log"
    html_path = root / "retrofit_dashboard.html"
    data_path = root / "retrofit_dashboard_data.json"
    full_path = root / "full_population_results.json"
    abaqus_path = root / "abaqus_results.json"
    sweep_a_path = root / "sweep_A_results.json"
    bc_sens_path = root / "bc_sensitivity_results.json"
    baseline_path = root / "baseline_results.json"
    de_path = root / "de_results.json"
    fe_manifest_path = root / "fe_images_manifest.json"
    verification_path = root / "verification_report.json"

    log_text = log_path.read_text(encoding="utf-8")
    data = parse_log(log_text)
    full_pop = None
    if full_path.exists():
        full_pop = json.loads(full_path.read_text(encoding="utf-8"))
    abaqus_results = None
    if abaqus_path.exists():
        abaqus_results = json.loads(abaqus_path.read_text(encoding="utf-8"))
    sweep_a = None
    if sweep_a_path.exists():
        sweep_a = json.loads(sweep_a_path.read_text(encoding="utf-8"))
    bc_sensitivity = None
    if bc_sens_path.exists():
        bc_sensitivity = json.loads(bc_sens_path.read_text(encoding="utf-8"))
    baseline_sweep = None
    if baseline_path.exists():
        baseline_sweep = json.loads(baseline_path.read_text(encoding="utf-8"))
    de_sweep = None
    if de_path.exists():
        de_sweep = json.loads(de_path.read_text(encoding="utf-8"))
    fe_manifest = None
    if fe_manifest_path.exists():
        fe_manifest = json.loads(fe_manifest_path.read_text(encoding="utf-8"))
    verification_report = None
    if verification_path.exists():
        verification_report = json.loads(verification_path.read_text(encoding="utf-8"))
        data["verification"] = verification_report.get("summary", {})
        
    # --- NOVO: Executar geração de Pareto e integrar na raiz dos dados exportados ---
    all_pass, full_frontier = _pareto_from_full_population(full_pop)
    if full_frontier:
        data["pareto"] = full_frontier
        data["all_pass"] = all_pass
        
        topsis_candidates = [p for p in full_frontier if p.get("is_topsis_winner")]
        if topsis_candidates:
            data["winner_topsis"] = topsis_candidates[0]
        else:
            data["winner_topsis"] = data["winner"]
        
    data_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    html_path.write_text(
        build_html(
            data,
            full_pop=full_pop,
            abaqus_results=abaqus_results,
            a_sweep=sweep_a,
            bc_sweep=bc_sensitivity,
            baseline_sweep=baseline_sweep,
            de_sweep=de_sweep,
            fe_manifest=fe_manifest,
            verification_report=verification_report,
        ),
        encoding="utf-8",
    )
    print(f"Wrote: {html_path}")
    print(f"Wrote: {data_path}")
    
    # --- NOVO: Copiar JSONs para a pasta public E dist do React App ---
    react_public_data_path = root / "tornado-control-center" / "public" / "data.json"
    react_public_manifest_path = root / "tornado-control-center" / "public" / "manifest.json"
    react_dist_data_path = root / "tornado-control-center" / "dist" / "data.json"
    react_dist_manifest_path = root / "tornado-control-center" / "dist" / "manifest.json"
    
    try:
        react_public_data_path.parent.mkdir(parents=True, exist_ok=True)
        react_public_data_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        if fe_manifest:
            react_public_manifest_path.write_text(json.dumps(fe_manifest, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"Aviso: Não foi possível copiar para public: {e}")
        
    try:
        react_dist_data_path.parent.mkdir(parents=True, exist_ok=True)
        react_dist_data_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        if fe_manifest:
            react_dist_manifest_path.write_text(json.dumps(fe_manifest, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"Aviso: Não foi possível copiar para dist: {e}")


if __name__ == "__main__":
    main()
