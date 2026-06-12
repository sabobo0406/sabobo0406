// Stripe 連携（売上集計）。
// SDK を足さず REST を直接叩く軽量実装。secret key 未設定なら null。

function key() {
  return process.env.STRIPE_SECRET_KEY || "";
}

export function hasStripe(): boolean {
  return Boolean(key());
}

async function stripeGet(pathname: string): Promise<any | null> {
  const k = key();
  if (!k) return null;
  try {
    const res = await fetch(`https://api.stripe.com/v1${pathname}`, {
      headers: { Authorization: `Bearer ${k}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export interface StripeSummary {
  /** 直近30日の売上合計（最小通貨単位。JPYなら円） */
  total30d: number;
  /** 直近30日の取引件数 */
  count30d: number;
  /** 日次推移（直近30日） */
  trend: { date: string; amount: number }[];
  currency: string;
}

/**
 * 成功した Charge を直近30日分集計する。
 * 取引が多い場合のページングは簡易化（最大1000件）。
 */
export async function fetchStripeSummary(): Promise<StripeSummary | null> {
  if (!key()) return null;
  const since = Math.floor((Date.now() - 30 * 86400000) / 1000);
  const byDay: Record<string, number> = {};
  let total = 0;
  let count = 0;
  let currency = "jpy";
  let startingAfter: string | undefined;

  for (let page = 0; page < 10; page++) {
    const params = new URLSearchParams({ limit: "100", "created[gte]": String(since) });
    if (startingAfter) params.set("starting_after", startingAfter);
    const json = await stripeGet(`/charges?${params.toString()}`);
    if (!json?.data) break;
    for (const ch of json.data) {
      if (ch.paid && !ch.refunded && ch.status === "succeeded") {
        total += ch.amount;
        count++;
        currency = ch.currency || currency;
        const day = new Date(ch.created * 1000).toISOString().slice(0, 10);
        byDay[day] = (byDay[day] ?? 0) + ch.amount;
      }
    }
    if (!json.has_more || json.data.length === 0) break;
    startingAfter = json.data[json.data.length - 1].id;
  }

  const trend = Object.entries(byDay)
    .map(([date, amount]) => ({ date, amount }))
    .sort((a, b) => a.date.localeCompare(b.date));

  return { total30d: total, count30d: count, trend, currency };
}
