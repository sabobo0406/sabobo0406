#!/usr/bin/env python3
"""
Twitter Paper Downloader
========================
X(Twitter)アカウント @ajog_thegray を定期的に監視し、
ツイートで紹介されている論文のPDFをダウンロードするツール。

使い方:
  1. .env ファイルに設定を記入
  2. python twitter_paper_downloader.py         # 1回実行
  3. python twitter_paper_downloader.py --watch  # 定期監視モード
"""

import os
import re
import json
import time
import logging
import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote

import requests
from dotenv import load_dotenv

# ── ログ設定 ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── 定数 ──────────────────────────────────────────────────
load_dotenv()

TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")
TARGET_USERNAME = os.getenv("TARGET_USERNAME", "ajog_thegray")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "papers")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "60"))
STATE_FILE = os.getenv("STATE_FILE", "downloader_state.json")
UNPAYWALL_EMAIL = os.getenv("UNPAYWALL_EMAIL", "")

# 論文関連ドメインのパターン
PAPER_DOMAINS = [
    "doi.org",
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "scholar.google.com",
    "arxiv.org",
    "biorxiv.org",
    "medrxiv.org",
    "sciencedirect.com",
    "springer.com",
    "link.springer.com",
    "nature.com",
    "wiley.com",
    "onlinelibrary.wiley.com",
    "thelancet.com",
    "bmj.com",
    "nejm.org",
    "jamanetwork.com",
    "journals.lww.com",
    "academic.oup.com",
    "ajog.org",
    "greenjournal.org",
    "obgyn.onlinelibrary.wiley.com",
]

# DOI正規表現
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s,;\"'<>\])}]+")

# URL正規表現
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")


# ── 状態管理 ──────────────────────────────────────────────
def load_state() -> dict:
    """前回の実行状態を読み込む"""
    if Path(STATE_FILE).exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_tweet_id": None, "downloaded_dois": [], "downloaded_urls": []}


def save_state(state: dict):
    """実行状態を保存する"""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# ── Twitter API ───────────────────────────────────────────
def get_user_id(username: str) -> str | None:
    """ユーザー名からユーザーIDを取得"""
    url = f"https://api.twitter.com/2/users/by/username/{username}"
    headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("id")
    except requests.RequestException as e:
        logger.error(f"ユーザーID取得失敗: {e}")
        return None


def fetch_tweets(user_id: str, since_id: str | None = None) -> list[dict]:
    """ユーザーの最新ツイートを取得"""
    url = f"https://api.twitter.com/2/users/{user_id}/tweets"
    headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
    params = {
        "max_results": 100,
        "tweet.fields": "created_at,entities,text",
        "expansions": "attachments.media_keys",
    }
    if since_id:
        params["since_id"] = since_id

    tweets = []
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        tweets = data.get("data", [])
        logger.info(f"{len(tweets)} 件のツイートを取得しました")
    except requests.RequestException as e:
        logger.error(f"ツイート取得失敗: {e}")
    return tweets


# ── URL / DOI 抽出 ────────────────────────────────────────
def extract_urls_from_tweet(tweet: dict) -> list[str]:
    """ツイートからURLを抽出"""
    urls = []

    # entities からURL取得
    entities = tweet.get("entities", {})
    for u in entities.get("urls", []):
        expanded = u.get("expanded_url") or u.get("url", "")
        if expanded:
            urls.append(expanded)

    # テキストからもURL抽出（entitiesに含まれないケース対策）
    text = tweet.get("text", "")
    for match in URL_PATTERN.findall(text):
        clean = match.rstrip(".,;:!?)")
        if clean not in urls:
            urls.append(clean)

    return urls


def extract_dois(urls: list[str], text: str = "") -> list[str]:
    """URLやテキストからDOIを抽出"""
    dois = set()

    # URLからDOI抽出
    for url in urls:
        if "doi.org/" in url:
            # https://doi.org/10.xxxx/yyyy
            parts = url.split("doi.org/", 1)
            if len(parts) == 2:
                doi = unquote(parts[1]).strip().rstrip(".,;:!?)")
                dois.add(doi)

    # テキストからDOI抽出
    for match in DOI_PATTERN.findall(text):
        doi = match.rstrip(".,;:!?)")
        dois.add(doi)

    return list(dois)


def is_paper_url(url: str) -> bool:
    """論文関連のURLかどうか判定"""
    parsed = urlparse(url)
    domain = parsed.netloc.lower().lstrip("www.")
    return any(d in domain for d in PAPER_DOMAINS)


