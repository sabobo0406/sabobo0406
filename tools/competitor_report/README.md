# competitor_report — 競合アカウント巡回レポート

競合アカウント(X / Instagram / note / Voicy)の投稿データを毎朝取得して、**前日より大きく伸びた投稿だけ**を Markdown レポートにまとめるツールです。

## 仕組み

1. 毎朝、各アカウントの最新投稿の数値を取得して `data/snapshots/日付.json` に保存
2. 前回のスナップショットと比較して、1日あたりの伸びを計算
3. 「アカウント内の中央値の◯倍以上伸びた投稿」だけを `reports/日付.md` に出力

つまり**2回目の実行から**レポートに伸びが表示されます(初回は比較対象がないため、基準データの保存のみ)。

## 対応プラットフォーム

| platform | 主要指標 | 必要な設定 |
|---|---|---|
| `note` | スキ数 | **不要**(公開APIを使用。`urlname` = note.com/◯◯◯ の◯◯◯部分) |
| `x` | インプレッション数 | `X_BEARER_TOKEN`([X Developer Portal](https://developer.x.com/) で発行。無料プランは読み取り回数が非常に少ないため日次巡回には Basic 以上を推奨) |
| `instagram` | いいね数 | `IG_ACCESS_TOKEN` と `IG_USER_ID`(自分の Instagram プロアカウント + [Meta アプリ](https://developers.facebook.com/) が必要。Business Discovery API を使用し、競合もプロアカウントである必要あり) |
| `csv` | views 列 | CSV を手入力・手動エクスポート(**Voicy** は公開APIがないためこちらを使用) |

非公式スクレイピングは各サービスの規約違反になるため、公式 API か手入力のみ対応しています。
API の設定が難しい場合は、どのプラットフォームも `csv` で手入力すれば使えます。

## 使い方

1. `config.json` を編集して巡回したいアカウントを登録

```json
{
  "accounts": [
    {"platform": "note", "name": "競合A (note)", "urlname": "xxxx"},
    {"platform": "x", "name": "競合B (X)", "username": "xxxx"},
    {"platform": "instagram", "name": "競合C (Instagram)", "username": "xxxx"},
    {"platform": "csv", "name": "競合D (Voicy)", "csv_path": "data/manual/sample_voicy.csv"}
  ],
  "growth_threshold": 2.0,
  "min_growth": 100,
  "max_posts_per_account": 30
}
```

- `growth_threshold`: 中央値の何倍伸びたら「伸びた投稿」とみなすか
- `min_growth`: 最低でもこれだけ数値が増えていないと対象外(ノイズ除去。スキ数中心なら 10〜20 程度に下げるのがおすすめ)
- 使わないプラットフォームの行は削除して OK。一部のアカウントの取得に失敗しても、残りの巡回は続行されます

2. 実行

```bash
export X_BEARER_TOKEN="xxxx"        # X を巡回する場合のみ
export IG_ACCESS_TOKEN="xxxx"       # Instagram を巡回する場合のみ
export IG_USER_ID="1784xxxxxxxx"    # 同上
python main.py
```

3. `reports/日付.md` を開く

## CSV の形式(Voicy・手入力用)

```csv
post_id,title,url,published_at,views,likes,comments
v001,#120 朝のマインドセットの話,https://voicy.jp/channel/0000/sample1,2026-06-08,85,85,4
```

`views` 列が伸び判定に使う主要指標です。Voicy ならいいね数(♡)など、伸びを追いたい数値を入れてください。

## 毎朝の自動実行

リポジトリの GitHub Actions(`.github/workflows/morning-report.yml`)が毎朝 7:00 JST に実行し、
スナップショットとレポートを自動コミットします。使う API に応じて Secrets に
`X_BEARER_TOKEN` / `IG_ACCESS_TOKEN` / `IG_USER_ID` を登録してください(note のみなら登録不要)。
