#!/usr/bin/env node
/**
 * Knowledge Watcher - External change monitoring for AI agent skills
 * Part of the Agent Skill Bus framework
 */

const fs = require("fs");
const path = require("path");

const DATA_DIR = path.resolve(__dirname, "../../data");
const DIFFS_FILE = path.join(DATA_DIR, "knowledge-diffs.jsonl");

function ensureDataDir() {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
}

function readJsonl(filePath) {
  ensureDataDir();
  if (!fs.existsSync(filePath)) return [];
  return fs
    .readFileSync(filePath, "utf-8")
    .trim()
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function writeJsonl(filePath, records) {
  ensureDataDir();
  fs.writeFileSync(
    filePath,
    records.map((r) => JSON.stringify(r)).join("\n") + (records.length ? "\n" : "")
  );
}

function appendJsonl(filePath, record) {
  ensureDataDir();
  fs.appendFileSync(filePath, JSON.stringify(record) + "\n");
}

function nextId(records) {
  const max = records.reduce((m, r) => {
    const num = parseInt(r.id.replace("kd-", ""), 10);
    return isNaN(num) ? m : Math.max(m, num);
  }, 0);
  return `kd-${String(max + 1).padStart(3, "0")}`;
}

// --- Record a knowledge diff ---
function recordDiff({ tier = 1, category, source, summary, impact = "medium", affectedSkills = [], status = "new" }) {
  const diffs = readJsonl(DIFFS_FILE);
  const record = {
    id: nextId(diffs),
    ts: new Date().toISOString(),
    tier: parseInt(tier, 10),
    category,
    source,
    summary,
    impact,
    affectedSkills: typeof affectedSkills === "string" ? affectedSkills.split(",").filter(Boolean) : affectedSkills,
    status,
    action: null,
  };
  appendJsonl(DIFFS_FILE, record);
  console.log(`[RECORDED] ${record.id}: [Tier ${record.tier}] ${summary} (impact=${impact})`);

  if (impact === "high" || impact === "critical") {
    console.log(`  [ALERT] High-impact change detected! Affected skills: ${record.affectedSkills.join(", ") || "unknown"}`);
  }

  return record;
}

// --- Scan dependencies (Tier 1) ---
function scanDependencies(packageJsonPath) {
  const baselinePath = path.join(DATA_DIR, "dep-baseline.json");

  if (!fs.existsSync(packageJsonPath)) {
    console.log(`[SCAN] No package.json found at: ${packageJsonPath}`);
    return [];
  }

  const pkg = JSON.parse(fs.readFileSync(packageJsonPath, "utf-8"));
  const currentDeps = { ...pkg.dependencies, ...pkg.devDependencies };

  let baseline = {};
  if (fs.existsSync(baselinePath)) {
    baseline = JSON.parse(fs.readFileSync(baselinePath, "utf-8"));
  }

  const changes = [];

  for (const [dep, version] of Object.entries(currentDeps)) {
    if (!baseline[dep]) {
      changes.push({ dep, from: null, to: version, type: "added" });
    } else if (baseline[dep] !== version) {
      const semverType = getSemverChange(baseline[dep], version);
      changes.push({ dep, from: baseline[dep], to: version, type: semverType });
    }
  }

  for (const dep of Object.keys(baseline)) {
    if (!currentDeps[dep]) {
      changes.push({ dep, from: baseline[dep], to: null, type: "removed" });
    }
  }

  if (changes.length === 0) {
    console.log("[SCAN] No dependency changes detected.");
  } else {
    console.log(`[SCAN] ${changes.length} dependency change(s) detected:`);
    changes.forEach((c) => {
      const impact = c.type === "major" || c.type === "removed" ? "high" : c.type === "minor" ? "medium" : "low";
      console.log(`  ${c.dep}: ${c.from || "(new)"} -> ${c.to || "(removed)"} [${c.type}]`);
      recordDiff({
        tier: 1,
        category: "dependency",
        source: packageJsonPath,
        summary: `${c.dep} ${c.type}: ${c.from || "new"} -> ${c.to || "removed"}`,
        impact,
      });
    });
  }

  // Update baseline
  fs.writeFileSync(baselinePath, JSON.stringify(currentDeps, null, 2));
  return changes;
}

function getSemverChange(oldVer, newVer) {
  const clean = (v) => v.replace(/[\^~>=<]/g, "").split(".");
  const o = clean(oldVer);
  const n = clean(newVer);
  if (o[0] !== n[0]) return "major";
  if (o[1] !== n[1]) return "minor";
  return "patch";
}

// --- List diffs ---
function listDiffs({ status = null, tier = null, skill = null } = {}) {
  let diffs = readJsonl(DIFFS_FILE);

  if (status) diffs = diffs.filter((d) => d.status === status);
  if (tier) diffs = diffs.filter((d) => d.tier === parseInt(tier, 10));
  if (skill) diffs = diffs.filter((d) => d.affectedSkills.includes(skill));

  if (diffs.length === 0) {
    console.log("[DIFFS] No matching knowledge diffs found.");
    return [];
  }

  // Group by tier
  const grouped = { 1: [], 2: [], 3: [] };
  diffs.forEach((d) => {
    if (!grouped[d.tier]) grouped[d.tier] = [];
    grouped[d.tier].push(d);
  });

  const tierNames = { 1: "Immediate", 2: "Daily", 3: "Weekly" };

  for (const [t, items] of Object.entries(grouped)) {
    if (items.length === 0) continue;
    // Sort by impact
    const impactOrder = { critical: 0, high: 1, medium: 2, low: 3 };
    items.sort((a, b) => (impactOrder[a.impact] ?? 2) - (impactOrder[b.impact] ?? 2));

    console.log(`\n[Tier ${t} - ${tierNames[t]}] ${items.length} diff(s):`);
    items.forEach((d) => {
      console.log(`  ${d.id} [${d.status}] [${d.impact}] ${d.category}: ${d.summary}`);
      if (d.affectedSkills.length > 0) {
        console.log(`    Affects: ${d.affectedSkills.join(", ")}`);
      }
    });
  }

  return diffs;
}

// --- Update diff status ---
function updateDiff(diffId, newStatus, actionId = null) {
  const diffs = readJsonl(DIFFS_FILE);
  const idx = diffs.findIndex((d) => d.id === diffId);
  if (idx === -1) {
    console.error(`[ERROR] Diff ${diffId} not found.`);
    return null;
  }
  diffs[idx].status = newStatus;
  if (actionId) diffs[idx].action = actionId;
  writeJsonl(DIFFS_FILE, diffs);
  console.log(`[UPDATED] ${diffId} -> ${newStatus}${actionId ? ` (action: ${actionId})` : ""}`);
  return diffs[idx];
}

// --- Report ---
function generateReport(days = 7) {
  const diffs = readJsonl(DIFFS_FILE);
  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
  const recent = diffs.filter((d) => new Date(d.ts).getTime() >= cutoff);

  const tierCounts = { 1: 0, 2: 0, 3: 0 };
  const categoryCounts = {};
  let unresolved = 0;

  recent.forEach((d) => {
    tierCounts[d.tier] = (tierCounts[d.tier] || 0) + 1;
    categoryCounts[d.category] = (categoryCounts[d.category] || 0) + 1;
    if (d.status === "new" && (d.impact === "high" || d.impact === "critical")) unresolved++;
  });

  console.log(`\n[REPORT] Knowledge Watcher - Last ${days} day(s):`);
  console.log(`  Total diffs:           ${recent.length}`);
  console.log(`  Tier 1 (Immediate):    ${tierCounts[1] || 0}`);
  console.log(`  Tier 2 (Daily):        ${tierCounts[2] || 0}`);
  console.log(`  Tier 3 (Weekly):       ${tierCounts[3] || 0}`);
  console.log(`  Unresolved high/crit:  ${unresolved}`);
  console.log(`  Categories:            ${Object.entries(categoryCounts).map(([k, v]) => `${k}(${v})`).join(", ")}`);

  return { total: recent.length, tierCounts, categoryCounts, unresolved };
}

// --- CLI ---
const [, , cmd, ...args] = process.argv;

function parseArgs(args) {
  const result = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith("--")) {
      const key = args[i].slice(2);
      const val = args[i + 1] && !args[i + 1].startsWith("--") ? args[++i] : true;
      result[key] = val;
    }
  }
  return result;
}

switch (cmd) {
  case "record":
    recordDiff(parseArgs(args));
    break;
  case "scan":
    scanDependencies(args[0] || "./package.json");
    break;
  case "list":
    listDiffs(parseArgs(args));
    break;
  case "update":
    updateDiff(args[0], args[1], args[2] || null);
    break;
  case "report":
    generateReport(parseInt(args[0], 10) || 7);
    break;
  default:
    console.log(`Usage: watcher.js <command>
Commands:
  record  --tier <1|2|3> --category <type> --source <src> --summary <text> [--impact high] [--affectedSkills s1,s2]
  scan    [path/to/package.json]   Scan for dependency changes (Tier 1)
  list    [--status new] [--tier 1] [--skill name]   List knowledge diffs
  update  <id> <status> [actionId]   Update diff status (new|acknowledged|acted|dismissed)
  report  [days]                     Generate monitoring report`);
}
