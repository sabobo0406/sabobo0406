#!/usr/bin/env python3
from __future__ import annotations
"""
Twitter Paper Checker (ブラウザ版)
==================================
X(Twitter)アカウントのツイートを取得し、
- ツイート内容の要約
- ツイート内リンクの生存確認
- 論文リンクかどうかの判定
を行うツール。

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
from datetime import datetime
from pathlib import Path
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
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "results")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "60"))
STATE_FILE = os.getenv("STATE_FILE", "downloader_state.json")
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
    "cell.com",
    "pnas.org",
    "nih.gov",
    "plos.org",
    "journals.plos.org",
    "frontiersin.org",
    "mdpi.com",
    "tandfonline.com",
    "sagepub.com",
    "cochranelibrary.com",
    "jstage.jst.go.jp",
    "researchgate.net",
    "ssrn.com",
]

DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s,;\"'<>\])}]+")
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")


# ── 状態管理 ──────────────────────────────────────────────
def load_state() -> dict:
    if Path(STATE_FILE).exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"seen_urls": [], "checked_tweets": []}


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

        # ログインウォール検出
        page_text = page.inner_text("body")
        if "ログイン" in page_text and "このアカウントは存在しません" not in page_text:
            # ログインポップアップを閉じる試み
            try:
                close_btn = page.locator(
                    '[data-testid="xMigrationBottomBar"] button, '
                    '[role="button"][aria-label="Close"], '
                    '[data-testid="app-bar-close"]'
                )
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

        if count == 0:
            logger.warning(
                "ツイートが検出できませんでした。"
                "X.comがログインを要求している可能性があります。"
                "--head オプションでブラウザを表示して確認してください。"
            )

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
                        if "t.co/" in href:
                            title = a_tags.nth(li).get_attribute("title") or ""
                            link_text = a_tags.nth(li).inner_text()
                            if title.startswith("http"):
                                links.append(title)
                            elif link_text.startswith("http"):
                                links.append(link_text)
                            else:
                                links.append(href)
                        elif href.startswith("http"):
                            links.append(href)

                # カード（プレビュー付きリンク）からURLを取得
                card = article.locator('[data-testid="card.wrapper"]')
                if card.count() > 0:
                    card_links = card.locator("a[href]")
                    for ci in range(card_links.count()):
                        card_href = card_links.nth(ci).get_attribute("href")
                        if card_href and card_href not in links:
                            if "t.co/" in card_href:
                                links.append(card_href)
                            elif card_href.startswith("http"):
                                links.append(card_href)
                    card_text = card.inner_text()
                    for match in URL_PATTERN.findall(card_text):
                        clean = match.rstrip(".,;:!?)")
                        if clean not in links:
                            links.append(clean)

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
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            if resp.url != tco:
                resolved[tco] = resp.url
                logger.debug(f"  {tco} -> {resp.url}")
                continue
        except requests.RequestException:
            pass
        try:
            resp = requests.get(
                tco,
                allow_redirects=True,
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                stream=True,
            )
            resp.close()
            if resp.url != tco:
                resolved[tco] = resp.url
                logger.debug(f"  {tco} -> {resp.url} (GET)")
        except requests.RequestException:
            logger.debug(f"  {tco} の解決に失敗")

    for tweet in tweets:
        tweet["links"] = [resolved.get(link, link) for link in tweet["links"]]

    logger.info(f"{len(resolved)} 件のリンクを解決しました")
    return tweets


# ── リンクチェック ────────────────────────────────────────
def check_link(url: str) -> dict:
    """URLの生存確認と論文リンク判定を行う"""
    result = {
        "url": url,
        "status": None,
        "alive": False,
        "is_paper": False,
        "paper_source": None,
        "doi": None,
        "final_url": url,
        "error": None,
    }

    # 論文リンク判定
    parsed = urlparse(url)
    domain = parsed.netloc.lower().lstrip("www.")
    for paper_domain in PAPER_DOMAINS:
        if paper_domain in domain:
            result["is_paper"] = True
            result["paper_source"] = paper_domain
            break

    # DOI抽出
    if "doi.org/" in url:
        parts = url.split("doi.org/", 1)
        if len(parts) == 2:
            result["doi"] = unquote(parts[1]).strip().rstrip(".,;:!?)")
    else:
        doi_matches = DOI_PATTERN.findall(url)
        if doi_matches:
            result["doi"] = doi_matches[0].rstrip(".,;:!?)")

    # テキスト内のDOIパターンでも論文判定
    if result["doi"]:
        result["is_paper"] = True

    # 生存確認
    try:
        resp = requests.head(
            url,
            allow_redirects=True,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,*/*",
            },
        )
        result["status"] = resp.status_code
        result["alive"] = resp.status_code < 400
        result["final_url"] = resp.url
    except requests.RequestException:
        # HEADが失敗した場合GETで再試行
        try:
            resp = requests.get(
                url,
                allow_redirects=True,
                timeout=15,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,*/*",
                },
                stream=True,
            )
            resp.close()
            result["status"] = resp.status_code
            result["alive"] = resp.status_code < 400
            result["final_url"] = resp.url
        except requests.RequestException as e:
            result["error"] = str(e)
            result["alive"] = False

    # リダイレクト先で再度論文判定
    if not result["is_paper"] and result["final_url"] != url:
        final_parsed = urlparse(result["final_url"])
        final_domain = final_parsed.netloc.lower().lstrip("www.")
        for paper_domain in PAPER_DOMAINS:
            if paper_domain in final_domain:
                result["is_paper"] = True
                result["paper_source"] = paper_domain
                break

    return result


def summarize_tweet(text: str) -> str:
    """ツイートテキストを要約する（最初の200文字 + リンクを除去した要約）"""
    # URLを除去
    clean_text = URL_PATTERN.sub("", text).strip()
    # 連続空白を整理
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    if not clean_text:
        return "(テキストなし - リンクのみのツイート)"

    # 200文字以内ならそのまま
    if len(clean_text) <= 200:
        return clean_text

    return clean_text[:200] + "..."


# ── メイン処理 ────────────────────────────────────────────
def process_tweet(tweet: dict, state: dict) -> dict:
    """ツイートを処理して要約とリンクチェック結果を返す"""
    text = tweet.get("text", "")
    links = tweet.get("links", [])
    timestamp = tweet.get("timestamp", "")

    logger.info(f"--- ツイート処理 ({timestamp}) ---")

    # テキスト内のURLも追加
    for match in URL_PATTERN.findall(text):
        clean = match.rstrip(".,;:!?)")
        if clean not in links:
            links.append(clean)

    # 内部リンク（x.comへのリンク等）を除外
    external_links = []
    for link in links:
        parsed = urlparse(link)
        domain = parsed.netloc.lower()
        if domain in ("x.com", "twitter.com", "t.co"):
            # t.coは解決済みのはずだが、解決失敗したものは除外
            if "t.co" in domain:
                continue
            # x.com/twitter.comの自分のツイートへのリンクは除外
            continue
        if link.startswith("http"):
            external_links.append(link)

    # 要約
    summary = summarize_tweet(text)

    # リンクチェック
    link_results = []
    for link in external_links:
        logger.info(f"  リンクチェック: {link}")
        result = check_link(link)
        status_str = "OK" if result["alive"] else f"NG({result['status'] or 'Error'})"
        paper_str = f" [論文: {result['paper_source']}]" if result["is_paper"] else ""
        doi_str = f" [DOI: {result['doi']}]" if result["doi"] else ""
        logger.info(f"    -> {status_str}{paper_str}{doi_str}")
        link_results.append(result)

    if not external_links:
        logger.info("  外部リンクなし")

    return {
        "timestamp": timestamp,
        "summary": summary,
        "original_text": text,
        "links": link_results,
        "has_paper_links": any(r["is_paper"] for r in link_results),
        "all_links_alive": all(r["alive"] for r in link_results) if link_results else True,
    }


def format_result(result: dict, index: int) -> str:
    """結果を見やすいテキストに整形"""
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"ツイート #{index + 1}  ({result['timestamp'] or '日時不明'})")
    lines.append(f"{'='*60}")
    lines.append(f"")
    lines.append(f"【要約】")
    lines.append(f"  {result['summary']}")
    lines.append(f"")

    if result["links"]:
        paper_count = sum(1 for r in result["links"] if r["is_paper"])
        alive_count = sum(1 for r in result["links"] if r["alive"])
        total = len(result["links"])
        lines.append(f"【リンク】 {total}件 (生存: {alive_count}/{total}, 論文: {paper_count}件)")
        lines.append(f"")

        for lr in result["links"]:
            status_icon = "○" if lr["alive"] else "×"
            paper_icon = "📄" if lr["is_paper"] else "  "

            lines.append(f"  {status_icon} {paper_icon} {lr['url']}")

            if lr["final_url"] != lr["url"]:
                lines.append(f"       -> {lr['final_url']}")

            details = []
            if lr["status"]:
                details.append(f"HTTP {lr['status']}")
            if lr["is_paper"] and lr["paper_source"]:
                details.append(f"論文サイト: {lr['paper_source']}")
            if lr["doi"]:
                details.append(f"DOI: {lr['doi']}")
            if lr["error"]:
                details.append(f"エラー: {lr['error']}")
            if details:
                lines.append(f"       ({', '.join(details)})")
            lines.append(f"")
    else:
        lines.append(f"【リンク】 なし")
        lines.append(f"")

    return "\n".join(lines)


def format_summary_report(results: list[dict]) -> str:
    """全体のサマリーレポートを生成"""
    lines = []
    total_tweets = len(results)
    paper_tweets = sum(1 for r in results if r["has_paper_links"])
    total_links = sum(len(r["links"]) for r in results)
    alive_links = sum(sum(1 for lr in r["links"] if lr["alive"]) for r in results)
    dead_links = total_links - alive_links
    paper_links = sum(sum(1 for lr in r["links"] if lr["is_paper"]) for r in results)

    lines.append(f"")
    lines.append(f"{'#'*60}")
    lines.append(f"  サマリーレポート")
    lines.append(f"{'#'*60}")
    lines.append(f"")
    lines.append(f"  対象アカウント: @{TARGET_USERNAME}")
    lines.append(f"  チェック日時:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"")
    lines.append(f"  ツイート数:     {total_tweets}")
    lines.append(f"  論文紹介ツイート: {paper_tweets}")
    lines.append(f"")
    lines.append(f"  リンク総数:     {total_links}")
    lines.append(f"    生存:         {alive_links}")
    lines.append(f"    デッド:       {dead_links}")
    lines.append(f"    論文リンク:   {paper_links}")
    lines.append(f"")

    # デッドリンク一覧
    if dead_links > 0:
        lines.append(f"  --- デッドリンク一覧 ---")
        for i, r in enumerate(results):
            for lr in r["links"]:
                if not lr["alive"]:
                    lines.append(f"  × {lr['url']}")
                    lines.append(f"    (ツイート #{i+1}, {r['timestamp'] or '日時不明'})")
        lines.append(f"")

    # 論文リンク一覧
    if paper_links > 0:
        lines.append(f"  --- 論文リンク一覧 ---")
        for i, r in enumerate(results):
            for lr in r["links"]:
                if lr["is_paper"]:
                    status = "○" if lr["alive"] else "×"
                    doi_str = f" (DOI: {lr['doi']})" if lr["doi"] else ""
                    lines.append(f"  {status} {lr['url']}{doi_str}")
                    lines.append(f"    (ツイート #{i+1}, {r['timestamp'] or '日時不明'})")
        lines.append(f"")

    lines.append(f"{'#'*60}")
    return "\n".join(lines)


def run_once(headless: bool = True):
    """1回の実行: ブラウザでツイートを取得して要約・リンクチェック"""
    state = load_state()

    tweets = scrape_tweets(TARGET_USERNAME, headless=headless)
    if not tweets:
        logger.info("ツイートが取得できませんでした")
        return

    results = []
    for tweet in tweets:
        result = process_tweet(tweet, state)
        results.append(result)

    save_state(state)

    # 結果をコンソール出力
    output_lines = []
    for i, result in enumerate(results):
        formatted = format_result(result, i)
        print(formatted)
        output_lines.append(formatted)

    # サマリー出力
    summary = format_summary_report(results)
    print(summary)
    output_lines.append(summary)

    # ファイル保存
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_path / f"tweet_check_{timestamp_str}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    logger.info(f"=== 結果を {output_file} に保存しました ===")


def watch_mode(headless: bool = True):
    """定期監視モード"""
    logger.info(
        f"定期監視モード開始: @{TARGET_USERNAME} を {CHECK_INTERVAL_MINUTES}分間隔で監視します"
    )
    logger.info(f"結果出力先: {Path(OUTPUT_DIR).resolve()}")
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
        description="X(Twitter)アカウントのツイート要約・リンクチェック（ブラウザ版・API不要）"
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
