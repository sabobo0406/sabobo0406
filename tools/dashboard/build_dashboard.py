"""data/metrics.csv から一画面の HTML ダッシュボードを生成する。

使い方:
    python build_dashboard.py
    → dashboard.html をブラウザで開く
"""

import csv
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "metrics.csv")
OUT_PATH = os.path.join(BASE_DIR, "dashboard.html")

CHART_COLORS = ["#4e79a7", "#f28e2b", "#59a14f", "#e15759", "#76b7b2", "#af7aa1"]

TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ダッシュボード</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  body {{ font-family: "Hiragino Sans", "Yu Gothic", sans-serif; margin: 0;
         background: #f5f6f8; color: #222; }}
  header {{ background: #fff; padding: 16px 24px; border-bottom: 1px solid #e3e5e8; }}
  h1 {{ font-size: 18px; margin: 0; }}
  .updated {{ color: #888; font-size: 12px; }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 24px; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px; margin-bottom: 24px; }}
  .card {{ background: #fff; border-radius: 10px; padding: 16px 20px;
           box-shadow: 0 1px 3px rgba(0,0,0,.06); }}
  .card .label {{ font-size: 13px; color: #666; }}
  .card .value {{ font-size: 28px; font-weight: 700; margin: 4px 0; }}
  .card .diff {{ font-size: 13px; }}
  .up {{ color: #1a8a3c; }} .down {{ color: #c0392b; }} .flat {{ color: #888; }}
  .charts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
             gap: 16px; }}
  .chart-box {{ background: #fff; border-radius: 10px; padding: 16px;
                box-shadow: 0 1px 3px rgba(0,0,0,.06); }}
  .chart-box h2 {{ font-size: 14px; margin: 0 0 8px; color: #444; }}
</style>
</head>
<body>
<header>
  <h1>📊 ダッシュボード</h1>
  <div class="updated">最終データ: {latest_date}(全 {row_count} 件)</div>
</header>
<main>
  <div class="cards">{cards}</div>
  <div class="charts">{charts}</div>
</main>
<script>
const labels = {labels_json};
const series = {series_json};
const colors = {colors_json};
Object.entries(series).forEach(([name, values], i) => {{
  new Chart(document.getElementById("chart-" + i), {{
    type: "line",
    data: {{
      labels: labels,
      datasets: [{{
        label: name, data: values, borderColor: colors[i % colors.length],
        backgroundColor: colors[i % colors.length] + "33", fill: true, tension: 0.25,
      }}],
    }},
    options: {{ plugins: {{ legend: {{ display: false }} }},
               scales: {{ y: {{ beginAtZero: false }} }} }},
  }});
}});
</script>
</body>
</html>
"""


def format_number(n: float) -> str:
    return f"{n:,.0f}" if n == int(n) else f"{n:,.1f}"


def build_card(name: str, values: list[float]) -> str:
    latest = values[-1]
    diff = latest - values[-2] if len(values) >= 2 else 0
    week = latest - values[-8] if len(values) >= 8 else latest - values[0]
    cls = "up" if diff > 0 else "down" if diff < 0 else "flat"
    sign = "+" if diff > 0 else ""
    wsign = "+" if week > 0 else ""
    return (
        f'<div class="card"><div class="label">{name}</div>'
        f'<div class="value">{format_number(latest)}</div>'
        f'<div class="diff {cls}">前回比 {sign}{format_number(diff)} / '
        f"直近7件 {wsign}{format_number(week)}</div></div>"
    )


def main() -> int:
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("data/metrics.csv にデータがありません", file=sys.stderr)
        return 1

    rows.sort(key=lambda r: r["date"])
    labels = [r["date"] for r in rows]
    metric_names = [k for k in rows[0] if k != "date"]
    series = {
        name: [float(r.get(name) or 0) for r in rows] for name in metric_names
    }

    cards = "".join(build_card(name, values) for name, values in series.items())
    charts = "".join(
        f'<div class="chart-box"><h2>{name}</h2><canvas id="chart-{i}"></canvas></div>'
        for i, name in enumerate(series)
    )

    html = TEMPLATE.format(
        latest_date=labels[-1],
        row_count=len(rows),
        cards=cards,
        charts=charts,
        labels_json=json.dumps(labels, ensure_ascii=False),
        series_json=json.dumps(series, ensure_ascii=False),
        colors_json=json.dumps(CHART_COLORS),
    )
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"ダッシュボードを生成しました: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
