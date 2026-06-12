# SNS運用ツールキット

SNS運用・コンテンツ制作を自動化する3つのツールです。すべて Python 製で、それぞれ独立して使えます。

| ツール | 役割 |
|---|---|
| [`competitor_report/`](./competitor_report/) | 競合アカウントを毎朝巡回して、伸びた投稿だけをレポートにまとめる |
| [`dashboard/`](./dashboard/) | 売上やフォロワーの数字を一画面に集める HTML ダッシュボードを生成する |
| [`transcribe_draft/`](./transcribe_draft/) | 動画・音声を文字起こしして、記事の下書きまで変換する |

## セットアップ

Python 3.10 以上が必要です。

```bash
cd tools
pip install -r requirements.txt
```

各ツールの使い方は、それぞれのフォルダ内の README.md を参照してください。

## 必要な API キー・環境変数

| 環境変数 | 使うツール | 取得方法 |
|---|---|---|
| `YOUTUBE_API_KEY` | competitor_report(YouTube 巡回時) | [Google Cloud Console](https://console.cloud.google.com/) で YouTube Data API v3 を有効化して API キーを発行 |
| `ANTHROPIC_API_KEY` | transcribe_draft(記事下書き生成) | [Claude Console](https://platform.claude.com/) で発行 |

```bash
export YOUTUBE_API_KEY="xxxx"
export ANTHROPIC_API_KEY="sk-ant-xxxx"
```

## 毎朝の自動実行(competitor_report)

`.github/workflows/morning-report.yml` に GitHub Actions のワークフローを用意しています。
リポジトリの Settings → Secrets and variables → Actions に `YOUTUBE_API_KEY` を登録すると、
毎朝 7:00(日本時間)に競合巡回が走り、レポートがリポジトリにコミットされます。
