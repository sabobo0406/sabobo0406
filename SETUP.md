# Twitter Paper Downloader

X(Twitter)アカウント [@ajog_thegray](https://x.com/ajog_thegray) を定期的に監視し、
紹介されている論文のPDFを自動ダウンロードするツールです。

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 設定ファイルの作成

```bash
cp .env.example .env
```

`.env` ファイルを編集して、以下を設定してください:

| 設定項目 | 必須 | 説明 |
|---|---|---|
| `TWITTER_BEARER_TOKEN` | 必須 | Twitter API v2のBearerトークン |
| `UNPAYWALL_EMAIL` | 推奨 | Unpaywall APIでOA論文PDFを取得するためのメールアドレス |
| `TARGET_USERNAME` | 任意 | 監視するアカウント（デフォルト: `ajog_thegray`） |
| `DOWNLOAD_DIR` | 任意 | PDF保存先（デフォルト: `papers/`） |
| `CHECK_INTERVAL_MINUTES` | 任意 | 監視間隔・分（デフォルト: `60`） |

### 3. Twitter API Bearerトークンの取得

1. [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard) にアクセス
2. プロジェクトとアプリを作成
3. Bearer Token を生成
4. `.env` に記入

## 使い方

### 1回だけ実行

```bash
python twitter_paper_downloader.py
```

### 定期監視モード

```bash
python twitter_paper_downloader.py --watch
```

### 監視間隔を変更（例: 30分）

```bash
python twitter_paper_downloader.py --watch --interval 30
```

## 対応する論文ソース

以下のドメインからのリンクを論文として認識します:

- DOIリンク (`doi.org`)
- PubMed / PubMed Central
- arXiv / bioRxiv / medRxiv
- 主要ジャーナル（Nature, Lancet, NEJM, JAMA, BMJ, Wiley, Springer, AJOG 等）

## PDFの取得方法

1. **Unpaywall API** - オープンアクセスのPDFを検索（推奨: `UNPAYWALL_EMAIL`を設定）
2. **直接リンク** - arXiv, bioRxiv等はURLから直接PDFリンクを生成
3. **PubMed Central** - PMC論文のPDFを取得

## cron で定期実行する場合

```bash
# 毎時0分に実行
0 * * * * cd /path/to/sabobo0406 && /path/to/python twitter_paper_downloader.py >> cron.log 2>&1
```
