// 音声・動画の文字起こし（OpenAI Whisper）。
// OPENAI_API_KEY が無ければモックのテキストを返す。

import OpenAI from "openai";
import type { TranscriptionResult } from "./types";
import { MOCK_TRANSCRIPT } from "./mock";

export function hasTranscriber(): boolean {
  return Boolean(process.env.OPENAI_API_KEY);
}

/**
 * アップロードされたファイルを文字起こしする。
 * 動画ファイルでも Whisper は音声トラックを抽出して処理できる。
 */
export async function transcribe(file: File): Promise<TranscriptionResult> {
  if (!hasTranscriber()) {
    return { text: MOCK_TRANSCRIPT, source: "mock", language: "ja" };
  }

  const client = new OpenAI();
  const model = process.env.TRANSCRIBE_MODEL || "whisper-1";

  const res = await client.audio.transcriptions.create({
    file,
    model,
    // whisper-1 は言語自動判定。日本語に寄せたい場合は language: "ja" を指定。
  });

  return { text: res.text, source: "real" };
}
