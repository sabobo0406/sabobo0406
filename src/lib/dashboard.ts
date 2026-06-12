// ダッシュボード集計。売上(Stripe)とフォロワー(Instagram/X)を1画面分にまとめる。

import type { DashboardData, Metric } from "./types";
import { fetchStripeSummary, hasStripe } from "./stripe";
import { fetchInstagramFollowerCount, hasInstagram } from "./instagram";
import { fetchXFollowerCount, hasX } from "./x";
import { loadFollowerHistory, recordFollowerTotal } from "./store";

function changePercent(trend: { amount?: number; value?: number }[]): number | null {
  if (trend.length < 2) return null;
  const vals = trend.map((t) => (t.amount ?? t.value ?? 0));
  const last = vals[vals.length - 1];
  const prev = vals[vals.length - 2];
  if (prev === 0) return null;
  return ((last - prev) / prev) * 100;
}

/** モックの売上推移（直近14日） */
function mockSalesTrend(): { date: string; amount: number }[] {
  const out: { date: string; amount: number }[] = [];
  for (let i = 13; i >= 0; i--) {
    const date = new Date(Date.now() - i * 86400000).toISOString().slice(0, 10);
    const amount = 80000 + Math.round(Math.sin(i / 2) * 25000 + i * 1500 + Math.random() * 8000);
    out.push({ date, amount });
  }
  return out;
}

function mockFollowerTrend(): { date: string; count: number }[] {
  const out: { date: string; count: number }[] = [];
  let base = 12400;
  for (let i = 13; i >= 0; i--) {
    const date = new Date(Date.now() - i * 86400000).toISOString().slice(0, 10);
    base += Math.round(Math.random() * 60 + 10);
    out.push({ date, count: base });
  }
  return out;
}

export async function generateDashboard(): Promise<DashboardData> {
  const metrics: Metric[] = [];

  // ── 売上（Stripe）──
  let salesTrend: { date: string; amount: number }[];
  if (hasStripe()) {
    const summary = await fetchStripeSummary();
    if (summary) {
      salesTrend = summary.trend.slice(-14);
      metrics.push({
        key: "revenue",
        label: "売上（直近30日）",
        value: summary.total30d,
        format: "currency",
        changePercent: changePercent(salesTrend),
        source: "real",
      });
      metrics.push({
        key: "orders",
        label: "取引件数（直近30日）",
        value: summary.count30d,
        format: "number",
        changePercent: null,
        unit: "件",
        source: "real",
      });
    } else {
      salesTrend = mockSalesTrend();
      pushMockSales(metrics, salesTrend);
    }
  } else {
    salesTrend = mockSalesTrend();
    pushMockSales(metrics, salesTrend);
  }

  // ── フォロワー（Instagram + X）──
  let totalFollowers = 0;
  let followerSource: "real" | "mock" = "mock";
  if (hasInstagram() || hasX()) {
    const [ig, x] = await Promise.all([
      hasInstagram() ? fetchInstagramFollowerCount() : Promise.resolve(null),
      hasX() ? fetchXFollowerCount() : Promise.resolve(null),
    ]);
    if (ig !== null || x !== null) {
      totalFollowers = (ig ?? 0) + (x ?? 0);
      followerSource = "real";
    }
  }

  let followerTrend: { date: string; count: number }[];
  if (followerSource === "real") {
    const history = await recordFollowerTotal(totalFollowers);
    followerTrend = history.map((h) => ({ date: h.date, count: h.value }));
    if (followerTrend.length < 2) {
      // 履歴が浅いうちは推移グラフをモックで補う
      followerTrend = mockFollowerTrend();
      followerTrend[followerTrend.length - 1] = {
        date: new Date().toISOString().slice(0, 10),
        count: totalFollowers,
      };
    }
  } else {
    const history = await loadFollowerHistory();
    followerTrend =
      history.length >= 2
        ? history.map((h) => ({ date: h.date, count: h.value }))
        : mockFollowerTrend();
    totalFollowers = followerTrend[followerTrend.length - 1].count;
  }

  metrics.push({
    key: "followers",
    label: "総フォロワー（IG + X）",
    value: totalFollowers,
    format: "number",
    changePercent: changePercent(followerTrend.map((t) => ({ value: t.count }))),
    unit: "人",
    source: followerSource,
  });

  // ── エンゲージメント率（簡易・モック寄り）──
  const engagementRate = 3.2 + (Math.random() * 1.5 - 0.75);
  metrics.push({
    key: "engagement",
    label: "平均エンゲージメント率",
    value: Number(engagementRate.toFixed(2)),
    format: "percent",
    changePercent: null,
    source: "mock",
  });

  return {
    generatedAt: new Date().toISOString(),
    metrics,
    salesTrend,
    followerTrend,
  };
}

function pushMockSales(metrics: Metric[], trend: { date: string; amount: number }[]) {
  const total = trend.reduce((s, t) => s + t.amount, 0);
  metrics.push({
    key: "revenue",
    label: "売上（直近14日）",
    value: total,
    format: "currency",
    changePercent: changePercent(trend),
    source: "mock",
  });
  metrics.push({
    key: "orders",
    label: "取引件数（直近14日）",
    value: Math.round(total / 9800),
    format: "number",
    changePercent: null,
    unit: "件",
    source: "mock",
  });
}
