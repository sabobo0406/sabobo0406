# competitor_report — 競合アカウント巡回レポート

競合アカウントの投稿データを毎朝取得して、**前日より大きく伸びた投稿だけ**を Markdown レポートにまとめるツールです。

## 仕組み

1. 毎朝、各アカウントの最新投稿の数値(再生数・いいね・コメント)を取得して `data/snapshots/日付.json` に保存
2. 前回のスナップショットと比較して、1日あたりの伸びを計算
3. 「アカウント内の中央値の◯倍以上伸びた投稿」だけを `reports/日付.md` に出力

つまり**2回目の実行から**レポートに伸びが表示されます(初回は比較対象がないため、基準データの保存のみ)。

## 対応データソース

| platform | 説明 |
|---|---|
| `youtube` | YouTube Data API v3 で自動取得(`YOUTUBE_API_KEY` が必要) |
| `csv` | 手動エクスポートした CSV を読み込み(Instagram インサイト等。非公式スクレイピングは規約違反になるため、公式エクスポートか手入力を使ってください) |

## 使い方

1. `config.json` を編集して巡回したいアカウントを登録

```json
{
  "accounts": [
    {"platform": "youtube", "name": "競合チャンネルA", "channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx"},
    {"platform": "csv", "name": "競合B (Instagram)", "csv_path": "data/manual/sample_instagram.csv"}
  ],
  "growth_threshold": 2.0,
  "min_growth": 100,
  "max_posts_per_account": 30
}
```

- `growth_threshold`: 中央値の何倍伸びたら「伸びた投稿」とみなすか
- `min_growth`: 最低でもこれだけ数値が増えていないと対象外(ノイズ除去)
- YouTube のチャンネル ID は、チャンネルページの URL(`youtube.com/channel/UC...`)か、概要欄の「チャンネルを共有」→「チャンネル ID をコピー」で確認できます

2. 実行

```bash
export YOUTUBE_API_KEY="xxxx"
python main.py
```

3. `reports/日付.md` を開く

## CSV の形式

```csv
post_id,title,url,published_at,views,likes,comments
p001,リール: 朝のルーティン,https://instagram.com/p/xxx,2026-06-10,1500,120,8
```

`views` の代わりに再生数・リーチなど、伸びを追いたい数値を入れてください。

## 毎朝の自動実行

リポジトリの GitHub Actions(`.github/workflows/morning-report.yml`)が毎朝 7:00 JST に実行し、
スナップショットとレポートを自動コミットします。Secrets に `YOUTUBE_API_KEY` の登録が必要です。
