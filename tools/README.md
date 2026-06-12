# SNS運用ツールキット

SNS運用・コンテンツ制作を自動化する3つのツールです。すべて Python 製で、それぞれ独立して使えます。

| ツール | 役割 |
|---|---|
| [`competitor_report/`](./competitor_report/) | 競合アカウント(X / Instagram / note / Voicy)を毎朝巡回して、伸びた投稿だけをレポートにまとめる |
| [`dashboard/`](./dashboard/) | 売上や各SNSのフォロワー数を一画面に集める HTML ダッシュボードを生成する |
| [`transcribe_draft/`](./transcribe_draft/) | 動画・音声を文字起こしして、記事の下書きまで変換する(Claude サブスクで動作・API課金なし) |

## セットアップ

Python 3.10 以上が必要です。

```bash
cd tools
pip install -r requirements.txt
```

各ツールの使い方は、それぞれのフォルダ内の README.md を参照してください。

## 必要なキー・アカウント

| 設定 | 使うツール | 備考 |
|---|---|---|
| なし | competitor_report(note 巡回)/ dashboard | note は公開APIのためキー不要 |
| `X_BEARER_TOKEN` | competitor_report(X 巡回) | [X Developer Portal](https://developer.x.com/) で発行 |
| `IG_ACCESS_TOKEN` / `IG_USER_ID` | competitor_report(Instagram 巡回) | 自分の Instagram プロアカウント + [Meta アプリ](https://developers.facebook.com/) が必要 |
| Claude Code(Pro/Max サブスク) | transcribe_draft(記事下書き) | `npm install -g @anthropic-ai/claude-code` してログイン。API キー不要 |

Voicy は公開APIがないため、competitor_report では CSV 手入力で対応します。

## 毎朝の自動実行(competitor_report)

`.github/workflows/morning-report.yml` に GitHub Actions のワークフローを用意しています。
リポジトリの Settings → Secrets and variables → Actions に、使う API のトークン
(`X_BEARER_TOKEN` / `IG_ACCESS_TOKEN` / `IG_USER_ID`)を登録すると、
毎朝 7:00(日本時間)に競合巡回が走り、レポートがリポジトリにコミットされます。
note だけ巡回する場合は Secrets の登録は不要です。
