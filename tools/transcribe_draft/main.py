"""動画・音声を文字起こしして、記事の下書きまで変換する。

使い方:
    python main.py 動画.mp4
    python main.py 音声.m4a --style note --model-size medium
"""

import argparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

STYLE_PROMPTS = {
    "blog": "読みやすいブログ記事。親しみやすい語り口で、見出しを使って構成する。",
    "note": "note 向けのエッセイ調の記事。一人称の語りを活かし、体験や気づきを中心に書く。",
    "seo": "SEO を意識した解説記事。検索意図に答える構成で、要点を箇条書きも使って整理する。",
}

DRAFT_SYSTEM = """あなたは日本語のコンテンツ編集者です。
話し言葉の文字起こしを、公開できる品質の記事下書きに書き直します。

ルール:
- 話の内容・主張・具体例は変えず、話し言葉特有の冗長さ(えー、あの、繰り返し等)だけを除く
- 文字起こしに無い情報を創作しない
- 出力は Markdown で、次の構成にする:
  1. タイトル案を3つ
  2. リード文(2〜3文)
  3. 見出し付きの本文
  4. まとめ
"""


def transcribe(path: str, model_size: str, lang: str) -> str:
    from faster_whisper import WhisperModel

    print(f"文字起こし中... (モデル: {model_size})", file=sys.stderr)
    model = WhisperModel(model_size, compute_type="int8")
    segments, _info = model.transcribe(path, language=lang)
    return "".join(seg.text for seg in segments).strip()


def generate_draft(transcript: str, style: str) -> str:
    import anthropic

    client = anthropic.Anthropic()
    print("記事下書きを生成中...", file=sys.stderr)
    with client.messages.stream(
        model="claude-opus-4-8",
        max_tokens=64000,
        thinking={"type": "adaptive"},
        system=DRAFT_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"次の文字起こしを記事の下書きにしてください。\n"
                    f"スタイル: {STYLE_PROMPTS[style]}\n\n"
                    f"<文字起こし>\n{transcript}\n</文字起こし>"
                ),
            }
        ],
    ) as stream:
        response = stream.get_final_message()

    return next(b.text for b in response.content if b.type == "text")


def main() -> int:
    parser = argparse.ArgumentParser(description="動画・音声 → 文字起こし → 記事下書き")
    parser.add_argument("input", help="動画・音声ファイルのパス")
    parser.add_argument("--style", choices=sorted(STYLE_PROMPTS), default="blog")
    parser.add_argument(
        "--model-size",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        default="small",
    )
    parser.add_argument("--lang", default="ja")
    parser.add_argument("--no-draft", action="store_true", help="文字起こしのみ行う")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"ファイルが見つかりません: {args.input}", file=sys.stderr)
        return 1
    if not args.no_draft and not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "環境変数 ANTHROPIC_API_KEY が未設定です。"
            "文字起こしのみ行う場合は --no-draft を付けてください。",
            file=sys.stderr,
        )
        return 1

    stem = os.path.splitext(os.path.basename(args.input))[0]
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    transcript = transcribe(args.input, args.model_size, args.lang)
    transcript_path = os.path.join(OUTPUT_DIR, f"{stem}_transcript.txt")
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript + "\n")
    print(f"文字起こしを保存しました: {transcript_path}")

    if args.no_draft:
        return 0

    draft = generate_draft(transcript, args.style)
    draft_path = os.path.join(OUTPUT_DIR, f"{stem}_draft.md")
    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(draft + "\n")
    print(f"記事下書きを保存しました: {draft_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
