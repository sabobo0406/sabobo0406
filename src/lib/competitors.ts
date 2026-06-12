// 競合巡回レポートのコアロジック。
// 1. 各SNSから競合の直近投稿を取得（キーが無ければモック）
// 2. 前回スナップショットと比較してエンゲージメントの伸びを計算
// 3. しきい値以上 伸びた投稿だけを返す
// 4. 今回のスナップショットを保存（次回の基準にする）

import type { CompetitorReport, GrowthItem, PostSnapshot } from "./types";
import { fetchInstagramCompetitorPosts, hasInstagram } from "./instagram";
import { fetchXCompetitorPosts, hasX } from "./x";
import { mockCompetitorPosts } from "./mock";
import { loadPreviousSnapshots, savePreviousSnapshots } from "./store";

function threshold(): number {
  const v = Number(process.env.GROWTH_THRESHOLD_PERCENT);
  return Number.isFinite(v) && v > 0 ? v : 20;
}

async function collectPosts(): Promise<{ posts: PostSnapshot[]; source: "real" | "mock" }> {
  const real = hasInstagram() || hasX();
  if (real) {
    const [ig, x] = await Promise.all([
      fetchInstagramCompetitorPosts(),
      fetchXCompetitorPosts(),
    ]);
    const posts = [...ig, ...x];
    if (posts.length > 0) return { posts, source: "real" };
    // キーはあるが取得0件 → モックで画面を成立させる
  }
  return { posts: mockCompetitorPosts(0), source: "mock" };
}

/**
 * レポートを生成する。
 * @param persist 前日比の基準を更新するか（プレビュー時は false にして基準を汚さない）
 */
export async function generateCompetitorReport(persist = true): Promise<CompetitorReport> {
  const { posts, source } = await collectPosts();
  let previous = await loadPreviousSnapshots();

  // モックかつ前回が無いときは、デモが成立するよう「前日分」を基準として注入
  if (source === "mock" && Object.keys(previous).length === 0) {
    previous = {};
    for (const p of mockCompetitorPosts(1)) previous[p.id] = p;
  }

  const hasBaseline = Object.keys(previous).length > 0;
  const limit = threshold();
  const items: GrowthItem[] = [];

  for (const post of posts) {
    const prev = previous[post.id];
    if (!prev) continue; // 新規投稿は前回が無いので伸び率を出せない
    const previousEngagement = prev.engagement;
    const delta = post.engagement - previousEngagement;
    if (delta <= 0) continue;
    const growthPercent =
      previousEngagement > 0 ? (delta / previousEngagement) * 100 : 100;
    if (growthPercent >= limit) {
      items.push({ post, previousEngagement, delta, growthPercent });
    }
  }

  items.sort((a, b) => b.growthPercent - a.growthPercent);

  if (persist) {
    await savePreviousSnapshots(posts);
  }

  const accounts = new Set(posts.map((p) => p.account));

  return {
    generatedAt: new Date().toISOString(),
    hasBaseline,
    thresholdPercent: limit,
    items,
    source,
    accountsScanned: accounts.size,
  };
}
