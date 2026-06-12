// Instagram Graph API 連携。
// 競合の最近の投稿取得と、自分のフォロワー数取得。
// トークン未設定なら null を返し、呼び出し側でモックにフォールバックする。

import type { PostSnapshot } from "./types";

const GRAPH = "https://graph.facebook.com/v21.0";

function token() {
  return process.env.INSTAGRAM_ACCESS_TOKEN || "";
}

function usernames(): string[] {
  return (process.env.COMPETITOR_INSTAGRAM_USERNAMES || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function hasInstagram(): boolean {
  return Boolean(token());
}

/**
 * Business Discovery で競合（公開ビジネスアカウント）の直近投稿を取得。
 * 自分のビジネスアカウントを経由して相手のユーザー名を問い合わせる Graph API の仕様。
 */
export async function fetchInstagramCompetitorPosts(): Promise<PostSnapshot[]> {
  const accessToken = token();
  const selfId = process.env.INSTAGRAM_BUSINESS_ACCOUNT_ID;
  const targets = usernames();
  if (!accessToken || !selfId || targets.length === 0) return [];

  const out: PostSnapshot[] = [];
  for (const username of targets) {
    const fields =
      `business_discovery.username(${username})` +
      `{username,media.limit(10){id,caption,permalink,media_url,thumbnail_url,like_count,comments_count,timestamp}}`;
    const url = `${GRAPH}/${selfId}?fields=${encodeURIComponent(fields)}&access_token=${accessToken}`;
    try {
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) continue;
      const json = await res.json();
      const media = json?.business_discovery?.media?.data ?? [];
      for (const m of media) {
        const likes = m.like_count ?? 0;
        const comments = m.comments_count ?? 0;
        out.push({
          id: `instagram_${username}_${m.id}`,
          platform: "instagram",
          account: username,
          url: m.permalink ?? `https://instagram.com/${username}`,
          caption: m.caption ?? "",
          thumbnailUrl: m.thumbnail_url ?? m.media_url,
          likes,
          comments,
          engagement: likes + comments,
          postedAt: m.timestamp ?? new Date().toISOString(),
          capturedAt: new Date().toISOString(),
        });
      }
    } catch {
      // ネットワーク等のエラーはスキップ（他アカウントの取得は続行）
    }
  }
  return out;
}

/** 自分のフォロワー数 */
export async function fetchInstagramFollowerCount(): Promise<number | null> {
  const accessToken = token();
  const selfId = process.env.INSTAGRAM_BUSINESS_ACCOUNT_ID;
  if (!accessToken || !selfId) return null;
  try {
    const url = `${GRAPH}/${selfId}?fields=followers_count&access_token=${accessToken}`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return null;
    const json = await res.json();
    return typeof json?.followers_count === "number" ? json.followers_count : null;
  } catch {
    return null;
  }
}
