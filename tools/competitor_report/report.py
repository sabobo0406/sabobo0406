"""スナップショット比較と Markdown レポート生成。"""

import statistics


def find_growing_posts(
    today: dict, previous: dict, threshold: float, min_growth: int
) -> tuple[list, list]:
    """前回スナップショットと比較して伸びた投稿を抽出する。

    Returns:
        (伸びた既存投稿のリスト, 好調な新規投稿のリスト)
        既存投稿: {"post": ..., "growth": {"views": int, "likes": int, "comments": int}}
    """
    deltas = []
    for post_id, post in today.items():
        if post_id in previous:
            prev_m = previous[post_id]["metrics"]
            growth = {
                k: post["metrics"][k] - prev_m.get(k, 0) for k in post["metrics"]
            }
            deltas.append({"post": post, "growth": growth})

    growing = []
    if deltas:
        median_views_growth = statistics.median(d["growth"]["views"] for d in deltas)
        bar = max(min_growth, threshold * max(median_views_growth, 0))
        growing = sorted(
            (d for d in deltas if d["growth"]["views"] >= bar),
            key=lambda d: d["growth"]["views"],
            reverse=True,
        )

    # 新規投稿: アカウント全体の再生数中央値を初日で超えていれば好調とみなす
    new_posts = []
    if previous:
        median_views = statistics.median(p["metrics"]["views"] for p in today.values())
        new_posts = sorted(
            (
                p
                for pid, p in today.items()
                if pid not in previous and p["metrics"]["views"] >= max(median_views, min_growth)
            ),
            key=lambda p: p["metrics"]["views"],
            reverse=True,
        )

    return growing, new_posts


def render_report(date: str, results: dict) -> str:
    """アカウントごとの結果を Markdown にまとめる。

    results: {account_name: {"growing": [...], "new": [...], "error": str|None,
                             "first_run": bool}}
    """
    lines = [f"# 競合巡回レポート {date}", ""]

    total = sum(len(r.get("growing", [])) + len(r.get("new", [])) for r in results.values())
    lines.append(f"伸びた投稿: **{total} 件**")
    lines.append("")

    for name, r in results.items():
        lines.append(f"## {name}")
        lines.append("")

        if r.get("error"):
            lines.append(f"⚠️ 取得に失敗しました: {r['error']}")
            lines.append("")
            continue

        if r.get("first_run"):
            lines.append("初回巡回のため基準データを保存しました。次回から伸びを表示します。")
            lines.append("")
            continue

        if not r["growing"] and not r["new"]:
            lines.append("特に伸びた投稿はありませんでした。")
            lines.append("")
            continue

        if r["growing"]:
            lines.append("### 📈 伸びた投稿")
            lines.append("")
            lines.append("| 投稿 | 再生/閲覧 (+増分) | いいね (+増分) | コメント (+増分) |")
            lines.append("|---|---|---|---|")
            for d in r["growing"]:
                p, g = d["post"], d["growth"]
                m = p["metrics"]
                title = f"[{p['title']}]({p['url']})" if p["url"] else p["title"]
                lines.append(
                    f"| {title} | {m['views']:,} (+{g['views']:,}) "
                    f"| {m['likes']:,} (+{g['likes']:,}) "
                    f"| {m['comments']:,} (+{g['comments']:,}) |"
                )
            lines.append("")

        if r["new"]:
            lines.append("### 🆕 好調な新規投稿")
            lines.append("")
            lines.append("| 投稿 | 公開日 | 再生/閲覧 | いいね |")
            lines.append("|---|---|---|---|")
            for p in r["new"]:
                m = p["metrics"]
                title = f"[{p['title']}]({p['url']})" if p["url"] else p["title"]
                lines.append(
                    f"| {title} | {p['published_at']} | {m['views']:,} | {m['likes']:,} |"
                )
            lines.append("")

    return "\n".join(lines) + "\n"
