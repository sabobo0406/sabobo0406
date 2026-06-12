// 軽量なファイルベースの永続化。
// 競合巡回の「前日比」を出すために、前回スナップショットを .data/ に保存する。
// （本番でスケールさせるときは DB に差し替える前提の薄いラッパー）

import { promises as fs } from "fs";
import path from "path";
import type { PostSnapshot } from "./types";

const DATA_DIR = path.join(process.cwd(), ".data");
const SNAPSHOT_FILE = path.join(DATA_DIR, "competitor-snapshots.json");
const FOLLOWER_HISTORY_FILE = path.join(DATA_DIR, "follower-history.json");
const SALES_HISTORY_FILE = path.join(DATA_DIR, "sales-history.json");

async function ensureDir() {
  await fs.mkdir(DATA_DIR, { recursive: true });
}

async function readJson<T>(file: string, fallback: T): Promise<T> {
  try {
    const raw = await fs.readFile(file, "utf-8");
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

async function writeJson(file: string, data: unknown) {
  await ensureDir();
  await fs.writeFile(file, JSON.stringify(data, null, 2), "utf-8");
}

/** 前回の競合投稿スナップショット（id -> engagement） */
export async function loadPreviousSnapshots(): Promise<Record<string, PostSnapshot>> {
  return readJson<Record<string, PostSnapshot>>(SNAPSHOT_FILE, {});
}

/** 今回のスナップショットを保存（次回の前日比の基準になる） */
export async function savePreviousSnapshots(posts: PostSnapshot[]): Promise<void> {
  const map: Record<string, PostSnapshot> = {};
  for (const p of posts) map[p.id] = p;
  await writeJson(SNAPSHOT_FILE, map);
}

type DailyPoint = { date: string; value: number };

async function appendDaily(file: string, value: number, maxDays = 30): Promise<DailyPoint[]> {
  const today = new Date().toISOString().slice(0, 10);
  const history = await readJson<DailyPoint[]>(file, []);
  const without = history.filter((h) => h.date !== today);
  const updated = [...without, { date: today, value }].slice(-maxDays);
  await writeJson(file, updated);
  return updated;
}

export async function recordFollowerTotal(total: number) {
  return appendDaily(FOLLOWER_HISTORY_FILE, total);
}

export async function recordSalesTotal(amount: number) {
  return appendDaily(SALES_HISTORY_FILE, amount);
}

export async function loadFollowerHistory(): Promise<DailyPoint[]> {
  return readJson<DailyPoint[]>(FOLLOWER_HISTORY_FILE, []);
}

export async function loadSalesHistory(): Promise<DailyPoint[]> {
  return readJson<DailyPoint[]>(SALES_HISTORY_FILE, []);
}