def filter_paper_urls(urls: list[str]) -> list[str]:
    """論文関連のURLだけをフィルタ"""
    return [u for u in urls if is_paper_url(u)]


# ── DOI → PDF 解決 ────────────────────────────────────────
def resolve_doi_to_pdf(doi: str) -> str | None:
    """DOIからPDFのURLを解決する（Unpaywall API利用）"""
    if not UNPAYWALL_EMAIL:
        logger.warning("UNPAYWALL_EMAIL が設定されていません。Unpaywall APIを使えません。")
        return None

    url = f"https://api.unpaywall.org/v2/{doi}"
    params = {"email": UNPAYWALL_EMAIL}
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            # best_oa_location を優先
            best = data.get("best_oa_location")
            if best:
                pdf_url = best.get("url_for_pdf") or best.get("url")
                if pdf_url:
                    logger.info(f"Unpaywall: {doi} -> {pdf_url}")
                    return pdf_url
            # 他のOAロケーションも確認
            for loc in data.get("oa_locations", []):
                pdf_url = loc.get("url_for_pdf") or loc.get("url")
                if pdf_url:
                    logger.info(f"Unpaywall (alt): {doi} -> {pdf_url}")
                    return pdf_url
    except requests.RequestException as e:
        logger.warning(f"Unpaywall APIエラー ({doi}): {e}")
    return None


def try_direct_pdf_from_url(url: str) -> str | None:
    """URLから直接PDFリンクを取得する試み"""
    # arXiv
    if "arxiv.org/abs/" in url:
        return url.replace("/abs/", "/pdf/") + ".pdf"
    if "arxiv.org/pdf/" in url:
        return url if url.endswith(".pdf") else url + ".pdf"

    # bioRxiv / medRxiv
    if ("biorxiv.org" in url or "medrxiv.org" in url) and "/content/" in url:
        if not url.endswith(".full.pdf"):
            base = url.split("?")[0].rstrip("/")
            return base + ".full.pdf"

    # PubMed Central
    if "ncbi.nlm.nih.gov/pmc/articles/" in url:
        pmc_match = re.search(r"PMC\d+", url)
        if pmc_match:
            pmc_id = pmc_match.group()
            return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/"

    # 既にPDFリンクの場合
    if url.lower().endswith(".pdf"):
        return url

    return None


# ── PDF ダウンロード ──────────────────────────────────────
def download_pdf(pdf_url: str, filename: str) -> bool:
    """PDFをダウンロードして保存"""
    download_path = Path(DOWNLOAD_DIR)
    download_path.mkdir(parents=True, exist_ok=True)

    filepath = download_path / filename
    if filepath.exists():
        logger.info(f"既にダウンロード済み: {filename}")
        return True

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PaperDownloader/1.0)",
        "Accept": "application/pdf,*/*",
    }
    try:
        resp = requests.get(pdf_url, headers=headers, timeout=60, stream=True)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        # PDFかどうか簡易チェック
        first_chunk = b""
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if not first_chunk:
                    first_chunk = chunk
                f.write(chunk)

        # PDFヘッダチェック
        if not first_chunk.startswith(b"%PDF") and "pdf" not in content_type.lower():
            logger.warning(f"PDFではない可能性があります: {filename} (Content-Type: {content_type})")
            filepath.unlink()
            return False

        size_mb = filepath.stat().st_size / (1024 * 1024)
        logger.info(f"ダウンロード完了: {filename} ({size_mb:.1f} MB)")
        return True

    except requests.RequestException as e:
        logger.error(f"ダウンロード失敗 ({pdf_url}): {e}")
        if filepath.exists():
            filepath.unlink()
        return False


def make_filename(doi: str = "", url: str = "", tweet_text: str = "") -> str:
    """ダウンロードファイル名を生成"""
    if doi:
        safe = re.sub(r"[^\w\-.]", "_", doi)
        return f"{safe}.pdf"
    if url:
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        parsed = urlparse(url)
        path_part = parsed.path.strip("/").split("/")[-1] if parsed.path else ""
        safe_part = re.sub(r"[^\w\-.]", "_", path_part)[:50]
        return f"{safe_part}_{url_hash}.pdf"
    return f"paper_{hashlib.md5(tweet_text.encode()).hexdigest()[:12]}.pdf"


