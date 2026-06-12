// APIキーが無いときに使うサンプルデータ。
// 画面の見た目・データの流れを、キー無しでも確認できるようにするためのもの。

import type { PostSnapshot } from "./types";

const SAMPLE_ACCOUNTS = [
  { account: "competitor_a", platform: "instagram" as const },
  { account: "competitor_b", platform: "instagram" as const },
  { account: "rival_studio", platform: "x" as const },
];

const SAMPLE_CAPTIONS = [
  "新作コレクションを公開しました🌸 詳細はプロフィールから",
  "ユーザーさんの声を紹介。リアルな使用感をどうぞ",
  "舞台裏をちょっとだけ。チームで作ってます",
  "期間限定キャンペーン開始！お見逃しなく",
  "よくある質問にまとめて回答しました",
  "アップデートのお知らせ。新機能が3つ追加",
];

/** 安定した擬似乱数（seedで再現可能） */
function seeded(seed: number) {
  let s = seed % 2147483647;
  if (s <= 0) s += 2147483646;
  return () => (s = (s * 16807) % 2147483647) / 2147483647;
}

/**
 * 競合投稿のモック。
 * dayOffset を変えると、前日(=1)→当日(=0) でエンゲージメントが伸びた状態を再現できる。
 */
export function mockCompetitorPosts(dayOffset = 0): PostSnapshot[] {
  const rand = seeded(20260612 + dayOffset);
  const now = Date.now();
  const posts: PostSnapshot[] = [];
  let n = 0;
  for (const { account, platform } of SAMPLE_ACCOUNTS) {
    for (let i = 0; i < 4; i++) {
      const base = 200 + Math.floor(rand() * 1800);
      // 当日(dayOffset=0)は一部の投稿だけ大きく伸ばす
      const boost = dayOffset === 0 && i % 2 === 0 ? 1 + rand() * 0.9 : 1 + rand() * 0.1;
      const likes = Math.floor(base * boost);
      const comments = Math.floor(likes * (0.02 + rand() * 0.05));
      const id = `${platform}_${account}_${i}`;
      posts.push({
        id,
        platform,
        account,
        url: `https://example.com/${platform}/${account}/${i}`,
        caption: SAMPLE_CAPTIONS[n % SAMPLE_CAPTIONS.length],
        likes,
        comments,
        engagement: likes + comments,
        postedAt: new Date(now - (i + 1) * 86400000).toISOString(),
        capturedAt: new Date(now - dayOffset * 86400000).toISOString(),
      });
      n++;
    }
  }
  return posts;
}

export const MOCK_TRANSCRIPT = `今日はですね、新しく始めたプロジェクトについて話していきたいと思います。
まず最初にお伝えしたいのは、このツールを作ろうと思ったきっかけです。
毎朝、競合のアカウントを一つ一つ見て回るのって、すごく時間がかかるんですよね。
それを自動化できたらいいなと思ったのが始まりでした。
あとは、売上とかフォロワーの数字が色んな所に散らばっていて、
一画面でぱっと見られたら便利だなと。
最後に、撮った動画や音声をそのまま記事の下書きにできたら、
発信のハードルがぐっと下がるんじゃないかと考えています。`;
