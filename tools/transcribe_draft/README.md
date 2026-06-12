# transcribe_draft — 文字起こし → 記事下書き

動画・音声ファイルをローカルで文字起こしして、Claude で**そのまま使える記事の下書き**まで変換するツールです。

文字起こしはローカル Whisper(無料)、記事生成は **Claude Code CLI 経由**なので、
Claude Pro/Max のサブスクに含まれる形で動きます(API キー・従量課金は不要)。

## 必要なもの

- `pip install -r ../requirements.txt`(faster-whisper)
- [ffmpeg](https://ffmpeg.org/download.html)(動画・音声のデコードに必要)
- [Claude Code](https://code.claude.com/)(記事下書きの生成に使用)
  ```bash
  npm install -g @anthropic-ai/claude-code
  claude   # 初回起動時に Pro/Max アカウントでログイン
  ```

## 使い方

```bash
# 基本(mp4 / mov / mp3 / wav / m4a など大抵の形式に対応)
python main.py 動画ファイル.mp4

# オプション
python main.py 音声.m4a --style note --model-size medium
```

| オプション | 既定値 | 説明 |
|---|---|---|
| `--style` | `blog` | 下書きのスタイル: `blog`(ブログ記事)/ `note`(note向けエッセイ調)/ `seo`(SEO記事) |
| `--model-size` | `small` | Whisper のモデルサイズ: `tiny` / `base` / `small` / `medium` / `large-v3`(大きいほど高精度・低速) |
| `--lang` | `ja` | 音声の言語 |
| `--no-draft` | — | 文字起こしのみ行い、記事生成をスキップ |

## 出力

`output/` フォルダに2つのファイルができます:

- `<ファイル名>_transcript.txt` — 文字起こし全文
- `<ファイル名>_draft.md` — 記事の下書き(タイトル案・リード文・見出し付き本文・まとめ)

Claude Code が入っていない環境では、代わりに `<ファイル名>_prompt.txt` が保存されます。
この内容を claude.ai のチャットに貼り付ければ、同じ下書きが作れます。
