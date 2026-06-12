# くるくる (kuru-kuru)

運用まわりの「毎日のだるい作業」を3つまとめて軽くするツールです。

1. **競合巡回レポート** — 競合アカウントを毎朝巡回し、前回より伸びた投稿だけをレポートにまとめます。
2. **数値ダッシュボード** — 売上（Stripe）とフォロワー（Instagram / X）を1画面に集約します。
3. **文字起こし → 記事下書き** — 動画・音声を文字起こしし、Claude が記事の下書きに変換します。

> ルート直下の `README.md` は GitHub プロフィール用の特別ファイルのため触れていません。アプリの説明はこのファイルにまとめています。

---

## 技術スタック

- **Next.js 14（App Router）+ TypeScript + Tailwind CSS**
- 記事生成: **Anthropic Claude（`claude-opus-4-8`）** — アダプティブ思考 + 構造化出力 + ストリーミング
- 文字起こし: **OpenAI Whisper**
- データ取得: Instagram Graph API / X API v2 / Stripe API
- 永続化: `.data/` 以下のファイル（前日比スナップショット・推移履歴）。本番では DB に差し替え前提の薄い実装。

**APIキーが無い項目はすべて自動でサンプルデータにフォールバック**するので、何も設定しなくても全画面が動きます。キーを入れた項目から順に実データへ切り替わります。

---

## セットアップ

```bash
npm install
cp .env.example .env.local   # 使う機能のキーだけ埋める（空でもOK）
npm run dev                  # http://localhost:3000
```

### よく使うコマンド

| コマンド | 内容 |
| --- | --- |
| `npm run dev` | 開発サーバー起動 |
| `npm run build` / `npm run start` | 本番ビルド / 起動 |
| `npm run typecheck` | 型チェック |
| `npm run morning-report` | 競合巡回をCLIで実行（cron向け） |

---

## 機能ごとの設定

### 1. 競合巡回レポート（`/competitors`）

- 「いま巡回する」で実行すると、現在のスナップショットを取得し、**前回保存した値との差分**から伸び率を計算します。
- `GROWTH_THRESHOLD_PERCENT`（既定20）以上 伸びた投稿だけを表示します。
- 初回は基準取得のみ。2回目以降に伸びが出ます。
- 実データに必要な環境変数:
  - Instagram: `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ACCOUNT_ID`, `COMPETITOR_INSTAGRAM_USERNAMES`
  - X: `X_BEARER_TOKEN`, `COMPETITOR_X_USERNAMES`

**毎朝の自動化:** cron で `npm run morning-report` を実行。スクリプト末尾に Slack / メール送信を足せます。

```cron
0 7 * * * cd /path/to/app && npm run morning-report >> patrol.log 2>&1
```

### 2. ダッシュボード（`/`）

- 売上: `STRIPE_SECRET_KEY`（直近30日の成功Chargeを集計）
- フォロワー: Instagram / X のトークン（合算）。日次でフォロワー総数を `.data/` に記録し、推移グラフにします。

### 3. 文字起こし → 記事下書き（`/transcribe`）

- 文字起こし: `OPENAI_API_KEY`（`TRANSCRIBE_MODEL` で `whisper-1` / `gpt-4o-transcribe` を選択）
- 記事生成: `ANTHROPIC_API_KEY`
- 音声・動画どちらもOK。生成結果は Markdown でコピーできます。

---

## ディレクトリ構成

```
src/
  app/
    page.tsx                  ダッシュボード
    competitors/page.tsx      競合巡回
    transcribe/page.tsx       文字起こし→記事
    api/                      各機能のAPIルート
  lib/
    competitors.ts            巡回ロジック（取得→前日比→抽出）
    dashboard.ts              数値集計
    instagram.ts / x.ts       SNS取得（実API or 空配列）
    stripe.ts                 売上集計
    transcription.ts          Whisper 連携
    anthropic.ts              Claude 記事生成
    store.ts                  ファイルベース永続化
    mock.ts                   サンプルデータ
  components/                 Nav / Sparkline / Markdown
scripts/morning-report.ts     朝の巡回（cron向け）
```

---

## 注意

- `.data/` と `.env.local` は `.gitignore` 済み（コミットされません）。
- 実APIの利用規約・レート制限・スクレイピング可否は各プラットフォームの規約に従ってください。本ツールは公式APIの利用を前提にしています。
