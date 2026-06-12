import { NextResponse } from "next/server";
import { generateDashboard } from "@/lib/dashboard";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const data = await generateDashboard();
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "ダッシュボード生成に失敗しました" },
      { status: 500 },
    );
  }
}
