"""投稿データの取得。platform ごとにフェッチャーを定義する。

すべてのフェッチャーは次の形式の dict を返す:
    {post_id: {"title": str, "url": str, "published_at": str,
               "metrics": {"views": int, "likes": int, "comments": int}}}
"""

import csv
import json
import os
import urllib.parse
import urllib.request

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def _youtube_get(endpoint: str, params: dict) -> dict:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("環境変数 YOUTUBE_API_KEY が設定されていません")
    params = {**params, "key": api_key}
    url = f"{YOUTUBE_API_BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def fetch_youtube(account: dict, max_posts: int) -> dict:
    """チャンネルの最新動画とその統計を取得する。"""
    channel_id = account["channel_id"]

    channels = _youtube_get("channels", {"part": "contentDetails", "id": channel_id})
    if not channels.get("items"):
        raise RuntimeError(f"チャンネルが見つかりません: {channel_id}")
    uploads_playlist = channels["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    items = _youtube_get(
        "playlistItems",
        {"part": "snippet", "playlistId": uploads_playlist, "maxResults": min(max_posts, 50)},
    )
    video_ids = [it["snippet"]["resourceId"]["videoId"] for it in items.get("items", [])]
    if not video_ids:
        return {}

    videos = _youtube_get(
        "videos", {"part": "snippet,statistics", "id": ",".join(video_ids)}
    )

    posts = {}
    for v in videos.get("items", []):
        stats = v.get("statistics", {})
        posts[v["id"]] = {
            "title": v["snippet"]["title"],
            "url": f"https://www.youtube.com/watch?v={v['id']}",
            "published_at": v["snippet"]["publishedAt"][:10],
            "metrics": {
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
            },
        }
    return posts


def fetch_csv(account: dict, max_posts: int) -> dict:
    """手動エクスポートした CSV から読み込む(Instagram インサイト等)。"""
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
    "youtube": fetch_youtube,
    "csv": fetch_csv,
}


def fetch_account(account: dict, max_posts: int) -> dict:
    platform = account["platform"]
    if platform not in FETCHERS:
        raise ValueError(f"未対応の platform です: {platform}(対応: {', '.join(FETCHERS)})")
    return FETCHERS[platform](account, max_posts)