# ── メイン処理 ────────────────────────────────────────────
def process_tweet(tweet: dict, state: dict) -> list[str]:
    """1つのツイートを処理し、ダウンロードしたファイル名のリストを返す"""
    text = tweet.get("text", "")
    tweet_id = tweet.get("id", "")
    created = tweet.get("created_at", "")
    downloaded = []

    logger.info(f"--- ツイート処理 (ID: {tweet_id}, {created}) ---")
    logger.info(f"テキスト: {text[:120]}...")

    urls = extract_urls_from_tweet(tweet)
    dois = extract_dois(urls, text)
    paper_urls = filter_paper_urls(urls)

    if not dois and not paper_urls:
        logger.info("論文関連のURLが見つかりませんでした")
        return downloaded

    # DOIベースのダウンロード
    for doi in dois:
        if doi in state["downloaded_dois"]:
            logger.info(f"既にダウンロード済みDOI: {doi}")
            continue

        filename = make_filename(doi=doi)
        pdf_url = resolve_doi_to_pdf(doi)

        if pdf_url and download_pdf(pdf_url, filename):
            state["downloaded_dois"].append(doi)
            downloaded.append(filename)
            continue

        # Unpaywall で見つからない場合、直接URLを試す
        for url in paper_urls:
            direct = try_direct_pdf_from_url(url)
            if direct and download_pdf(direct, filename):
                state["downloaded_dois"].append(doi)
                downloaded.append(filename)
                break

    # DOIが無いがURLがある場合
    for url in paper_urls:
        if url in state["downloaded_urls"]:
            continue
        # DOI経由で既にダウンロード済みなら飛ばす
        url_dois = extract_dois([url])
        if any(d in state["downloaded_dois"] for d in url_dois):
            continue

        direct = try_direct_pdf_from_url(url)
        if direct:
            filename = make_filename(url=url)
            if download_pdf(direct, filename):
                state["downloaded_urls"].append(url)
                downloaded.append(filename)

    return downloaded


def run_once():
    """1回の実行: ツイートを取得して論文をダウンロード"""
    if not TWITTER_BEARER_TOKEN:
        logger.error(
            "TWITTER_BEARER_TOKEN が設定されていません。\n"
            ".envファイルに TWITTER_BEARER_TOKEN=xxxxx を設定してください。\n"
            "取得方法: https://developer.twitter.com/en/portal/dashboard"
        )
        return

    state = load_state()

    # ユーザーID取得
    user_id = get_user_id(TARGET_USERNAME)
    if not user_id:
        logger.error(f"ユーザー @{TARGET_USERNAME} が見つかりません")
        return

    logger.info(f"@{TARGET_USERNAME} (ID: {user_id}) のツイートを取得中...")

    # ツイート取得
    tweets = fetch_tweets(user_id, state.get("last_tweet_id"))
    if not tweets:
        logger.info("新しいツイートはありません")
        return

    # 最新のツイートIDを記録
    state["last_tweet_id"] = tweets[0]["id"]

    # 各ツイートを処理
    total_downloaded = []
    for tweet in tweets:
        downloaded = process_tweet(tweet, state)
        total_downloaded.extend(downloaded)

    save_state(state)

    logger.info(f"=== 完了: {len(total_downloaded)} 件のPDFをダウンロードしました ===")
    for f in total_downloaded:
        logger.info(f"  - {f}")


def watch_mode():
    """定期監視モード"""
    logger.info(
        f"定期監視モード開始: @{TARGET_USERNAME} を {CHECK_INTERVAL_MINUTES}分間隔で監視します"
    )
    logger.info(f"ダウンロード先: {Path(DOWNLOAD_DIR).resolve()}")
    logger.info("停止するには Ctrl+C を押してください")

    while True:
        try:
            run_once()
        except Exception as e:
            logger.error(f"実行エラー: {e}", exc_info=True)

        logger.info(f"次の確認まで {CHECK_INTERVAL_MINUTES} 分待機中...")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)


# ── エントリーポイント ────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="X(Twitter)アカウントから論文PDFを自動ダウンロード"
    )
    parser.add_argument(
        "--watch", action="store_true", help="定期監視モード（デフォルト: 1回実行）"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help=f"監視間隔（分）（デフォルト: {CHECK_INTERVAL_MINUTES}）",
    )
    args = parser.parse_args()

    if args.interval:
        global CHECK_INTERVAL_MINUTES
        CHECK_INTERVAL_MINUTES = args.interval

    if args.watch:
        watch_mode()
    else:
        run_once()


if __name__ == "__main__":
    main()
