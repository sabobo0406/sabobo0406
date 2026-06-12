// X (Twitter) API v2 連携。
// 競合の最近のツイートのエンゲージメント取得と、自分のフォロワー数取得。
// Bearer トークン未設定なら空配列 / null を返す。

import type { PostSnapshot } from "./types";

const API = "https://api.twitter.com/2";

function bearer() {
  return process.env.X_BEARER_TOKEN || "";
}

function usernames(): string[] {
  return (process.env.COMPETITOR_X_USERNAMES || "")
    .split(",")
    .map((s) => s.trim().replace(/^@/, ""))
    .filter(Boolean);
}

export function hasX(): boolean {
  return Boolean(bearer());
}

async function xGet(pathname: string): Promise<any | null> {
  const t = bearer();
  if (!t) return null;
  try {
    const res = await fetch(`${API}${pathname}`, {
      headers: { Authorization: `Bearer ${t}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchXCompetitorPosts(): Promise<PostSnapshot[]> {
  const targets = usernames();
  if (!bearer() || targets.length === 0) return [];

  const out: PostSnapshot[] = [];
  for (const username of targets) {
    const userJson = await xGet(`/users/by/username/${username}`);
    const userId = userJson?.data?.id;
    if (!userId) continue;
    const tweetsJson = await xGet(
      `/users/${userId}/tweets?max_results=10&tweet.fields=public_metrics,created_at`,
    );
    const tweets = tweetsJson?.data ?? [];
    for (const tw of tweets) {
      const m = tw.public_metrics ?? {};
      const likes = m.like_count ?? 0;
      const comments = (m.reply_count ?? 0) + (m.retweet_count ?? 0);
      out.push({
        id: `x_${username}_${tw.id}`,
        platform: "x",
        account: username,
        url: `https://x.com/${username}/status/${tw.id}`,
        caption: tw.text ?? "",
        likes,
        comments,
        engagement: likes + comments,
        postedAt: tw.created_at ?? new Date().toISOString(),
        capturedAt: new Date().toISOString(),
      });
    }
  }
  return out;
}

export async function fetchXFollowerCount(): Promise<number | null> {
  if (!bearer()) return null;
  // 自分のアカウント名は競合リストとは別に、ここでは me エンドポイントを使う
  // （OAuth2 ユーザーコンテキストが必要な場合があるため、取得不可なら null）
  const json = await xGet(`/users/me?user.fields=public_metrics`);
  const count = json?.data?.public_metrics?.followers_count;
  return typeof count === "number" ? count : null;
}
