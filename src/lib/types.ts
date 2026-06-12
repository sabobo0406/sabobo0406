// アプリ全体で使う型定義

export type Platform = "instagram" | "x";

/** 1件の投稿スナップショット */
export interface PostSnapshot {
  id: string;
  platform: Platform;
  account: string;
  url: string;
  caption: string;
  thumbnailUrl?: string;
  likes: number;
  comments: number;
  /** エンゲージメント合計（likes + comments）。並び替え・伸び率計算の基準 */
  engagement: number;
  postedAt: string; // ISO
  capturedAt: string; // ISO（このスナップショットを取得した時刻）
}

/** 前回比で伸びた投稿（レポートの1行） */
export interface GrowthItem {
  post: PostSnapshot;
  previousEngagement: number;
  delta: number;
  growthPercent: number;
}

export interface CompetitorReport {
  generatedAt: string;
  /** 前回スナップショットがあったか（無い初回はベースライン取得のみ） */
  hasBaseline: boolean;
  thresholdPercent: number;
  items: GrowthItem[];
  /** データソース（real = 実API / mock = サンプル） */
  source: "real" | "mock";
  accountsScanned: number;
}

/** ダッシュボードの1指標 */
export interface Metric {
  key: string;
  label: string;
  value: number;
  /** 表示フォーマット */
  format: "number" | "currency" | "percent";
  /** 前期間比（%）。未取得なら null */
  changePercent: number | null;
  unit?: string;
  source: "real" | "mock";
}

export interface DashboardData {
  generatedAt: string;
  metrics: Metric[];
  /** 直近の売上推移（日次） */
  salesTrend: { date: string; amount: number }[];
  /** フォロワー推移（日次・全プラットフォーム合算） */
  followerTrend: { date: string; count: number }[];
}

export interface TranscriptionResult {
  text: string;
  source: "real" | "mock";
  durationSec?: number;
  language?: string;
}

export interface ArticleDraft {
  title: string;
  body: string; // Markdown
  source: "real" | "mock";
}
