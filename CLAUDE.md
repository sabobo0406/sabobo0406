# CLAUDE.md

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
