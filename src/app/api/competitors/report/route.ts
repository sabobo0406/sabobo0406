import { NextResponse } from "next/server";
import { generateCompetitorReport } from "@/lib/competitors";

export const dynamic = "force-dynamic";

// GET  /api/competitors/report?preview=1  → 基準を更新せずプレビュー
// POST /api/competitors/report            → 巡回を実行し、基準を更新（朝の巡回相当）
export async function GET(req: Request) {
  const preview = new URL(req.url).searchParams.get("preview") === "1";
  try {
    const report = await generateCompetitorReport(!preview);
    return NextResponse.json(report);
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "レポート生成に失敗しました" },
      { status: 500 },
    );
  }
}

export async function POST() {
  try {
    const report = await generateCompetitorReport(true);
    return NextResponse.json(report);
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "レポート生成に失敗しました" },
      { status: 500 },
    );
  }
}
