"use client";

import { useEffect, useState } from "react";
import { formatDateTime, formatNumber, relativeDay } from "@/lib/format";
import type { CompetitorReport } from "@/lib/types";

export default function CompetitorsPage() {
  const [report, setReport] = useState<CompetitorReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadPreview() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/competitors/report?preview=1", { cache: "no-store" });
      if (!res.ok) throw new Error((await res.json()).error || "取得に失敗しました");
      setReport(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラー");
    } finally {
      setLoading(false);
    }
  }

  // 巡回を実行（基準を更新 = 朝の巡回相当）
  async function runPatrol() {
    setRunning(true);
    setError(null);
    try {
      const res = await fetch("/api/competitors/report", { method: "POST" });
      if (!res.ok) throw new Error((await res.json()).error || "実行に失敗しました");
      setReport(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラー");
    } finally {
      setRunning(false);
    }
  }

  useEffect(() => {
    loadPreview();
  }, []);

  const platformBadge = (p: string) =>
    p === "instagram" ? "📷 Instagram" : "𝕏 X";

  return (
    <div>
      <div className="flex items-end justify-between flex-wrap gap-2 mb-2">
        <div>
          <h1 className="text-2xl font-bold">競合巡回レポート</h1>
          <p className="text-sub text-sm mt-1">
            登録した競合を巡回し、前回より伸びた投稿だけを抽出します。
          </p>
        </div>
        <button
          onClick={runPatrol}
          className="px-4 py-2 rounded-full bg-accent text-white text-sm hover:opacity-90 disabled:opacity-50"
          disabled={running}
        >
          {running ? "巡回中…" : "🔭 いま巡回する"}
        </button>
      </div>

      {report && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-sub mb-4">
          <span>巡回アカウント: {report.accountsScanned}</span>
          <span>抽出しきい値: 前回比 +{report.thresholdPercent}% 以上</span>
          <span>
            データ:{" "}
            {report.source === "real" ? (
              <span className="text-green-600">実API</span>
            ) : (
              <span className="text-amber-600">サンプル</span>
            )}
          </span>
          <span>生成: {formatDateTime(report.generatedAt)}</span>
        </div>
      )}

      {error && (
        <div className="rounded-lg bg-red-50 text-red-700 px-4 py-3 text-sm mb-4">{error}</div>
      )}

      {loading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-xl bg-white border border-black/5 h-24 animate-pulse" />
          ))}
        </div>
      )}

      {report && !report.hasBaseline && (
        <div className="rounded-lg bg-blue-50 text-blue-800 px-4 py-3 text-sm mb-4">
          初回のため基準データを取得しました。明日もう一度巡回すると、伸びた投稿が表示されます。
        </div>
      )}

      {report && report.hasBaseline && report.items.length === 0 && (
        <div className="rounded-lg bg-white border border-black/5 px-4 py-8 text-center text-sub">
          前回比で +{report.thresholdPercent}% 以上 伸びた投稿はありませんでした。
        </div>
      )}

      <ul className="space-y-3">
        {report?.items.map((item) => (
          <li
            key={item.post.id}
            className="rounded-xl bg-white border border-black/5 p-4 shadow-sm flex gap-4"
          >
            <div className="shrink-0 flex flex-col items-center justify-center w-20">
              <div className="text-2xl font-bold text-accent">
                +{Math.round(item.growthPercent)}%
              </div>
              <div className="text-[10px] text-sub mt-0.5">前回比</div>
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 text-xs text-sub mb-1">
                <span className="font-medium text-ink">@{item.post.account}</span>
                <span>{platformBadge(item.post.platform)}</span>
                <span>· {relativeDay(item.post.postedAt)}投稿</span>
              </div>
              <p className="text-sm line-clamp-2 mb-2">{item.post.caption || "(本文なし)"}</p>
              <div className="flex items-center gap-3 text-xs text-sub">
                <span>♡ {formatNumber(item.post.likes)}</span>
                <span>💬 {formatNumber(item.post.comments)}</span>
                <span className="text-green-600">
                  +{formatNumber(item.delta)} (旧 {formatNumber(item.previousEngagement)})
                </span>
                <a
                  href={item.post.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent hover:underline ml-auto"
                >
                  投稿を開く →
                </a>
              </div>
            </div>
          </li>
        ))}
      </ul>

      <div className="mt-8 rounded-xl bg-white/60 border border-black/5 p-4 text-xs text-sub">
        <p className="font-medium text-ink mb-1">毎朝の自動巡回</p>
        <p>
          サーバーで <code>npm run morning-report</code> を cron 等で毎朝実行すると、巡回・基準更新・
          サマリー出力までを自動化できます。実データに切り替えるには <code>.env.local</code> に
          各SNSのトークンと競合ユーザー名を設定してください。
        </p>
      </div>
    </div>
  );
}
