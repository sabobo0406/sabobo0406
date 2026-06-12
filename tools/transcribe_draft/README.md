# transcribe_draft — 文字起こし → 記事下書き

動画・音声ファイルをローカルで文字起こしして、Claude で**そのまま使える記事の下書き**まで変換するツールです。

## 必要なもの

- `pip install -r ../requirements.txt`(anthropic / faster-whisper)
- [ffmpeg](https://ffmpeg.org/download.html)(動画・音声のデコードに必要)
- 環境変数 `ANTHROPIC_API_KEY`(記事下書きの生成に使用)

文字起こし自体はローカルで動くため無料です(初回実行時に Whisper モデルを自動ダウンロードします)。

## 使い方

```bash
export ANTHROPIC_API_KEY="sk-ant-xxxx"

# 基本(mp4 / mov / mp3 / wav / m4a など大抵の形式に対応)
python main.py 動画ファイル.mp4

# オプション
python main.py 音声.m4a --style blog --model-size small
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
- `<ファイル名>_draft.md` — 記事の下書き(タイトル案・見出し・本文・まとめ)
