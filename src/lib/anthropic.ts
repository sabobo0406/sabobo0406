// 記事下書き生成（Claude / Anthropic）。
// 文字起こしテキストから、構成された記事のドラフト（タイトル + 本文Markdown）を作る。
// ANTHROPIC_API_KEY が無ければモックのドラフトを返す。

import Anthropic from "@anthropic-ai/sdk";
import type { ArticleDraft } from "./types";

export function hasAnthropic(): boolean {
  return Boolean(process.env.ANTHROPIC_API_KEY);
}

const SYSTEM_PROMPT = `あなたは、話し言葉の文字起こしを読みやすいブログ記事の下書きに変換する日本語の編集者です。

やること:
- 文字起こしの内容に忠実に、事実を足したり捏造したりしない。
- 話し言葉のフィラー（えーと、あの、など）や言い直しを整理し、読みやすい書き言葉にする。
- 内容に合った見出し（##）で2〜5個のセクションに構造化する。
- 導入の一段落で読者の興味を引き、最後に簡単なまとめを置く。
- 本文は Markdown。誇張した煽り表現は避け、落ち着いたトーンで。`;

const OUTPUT_SCHEMA = {
  type: "object",
  properties: {
    title: { type: "string", description: "記事のタイトル（30文字以内目安）" },
    body: { type: "string", description: "記事本文（Markdown、見出し ## を含む）" },
  },
  required: ["title", "body"],
  additionalProperties: false,
} as const;

export async function draftArticle(transcript: string): Promise<ArticleDraft> {
  if (!hasAnthropic()) {
    return mockDraft(transcript);
  }

  const client = new Anthropic();

  // 長文出力に備えてストリーミングし、最終メッセージを取得する。
  const stream = client.messages.stream({
    model: "claude-opus-4-8",
    max_tokens: 8000,
    thinking: { type: "adaptive" },
    output_config: { effort: "high", format: { type: "json_schema", schema: OUTPUT_SCHEMA } },
    system: SYSTEM_PROMPT,
    messages: [
      {
        role: "user",
        content:
          `次の文字起こしを記事の下書きにしてください。\n\n--- 文字起こしここから ---\n${transcript}\n--- 文字起こしここまで ---`,
      },
    ],
  });

  const message = await stream.finalMessage();
  const textBlock = message.content.find((b) => b.type === "text");
  const raw = textBlock && "text" in textBlock ? textBlock.text : "";

  try {
    const parsed = JSON.parse(raw) as { title: string; body: string };
    return { title: parsed.title, body: parsed.body, source: "real" };
  } catch {
    // 構造化出力が崩れた場合は本文としてそのまま返す
    return { title: "記事の下書き", body: raw || "(生成結果が空でした)", source: "real" };
  }
}

function mockDraft(transcript: string): ArticleDraft {
  const firstLine = transcript.split(/\n|。/)[0]?.trim().slice(0, 28) || "記事の下書き";
  const body = `## はじめに

これはサンプルの記事下書きです（ANTHROPIC_API_KEY 未設定のためモック）。
実際のキーを設定すると、以下の文字起こしから Claude が構造化された記事を生成します。

## 文字起こしの要約

${transcript.slice(0, 400)}${transcript.length > 400 ? "…" : ""}

## まとめ

\`.env.local\` に \`ANTHROPIC_API_KEY\` を設定すると、本物の下書き生成に切り替わります。`;
  return { title: firstLine, body, source: "mock" };
}
