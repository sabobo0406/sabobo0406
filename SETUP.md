# Twitter Paper Downloader (ブラウザ版)

X(Twitter)アカウント [@ajog_thegray](https://x.com/ajog_thegray) をブラウザで開いて、
紹介されている論文のPDFを自動ダウンロードするツールです。

**API不要** - Playwrightでブラウザを自動操作してツイートを取得します。

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 設定（オプション）

```bash
cp .env.example .env
```

| 設定項目 | 必須 | 説明 |
|---|---|---|
| `TARGET_USERNAME` | - | 監視するアカウント（デフォルト: `ajog_thegray`） |
| `DOWNLOAD_DIR` | - | PDF保存先（デフォルト: `papers/`） |
| `CHECK_INTERVAL_MINUTES` | - | 監視間隔・分（デフォルト: `60`） |
| `SCROLL_COUNT` | - | スクロール回数（デフォルト: `5`） |
| `UNPAYWALL_EMAIL` | 推奨 | Unpaywall APIでOA論文PDFを取得するためのメール |

## 使い方

### 1回だけ実行

```bash
python twitter_paper_downloader.py
```

### ブラウザを表示して実行（動作確認に便利）

```bash
python twitter_paper_downloader.py --head
```

### 定期監視モード

```bash
python twitter_paper_downloader.py --watch
```

### オプション一覧

```
--watch          定期監視モード
--head           ブラウザを表示して実行（デフォルト: ヘッドレス）
--interval 30    監視間隔を30分に変更
--scroll 10      スクロール回数を増やして多くのツイートを取得
```

## 仕組み

1. Playwrightでブラウザを起動し、X.comのプロフィールページを開く
2. ページをスクロールしてツイートを読み込む
3. ツイート内のリンクを抽出（t.co短縮URLも自動解決）
4. 論文関連のURL（DOI, PubMed, arXiv, AJOG等）をフィルタ
5. Unpaywall API やダイレクトリンクでPDFを取得
6. `papers/` ディレクトリにPDFを保存

## 注意事項

- X.comのUIが変更された場合、スクレイピングが動作しなくなる可能性があります
- ログインなしではツイートの表示が制限される場合があります
- 過度なアクセスは避けてください（デフォルト60分間隔）
