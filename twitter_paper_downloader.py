#!/usr/bin/env python3
"""
Twitter Paper Downloader (ブラウザ版)
=====================================
X(Twitter)アカウント @ajog_thegray をブラウザで開いて
ツイートから論文リンクを抽出し、PDFをダウンロードするツール。

API不要 - Playwrightでブラウザを自動操作します。

使い方:
  1. pip install -r requirements.txt && playwright install chromium
  2. python twitter_paper_downloader.py                # 1回実行
  3. python twitter_paper_downloader.py --watch         # 定期監視
  4. python twitter_paper_downloader.py --head          # ブラウザ表示して実行
"""

import os
import re
import json
import time
import logging
import argparse
import hashlib
from pathlib import Path
from __future__ import annotations
from typing import Optional
from urllib.parse import urlparse, unquote

import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ── ログ設定 ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── 定数 ──────────────────────────────────────────────────
load_dotenv()

TARGET_USERNAME = os.getenv("TARGET_USERNAME", "ajog_thegray")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "papers")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "60"))
STATE_FILE = os.getenv("STATE_FILE", "downloader_state.json")
UNPAYWALL_EMAIL = os.getenv("UNPAYWALL_EMAIL", "")
SCROLL_COUNT = int(os.getenv("SCROLL_COUNT", "5"))

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

DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s,;\"'<>\])}]+")
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")


# ── 状態管理 ──────────────────────────────────────────────
def load_state() -> dict:
    if Path(STATE_FILE).exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"seen_urls": [], "downloaded_dois": [], "downloaded_urls": []}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# ── ブラウザでツイート取得 ────────────────────────────────
def scrape_tweets(username: str, headless: bool = True, scroll_count: int = SCROLL_COUNT) -> list[dict]:
    """Playwrightでブラウザを開き、ツイートのテキストとリンクを取得"""
    profile_url = f"https://x.com/{username}"
    tweets = []

    logger.info(f"ブラウザで {profile_url} を開いています...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="ja-JP",
        )
        page = context.new_page()

        try:
            page.goto(profile_url, wait_until="networkidle", timeout=30000)
        except PlaywrightTimeout:
            logger.warning("ページ読み込みがタイムアウトしましたが、続行します")

        # ログイン要求ポップアップを閉じる試み
        try:
            close_btn = page.locator('[data-testid="xMigrationBottomBar"] button, [role="button"][aria-label="Close"]')
            if close_btn.count() > 0:
                close_btn.first.click(timeout=3000)
                time.sleep(1)
        except Exception:
            pass

        # ページをスクロールしてツイートを読み込む
        logger.info(f"{scroll_count} 回スクロールしてツイートを読み込みます...")
        for i in range(scroll_count):
            page.mouse.wheel(0, 2000)
            time.sleep(2)

        # ツイート要素を取得
        tweet_articles = page.locator('article[data-testid="tweet"]')
        count = tweet_articles.count()
        logger.info(f"{count} 件のツイート要素を検出しました")

        for idx in range(count):
            try:
                article = tweet_articles.nth(idx)

                # ツイートテキスト取得
                text_el = article.locator('[data-testid="tweetText"]')
                text = text_el.inner_text() if text_el.count() > 0 else ""

                # ツイート内のリンクを取得
                links = []
                a_tags = article.locator("a[href]")
                for li in range(a_tags.count()):
                    href = a_tags.nth(li).get_attribute("href")
                    if href:
                        # t.co リンクの場合、title属性やテキストから元URLを取得
                        if "t.co/" in href:
                            title = a_tags.nth(li).get_attribute("title") or ""
                            link_text = a_tags.nth(li).inner_text()
                            # title属性に元URLが入っていることがある
                            if title.startswith("http"):
                                links.append(title)
                            elif link_text.startswith("http"):
                                links.append(link_text)
                            else:
                                links.append(href)
                        elif href.startswith("http"):
                            links.append(href)

                # タイムスタンプ取得
                time_el = article.locator("time")
                timestamp = ""
                if time_el.count() > 0:
                    timestamp = time_el.first.get_attribute("datetime") or ""

                tweets.append({
                    "text": text,
                    "links": links,
                    "timestamp": timestamp,
                })
            except Exception as e:
                logger.warning(f"ツイート {idx} の解析でエラー: {e}")
                continue

        # t.co リンクを実際のURLに解決
        tweets = resolve_tco_links(tweets, page)

        browser.close()

    logger.info(f"{len(tweets)} 件のツイートを取得しました")
    return tweets


