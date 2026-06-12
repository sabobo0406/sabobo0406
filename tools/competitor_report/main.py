"""競合アカウントを巡回して、伸びた投稿をレポートにまとめる。

使い方:
    python main.py            # config.json のアカウントを巡回してレポート生成
"""

import json
import os
import sys
from datetime import date

from fetchers import fetch_account
from report import find_growing_posts, render_report

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_DIR = os.path.join(BASE_DIR, "data", "snapshots")
REPORT_DIR = os.path.join(BASE_DIR, "reports")


def load_previous_snapshot() -> dict:
    if not os.path.isdir(SNAPSHOT_DIR):
        return {}
    files = sorted(f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json"))
    if not files:
        return {}
    with open(os.path.join(SNAPSHOT_DIR, files[-1]), encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    with open(os.path.join(BASE_DIR, "config.json"), encoding="utf-8") as f:
        config = json.load(f)

    threshold = config.get("growth_threshold", 2.0)
    min_growth = config.get("min_growth", 100)
    max_posts = config.get("max_posts_per_account", 30)

    previous = load_previous_snapshot()
    today_str = date.today().isoformat()

    snapshot = {}
    results = {}
    for account in config["accounts"]:
        name = account["name"]
        try:
            posts = fetch_account(account, max_posts)
        except Exception as e:  # 1アカウント失敗しても巡回は続ける
            print(f"[警告] {name}: {e}", file=sys.stderr)
            results[name] = {"error": str(e)}
            continue

        snapshot[name] = posts
        prev_posts = previous.get(name, {})
        if not prev_posts:
            results[name] = {"first_run": True}
            continue

        growing, new_posts = find_growing_posts(posts, prev_posts, threshold, min_growth)
        results[name] = {"growing": growing, "new": new_posts}

    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    with open(os.path.join(SNAPSHOT_DIR, f"{today_str}.json"), "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    os.makedirs(REPORT_DIR, exist_ok=True)
    report_path = os.path.join(REPORT_DIR, f"{today_str}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(render_report(today_str, results))

    print(f"レポートを作成しました: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
