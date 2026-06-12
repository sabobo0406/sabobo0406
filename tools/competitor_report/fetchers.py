"""投稿データの取得。platform ごとにフェッチャーを定義する。

すべてのフェッチャーは次の形式の dict を返す:
    {post_id: {"title": str, "url": str, "published_at": str,
               "metrics": {"views": int, "likes": int, "comments": int}}}

"views" は伸びの判定に使う主要指標。プラットフォームごとに中身が異なる:
    x         → インプレッション数
    instagram → いいね数(競合の再生数は API で取得できないため)
    note      → スキ数
    csv       → CSV の views 列(Voicy など手入力用)
"""

import csv
import json
import os
import urllib.parse
import urllib.request

USER_AGENT = "Mozilla/5.0 (competitor-report; +https://github.com/sabobo0406)"


def _get_json(url: str, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"環境変数 {name} が設定されていません")
    return value


def fetch_x(account: dict, max_posts: int) -> dict:
    """X API v2 でユーザーの最新ポストと public_metrics を取得する。

    X_BEARER_TOKEN が必要(無料プランは読み取り回数が非常に少ないため、
    日次巡回には Basic 以上のプランを推奨)。
    """
    bearer = _require_env("X_BEARER_TOKEN")
    headers = {"Authorization": f"Bearer {bearer}"}
    username = account["username"].lstrip("@")

    user = _get_json(
        f"https://api.twitter.com/2/users/by/username/{urllib.parse.quote(username)}",
        headers,
    )
    if "data" not in user:
        raise RuntimeError(f"ユーザーが見つかりません: @{username}")
    user_id = user["data"]["id"]

    params = urllib.parse.urlencode(
        {
            "max_results": min(max(max_posts, 5), 100),
            "exclude": "retweets,replies",
            "tweet.fields": "public_metrics,created_at,text",
        }
    )
    tweets = _get_json(
        f"https://api.twitter.com/2/users/{user_id}/tweets?{params}", headers
    )

    posts = {}
    for t in tweets.get("data", []):
        m = t.get("public_metrics", {})
        title = t["text"].replace("\n", " ")
        posts[t["id"]] = {
            "title": title[:60] + ("…" if len(title) > 60 else ""),
            "url": f"https://x.com/{username}/status/{t['id']}",
            "published_at": t.get("created_at", "")[:10],
            "metrics": {
                "views": int(m.get("impression_count", 0)),
                "likes": int(m.get("like_count", 0)),
                "comments": int(m.get("reply_count", 0)),
            },
        }
    return posts


def fetch_instagram(account: dict, max_posts: int) -> dict:
    """Instagram Graph API の Business Discovery で競合の投稿を取得する。

    自分の Instagram プロ(ビジネス/クリエイター)アカウントと Meta アプリが必要:
      IG_ACCESS_TOKEN … Meta アプリのアクセストークン
      IG_USER_ID      … 自分の Instagram ユーザー ID
    競合アカウントもプロアカウントである必要がある。
    """
    token = _require_env("IG_ACCESS_TOKEN")
    ig_user_id = _require_env("IG_USER_ID")
    username = account["username"].lstrip("@")

    fields = (
        f"business_discovery.username({username})"
        f"{{media.limit({max_posts}){{id,caption,permalink,timestamp,like_count,comments_count}}}}"
    )
    params = urllib.parse.urlencode({"fields": fields, "access_token": token})
    data = _get_json(f"https://graph.facebook.com/v21.0/{ig_user_id}?{params}")

    media = data.get("business_discovery", {}).get("media", {}).get("data", [])
    posts = {}
    for m in media:
        caption = (m.get("caption") or "").replace("\n", " ")
        likes = int(m.get("like_count", 0))
        posts[m["id"]] = {
            "title": caption[:60] + ("…" if len(caption) > 60 else ""),
            "url": m.get("permalink", ""),
            "published_at": m.get("timestamp", "")[:10],
            "metrics": {
                "views": likes,  # 競合の再生数は取得不可のため、いいね数を主要指標にする
                "likes": likes,
                "comments": int(m.get("comments_count", 0)),
            },
        }
    return posts


def fetch_note(account: dict, max_posts: int) -> dict:
    """note の公開 API でクリエイターの最新記事とスキ数を取得する(キー不要)。

    urlname は note.com/◯◯◯ の ◯◯◯ 部分。
    """
    urlname = account["urlname"]
    data = _get_json(
        f"https://note.com/api/v2/creators/{urllib.parse.quote(urlname)}/contents"
        "?kind=note&page=1"
    )

    posts = {}
    for c in data.get("data", {}).get("contents", [])[:max_posts]:
        likes = int(c.get("likeCount", 0))
        posts[str(c["id"])] = {
            "title": c.get("name", ""),
            "url": c.get("noteUrl") or f"https://note.com/{urlname}/n/{c.get('key', '')}",
            "published_at": (c.get("publishAt") or "")[:10].replace("/", "-"),
            "metrics": {
                "views": likes,  # note の閲覧数は非公開のため、スキ数を主要指標にする
                "likes": likes,
                "comments": int(c.get("commentCount", 0)),
            },
        }
    return posts


def fetch_csv(account: dict, max_posts: int) -> dict:
    """手動エクスポート・手入力した CSV から読み込む(Voicy など API のない媒体用)。"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, account["csv_path"])

    posts = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in list(csv.DictReader(f))[:max_posts]:
            posts[row["post_id"]] = {
                "title": row.get("title", ""),
                "url": row.get("url", ""),
                "published_at": row.get("published_at", ""),
                "metrics": {
                    "views": int(row.get("views") or 0),
                    "likes": int(row.get("likes") or 0),
                    "comments": int(row.get("comments") or 0),
                },
            }
    return posts


FETCHERS = {
    "x": fetch_x,
    "instagram": fetch_instagram,
    "note": fetch_note,
    "csv": fetch_csv,
}


def fetch_account(account: dict, max_posts: int) -> dict:
    platform = account["platform"]
    if platform not in FETCHERS:
        raise ValueError(f"未対応の platform です: {platform}(対応: {', '.join(FETCHERS)})")
    return FETCHERS[platform](account, max_posts)
