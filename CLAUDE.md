# CLAUDE.md

<!--
Fable 5 向けに最適化した CLAUDE.md の書き方（このファイル自体が見本です）:
- 手順（〜してから〜せよ）は書かない。目標・理由・境界・検証方法だけを書く
- 「テストを忘れずに」等の検証リマインダーは書かない（Fable は自律的に検証する）
- 短く保つ。迷ったら削る
-->

## このリポジトリについて

GitHub プロフィール用リポジトリ。`README.md` がプロフィールページに表示される。

## 目標

- プロフィールは簡潔で正確に保つ（誇張しない）
- 関心領域: AI × 医療、特に女性の健康改善

## 境界（やらないこと）

- README の自己紹介の内容（関心・連絡先など）を勝手に変えない。文法・体裁の修正は提案ベースで
- 連絡先やSNSアカウントの追加・変更は必ず確認を取る

## X (Twitter) の検索・閲覧について

X (x.com / twitter.com) を検索・閲覧するときは、直接アクセスせず必ず Jina を使うこと。
x.com は直接フェッチするとログイン壁やブロックで内容が取得できないため。

- **検索**: `https://s.jina.ai/?q=<URLエンコードした検索クエリ>` を WebFetch する
  - X 内に限定したい場合はクエリに ` site:x.com` を付ける(例: `https://s.jina.ai/?q=claude%20code%20site%3Ax.com`)
- **個別ページの閲覧**: 元の URL の前に `https://r.jina.ai/` を付けて WebFetch する
  (例: `https://r.jina.ai/https://x.com/user/status/123`)
  - `.claude/settings.json` の PreToolUse フックにより、x.com / twitter.com への WebFetch は自動でこの形式に書き換えられる
- 環境変数 `JINA_API_KEY` が設定されている場合は、レート制限緩和のため Bash + curl で
  `Authorization: Bearer $JINA_API_KEY` ヘッダーを付けて呼んでもよい

## 検証

- README は GitHub プロフィールに表示されるため、Markdown のレンダリング崩れがないこと

## 学習メモ

セッションをまたいで残すべき教訓は `.claude/memory/` に記録する。書式は `.claude/memory/README.md` を参照。
