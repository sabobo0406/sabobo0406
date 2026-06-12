"""動画・音声を文字起こしして、記事の下書きまで変換する。

文字起こしはローカルの Whisper(無料)、記事下書きは Claude Code CLI 経由で
生成する(Claude Pro/Max のサブスクで動くため API の従量課金は不要)。

使い方:
    python main.py 動画.mp4
    python main.py 音声.m4a --style note --model-size medium
"""

import argparse
import os
import shutil
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

STYLE_PROMPTS = {
    "blog": "読みやすいブログ記事。親しみやすい語り口で、見出しを使って構成する。",
    "note": "note 向けのエッセイ調の記事。一人称の語りを活かし、体験や気づきを中心に書く。",
    "seo": "SEO を意識した解説記事。検索意図に答える構成で、要点を箇条書きも使って整理する。",
}

DRAFT_PROMPT = """あなたは日本語のコンテンツ編集者です。
次の話し言葉の文字起こしを、公開できる品質の記事下書きに書き直してください。

ルール:
- 話の内容・主張・具体例は変えず、話し言葉特有の冗長さ(えー、あの、繰り返し等)だけを除く
- 文字起こしに無い情報を創作しない
- 記事スタイル: {style}
- 出力は Markdown のみ(前置きや解説は不要)で、次の構成にする:
  1. タイトル案を3つ
  2. リード文(2〜3文)
  3. 見出し付きの本文
  4. まとめ

<文字起こし>
{transcript}
</文字起こし>
"""


def transcribe(path: str, model_size: str, lang: str) -> str:
    from faster_whisper import WhisperModel

    print(f"文字起こし中... (モデル: {model_size})", file=sys.stderr)
    model = WhisperModel(model_size, compute_type="int8")
    segments, _info = model.transcribe(path, language=lang)
    return "".join(seg.text for seg in segments).strip()


def generate_draft(transcript: str, style: str) -> str | None:
    """Claude Code CLI(サブスク)で記事下書きを生成する。

    CLI が無い場合は None を返す(main 側でプロンプトをファイル保存する)。
    """
    if not shutil.which("claude"):
        return None

    prompt = DRAFT_PROMPT.format(style=STYLE_PROMPTS[style], transcript=transcript)
    print("記事下書きを生成中... (claude CLI)", file=sys.stderr)
    result = subprocess.run(
        ["claude", "-p"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=1200,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"claude CLI がエラーを返しました:\n{result.stderr.strip()}\n"
            "`claude` を一度起動してログイン済みか確認してください。"
        )
    return result.stdout.strip()


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
    if draft is None:
        # claude CLI が無い環境では、claude.ai に貼り付けられるプロンプトを保存する
        prompt_path = os.path.join(OUTPUT_DIR, f"{stem}_prompt.txt")
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(DRAFT_PROMPT.format(style=STYLE_PROMPTS[args.style], transcript=transcript))
        print(
            "claude コマンドが見つからないため、プロンプトを保存しました。\n"
            f"  {prompt_path}\n"
            "この内容を claude.ai に貼り付けると下書きが作れます。\n"
            "(Claude Code のインストール: npm install -g @anthropic-ai/claude-code)",
            file=sys.stderr,
        )
        return 0

    draft_path = os.path.join(OUTPUT_DIR, f"{stem}_draft.md")
    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(draft + "\n")
    print(f"記事下書きを保存しました: {draft_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
