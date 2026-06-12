import { NextResponse } from "next/server";
import { transcribe } from "@/lib/transcription";
import { draftArticle } from "@/lib/anthropic";

export const dynamic = "force-dynamic";
export const maxDuration = 300; // 文字起こし+生成は時間がかかるため上限を延ばす

// multipart/form-data: file（音声/動画）+ draft（"1" なら記事下書きまで生成）
export async function POST(req: Request) {
  try {
    const form = await req.formData();
    const file = form.get("file");
    const wantDraft = form.get("draft") === "1";

    if (!(file instanceof File)) {
      return NextResponse.json({ error: "ファイルが見つかりません" }, { status: 400 });
    }

    const transcription = await transcribe(file);

    if (!wantDraft) {
      return NextResponse.json({ transcription });
    }

    const article = await draftArticle(transcription.text);
    return NextResponse.json({ transcription, article });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "処理に失敗しました" },
      { status: 500 },
    );
  }
}
