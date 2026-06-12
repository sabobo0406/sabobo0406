// 表示用のフォーマットヘルパー

import type { Metric } from "./types";

export function formatMetric(m: Metric): string {
  switch (m.format) {
    case "currency":
      return `¥${m.value.toLocaleString("ja-JP")}`;
    case "percent":
      return `${m.value.toFixed(2)}%`;
    default:
      return m.value.toLocaleString("ja-JP") + (m.unit ?? "");
  }
}

export function formatNumber(n: number): string {
  return n.toLocaleString("ja-JP");
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function relativeDay(iso: string): string {
  const d = new Date(iso);
  const diffDays = Math.floor((Date.now() - d.getTime()) / 86400000);
  if (diffDays <= 0) return "今日";
  if (diffDays === 1) return "昨日";
  return `${diffDays}日前`;
}