def resolve_tco_links(tweets: list[dict], page) -> list[dict]:
    """t.co短縮URLを実際のURLに解決する"""
    tco_links = set()
    for tweet in tweets:
        for link in tweet["links"]:
            if "t.co/" in link:
                tco_links.add(link)

    if not tco_links:
        return tweets

    logger.info(f"{len(tco_links)} 件のt.coリンクを解決中...")
    resolved = {}

    for tco in tco_links:
        try:
            resp = requests.head(
                tco,
                allow_redirects=True,
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp.url != tco:
                resolved[tco] = resp.url
                logger.debug(f"  {tco} -> {resp.url}")
        except requests.RequestException:
            pass

    # 解決したURLで置換
    for tweet in tweets:
        tweet["links"] = [resolved.get(link, link) for link in tweet["links"]]

    logger.info(f"{len(resolved)} 件のリンクを解決しました")
    return tweets


# ── URL / DOI 抽出 ────────────────────────────────────────
def extract_dois(urls: list[str], text: str = "") -> list[str]:
    dois = set()
    for url in urls:
        if "doi.org/" in url:
            parts = url.split("doi.org/", 1)
            if len(parts) == 2:
                doi = unquote(parts[1]).strip().rstrip(".,;:!?)")
                dois.add(doi)
    for match in DOI_PATTERN.findall(text):
        doi = match.rstrip(".,;:!?)")
        dois.add(doi)
    return list(dois)


def is_paper_url(url: str) -> bool:
    parsed = urlparse(url)
    domain = parsed.netloc.lower().lstrip("www.")
    return any(d in domain for d in PAPER_DOMAINS)


def filter_paper_urls(urls: list[str]) -> list[str]:
    return [u for u in urls if is_paper_url(u)]


# ── DOI -> PDF 解決 ───────────────────────────────────────
def resolve_doi_to_pdf(doi: str) -> Optional[str]:
    if not UNPAYWALL_EMAIL:
        logger.warning("UNPAYWALL_EMAIL 未設定のため、Unpaywall APIをスキップします")
        return None
    url = f"https://api.unpaywall.org/v2/{doi}"
    params = {"email": UNPAYWALL_EMAIL}
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            best = data.get("best_oa_location")
            if best:
                pdf_url = best.get("url_for_pdf") or best.get("url")
                if pdf_url:
                    logger.info(f"Unpaywall: {doi} -> {pdf_url}")
                    return pdf_url
            for loc in data.get("oa_locations", []):
                pdf_url = loc.get("url_for_pdf") or loc.get("url")
                if pdf_url:
                    logger.info(f"Unpaywall (alt): {doi} -> {pdf_url}")
                    return pdf_url
    except requests.RequestException as e:
        logger.warning(f"Unpaywall APIエラー ({doi}): {e}")
    return None


def try_direct_pdf_from_url(url: str) -> Optional[str]:
    if "arxiv.org/abs/" in url:
        return url.replace("/abs/", "/pdf/") + ".pdf"
    if "arxiv.org/pdf/" in url:
        return url if url.endswith(".pdf") else url + ".pdf"
    if ("biorxiv.org" in url or "medrxiv.org" in url) and "/content/" in url:
        if not url.endswith(".full.pdf"):
            base = url.split("?")[0].rstrip("/")
            return base + ".full.pdf"
    if "ncbi.nlm.nih.gov/pmc/articles/" in url:
        pmc_match = re.search(r"PMC\d+", url)
        if pmc_match:
            pmc_id = pmc_match.group()
            return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/"
    if url.lower().endswith(".pdf"):
        return url
    return None


# ── PDF ダウンロード ──────────────────────────────────────
def download_pdf(pdf_url: str, filename: str) -> bool:
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
        first_chunk = b""
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if not first_chunk:
                    first_chunk = chunk
                f.write(chunk)
        if not first_chunk.startswith(b"%PDF") and "pdf" not in content_type.lower():
            logger.warning(f"PDFではない可能性: {filename} (Content-Type: {content_type})")
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
    text = tweet.get("text", "")
    links = tweet.get("links", [])
    timestamp = tweet.get("timestamp", "")
    downloaded = []

    logger.info(f"--- ツイート処理 ({timestamp}) ---")
    logger.info(f"テキスト: {text[:120]}...")

    # テキスト内のURLも追加
    for match in URL_PATTERN.findall(text):
        clean = match.rstrip(".,;:!?)")
        if clean not in links:
            links.append(clean)

    dois = extract_dois(links, text)
    paper_urls = filter_paper_urls(links)

    if not dois and not paper_urls:
        logger.info("論文関連のURLが見つかりませんでした")
        return downloaded

    logger.info(f"  DOI: {dois}, 論文URL: {len(paper_urls)}件")

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


def run_once(headless: bool = True):
    """1回の実行: ブラウザでツイートを取得して論文をダウンロード"""
    state = load_state()

    tweets = scrape_tweets(TARGET_USERNAME, headless=headless)
    if not tweets:
        logger.info("ツイートが取得できませんでした")
        return

    total_downloaded = []
    for tweet in tweets:
        downloaded = process_tweet(tweet, state)
        total_downloaded.extend(downloaded)

    save_state(state)

    logger.info(f"=== 完了: {len(total_downloaded)} 件のPDFをダウンロードしました ===")
    for f in total_downloaded:
        logger.info(f"  - {f}")


def watch_mode(headless: bool = True):
    """定期監視モード"""
    logger.info(
        f"定期監視モード開始: @{TARGET_USERNAME} を {CHECK_INTERVAL_MINUTES}分間隔で監視します"
    )
    logger.info(f"ダウンロード先: {Path(DOWNLOAD_DIR).resolve()}")
    logger.info("停止するには Ctrl+C を押してください")

    while True:
        try:
            run_once(headless=headless)
        except Exception as e:
            logger.error(f"実行エラー: {e}", exc_info=True)
        logger.info(f"次の確認まで {CHECK_INTERVAL_MINUTES} 分待機中...")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)


# ── エントリーポイント ────────────────────────────────────
def main():
    global CHECK_INTERVAL_MINUTES, SCROLL_COUNT

    parser = argparse.ArgumentParser(
        description="X(Twitter)アカウントから論文PDFを自動ダウンロード（ブラウザ版・API不要）"
    )
    parser.add_argument(
        "--watch", action="store_true", help="定期監視モード"
    )
    parser.add_argument(
        "--head", action="store_true",
        help="ブラウザを表示して実行（デフォルト: ヘッドレス）",
    )
    parser.add_argument(
        "--interval", type=int, default=None,
        help=f"監視間隔（分）（デフォルト: {CHECK_INTERVAL_MINUTES}）",
    )
    parser.add_argument(
        "--scroll", type=int, default=None,
        help=f"スクロール回数（デフォルト: {SCROLL_COUNT}）",
    )
    args = parser.parse_args()

    if args.interval:
        CHECK_INTERVAL_MINUTES = args.interval
    if args.scroll:
        SCROLL_COUNT = args.scroll

    headless = not args.head

    if args.watch:
        watch_mode(headless=headless)
    else:
        run_once(headless=headless)


if __name__ == "__main__":
    main()
