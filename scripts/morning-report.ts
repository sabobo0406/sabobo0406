// 毎朝の自動巡回スクリプト。
// cron 等で `npm run morning-report` を叩くと、巡回→基準更新→サマリー出力を行う。
// 例（毎朝7時）: 0 7 * * *  cd /path/to/app && npm run morning-report >> patrol.log 2>&1

import { generateCompetitorReport } from "../src/lib/competitors";

async function main() {
  const report = await generateCompetitorReport(true);

  const lines: string[] = [];
  lines.push("════════════════════════════════════════");
  lines.push(`🔭 競合巡回レポート  ${new Date().toLocaleString("ja-JP")}`);
  lines.push(`データソース: ${report.source === "real" ? "実API" : "サンプル"}`);
  lines.push(`巡回アカウント: ${report.accountsScanned} / しきい値: +${report.thresholdPercent}%`);
  lines.push("════════════════════════════════════════");

  if (!report.hasBaseline) {
    lines.push("初回のため基準データのみ取得しました。明日から伸び率を算出します。");
  } else if (report.items.length === 0) {
    lines.push(`前回比 +${report.thresholdPercent}% 以上 伸びた投稿はありませんでした。`);
  } else {
    report.items.forEach((item, i) => {
      lines.push("");
      lines.push(
        `${i + 1}. [+${Math.round(item.growthPercent)}%] @${item.post.account} (${item.post.platform})`,
      );
      lines.push(`   ${item.post.caption.slice(0, 60).replace(/\n/g, " ")}`);
      lines.push(
        `   ♡${item.post.likes} 💬${item.post.comments}  (+${item.delta}) ${item.post.url}`,
      );
    });
  }

  console.log(lines.join("\n"));

  // ここで Slack / メール / Notion 等に送る処理を足せます。
  // 例: await fetch(process.env.SLACK_WEBHOOK_URL!, { method: "POST", body: JSON.stringify({ text: lines.join("\n") }) })
}

main().catch((e) => {
  console.error("巡回に失敗しました:", e);
  process.exit(1);
});
