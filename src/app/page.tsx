"use client";

import { useEffect, useState } from "react";
import Sparkline from "@/components/Sparkline";
import { formatMetric, formatDateTime, formatNumber } from "@/lib/format";
import type { DashboardData } from "@/lib/types";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/dashboard/metrics", { cache: "no-store" });
      if (!res.ok) throw new Error((await res.json()).error || "取得に失敗しました");
      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラー");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div>
      <div className="flex items-end justify-between flex-wrap gap-2 mb-6">
        <div>
          <h1 className="text-2xl font-bold">ダッシュボード</h1>
          <p className="text-sub text-sm mt-1">売上とフォロワーを1画面に集約します。</p>
        </div>
        <button
          onClick={load}
          className="px-4 py-2 rounded-full bg-ink text-white text-sm hover:opacity-90 disabled:opacity-50"
          disabled={loading}
        >
          {loading ? "更新中…" : "↻ 更新"}
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 text-red-700 px-4 py-3 text-sm mb-4">{error}</div>
      )}

      {loading && !data && <SkeletonGrid />}

      {data && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
            {data.metrics.map((m) => (
              <div key={m.key} className="rounded-xl bg-white border border-black/5 p-4 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-sub">{m.label}</span>
                  {m.source === "mock" && (
                    <span className="text-[10px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded">
                      サンプル
                    </span>
                  )}
                </div>
                <div className="text-xl font-bold mt-2">{formatMetric(m)}</div>
                {m.changePercent !== null && (
                  <div
                    className={`text-xs mt-1 ${
                      m.changePercent >= 0 ? "text-green-600" : "text-red-500"
                    }`}
                  >
                    {m.changePercent >= 0 ? "▲" : "▼"} {Math.abs(m.changePercent).toFixed(1)}%
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="rounded-xl bg-white border border-black/5 p-5 shadow-sm">
              <h2 className="font-semibold mb-1">売上推移</h2>
              <p className="text-xs text-sub mb-3">
                直近 {data.salesTrend.length} 日 / 合計 ¥
                {formatNumber(data.salesTrend.reduce((s, t) => s + t.amount, 0))}
              </p>
              <Sparkline points={data.salesTrend.map((t) => t.amount)} color="#e07a5f" />
              <div className="flex justify-between text-[10px] text-sub mt-1">
                <span>{data.salesTrend[0]?.date}</span>
                <span>{data.salesTrend[data.salesTrend.length - 1]?.date}</span>
              </div>
            </div>

            <div className="rounded-xl bg-white border border-black/5 p-5 shadow-sm">
              <h2 className="font-semibold mb-1">フォロワー推移</h2>
              <p className="text-xs text-sub mb-3">
                最新 {formatNumber(data.followerTrend[data.followerTrend.length - 1]?.count ?? 0)} 人
              </p>
              <Sparkline points={data.followerTrend.map((t) => t.count)} color="#3d5a80" />
              <div className="flex justify-between text-[10px] text-sub mt-1">
                <span>{data.followerTrend[0]?.date}</span>
                <span>{data.followerTrend[data.followerTrend.length - 1]?.date}</span>
              </div>
            </div>
          </div>

          <p className="text-xs text-sub mt-4">最終更新: {formatDateTime(data.generatedAt)}</p>
        </>
      )}
    </div>
  );
}

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="rounded-xl bg-white border border-black/5 p-4 h-24 animate-pulse" />
      ))}
    </div>
  );
}
