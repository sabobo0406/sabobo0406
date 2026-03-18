#!/usr/bin/env node
/**
 * Self-Improving Skills - Seven-step quality loop for AI agent skill monitoring
 * Part of the Agent Skill Bus framework
 */

const fs = require("fs");
const path = require("path");

const DATA_DIR = path.resolve(__dirname, "../../data");
const RUNS_FILE = path.join(DATA_DIR, "skill-runs.jsonl");
const IMPROVEMENTS_FILE = path.join(DATA_DIR, "improvements.jsonl");
const ROLLING_WINDOW = 20;
const DRIFT_THRESHOLD = 0.15;

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

function nextId(records, prefix) {
  const max = records.reduce((m, r) => {
    const num = parseInt(r.id.replace(`${prefix}-`, ""), 10);
    return isNaN(num) ? m : Math.max(m, num);
  }, 0);
  return `${prefix}-${String(max + 1).padStart(3, "0")}`;
}

// --- OBSERVE ---
function recordRun({ agent, skill, task, result = "success", score = 1.0, duration = 0, meta = {} }) {
  const runs = readJsonl(RUNS_FILE);
  const record = {
    id: nextId(runs, "sr"),
    ts: new Date().toISOString(),
    agent,
    skill,
    task,
    result,
    score: parseFloat(score),
    duration: parseInt(duration, 10),
    meta,
  };
  appendJsonl(RUNS_FILE, record);
  console.log(`[RECORDED] ${record.id}: ${skill} by ${agent} -> ${result} (score=${score})`);
  return record;
}

// --- ANALYZE ---
function analyzeSkill(skillName) {
  const runs = readJsonl(RUNS_FILE).filter((r) => r.skill === skillName);

  if (runs.length === 0) {
    console.log(`[ANALYZE] No runs found for skill: ${skillName}`);
    return null;
  }

  const recent = runs.slice(-ROLLING_WINDOW);
  const avgScore = recent.reduce((s, r) => s + r.score, 0) / recent.length;
  const failures = recent.filter((r) => r.result !== "success").length;
  const failureRate = failures / recent.length;

  // Trend calculation
  const half = Math.floor(recent.length / 2);
  const firstHalf = recent.slice(0, half);
  const secondHalf = recent.slice(half);
  const avgFirst = firstHalf.reduce((s, r) => s + r.score, 0) / (firstHalf.length || 1);
  const avgSecond = secondHalf.reduce((s, r) => s + r.score, 0) / (secondHalf.length || 1);
  const drift = avgFirst > 0 ? (avgFirst - avgSecond) / avgFirst : 0;

  let trend = "stable";
  if (avgSecond - avgFirst > 0.05) trend = "improving";
  if (avgFirst - avgSecond > 0.05) trend = "declining";

  let status = "healthy";
  if (avgScore < 0.6 || failureRate >= 0.3 || drift > DRIFT_THRESHOLD) status = "critical";
  else if (avgScore < 0.8 || failureRate >= 0.1) status = "warning";

  const report = {
    skill: skillName,
    totalRuns: runs.length,
    windowSize: recent.length,
    avgScore: Math.round(avgScore * 100) / 100,
    failureRate: Math.round(failureRate * 100) + "%",
    trend,
    drift: Math.round(drift * 100) + "%",
    status,
  };

  console.log(`[ANALYZE] Skill Health Report for "${skillName}":`);
  console.log(`  Status:       ${status.toUpperCase()}`);
  console.log(`  Avg Score:    ${report.avgScore}`);
  console.log(`  Failure Rate: ${report.failureRate}`);
  console.log(`  Trend:        ${trend}`);
  console.log(`  Drift:        ${report.drift}`);
  console.log(`  Runs:         ${report.totalRuns} total, ${report.windowSize} in window`);

  if (drift > DRIFT_THRESHOLD) {
    console.log(`  [ALERT] Week-over-week drift (${report.drift}) exceeds ${DRIFT_THRESHOLD * 100}% threshold!`);
  }

  return report;
}

// --- DIAGNOSE ---
function diagnoseSkill(skillName) {
  const runs = readJsonl(RUNS_FILE).filter((r) => r.skill === skillName);
  const failures = runs.filter((r) => r.result !== "success").slice(-10);

  if (failures.length === 0) {
    console.log(`[DIAGNOSE] No failures found for skill: ${skillName}`);
    return null;
  }

  console.log(`[DIAGNOSE] Analyzing ${failures.length} recent failures for "${skillName}":`);

  // Pattern analysis
  const agents = {};
  const tasks = {};
  let totalDuration = 0;

  failures.forEach((f) => {
    agents[f.agent] = (agents[f.agent] || 0) + 1;
    const taskType = f.task.split(" ").slice(0, 2).join(" ");
    tasks[taskType] = (tasks[taskType] || 0) + 1;
    totalDuration += f.duration || 0;
  });

  const avgDuration = totalDuration / failures.length;
  const topAgent = Object.entries(agents).sort((a, b) => b[1] - a[1])[0];
  const topTask = Object.entries(tasks).sort((a, b) => b[1] - a[1])[0];

  const diagnosis = {
    skill: skillName,
    failureCount: failures.length,
    mostFailingAgent: topAgent ? topAgent[0] : "N/A",
    mostFailingTaskType: topTask ? topTask[0] : "N/A",
    avgFailureDuration: Math.round(avgDuration),
    recentScores: failures.map((f) => f.score),
  };

  console.log(`  Most failing agent:     ${diagnosis.mostFailingAgent}`);
  console.log(`  Most failing task type: ${diagnosis.mostFailingTaskType}`);
  console.log(`  Avg failure duration:   ${diagnosis.avgFailureDuration}s`);
  console.log(`  Recent failure scores:  ${diagnosis.recentScores.join(", ")}`);

  return diagnosis;
}

// --- PROPOSE ---
function proposeImprovements(skillName) {
  const report = analyzeSkill(skillName);
  if (!report) return [];

  const proposals = [];

  if (report.status === "critical" || report.status === "warning") {
    if (parseFloat(report.failureRate) > 20) {
      proposals.push({
        description: "Add error handling and retry logic to skill execution",
        impact: "Reduce failure rate by handling transient errors",
        riskLevel: "low",
      });
    }
    if (report.trend === "declining") {
      proposals.push({
        description: "Review and update skill prompt instructions for clarity",
        impact: "Reverse score decline by improving instruction specificity",
        riskLevel: "medium",
      });
    }
    if (report.drift > "15%") {
      proposals.push({
        description: "Restructure skill workflow to handle new patterns",
        impact: "Address fundamental drift in task requirements",
        riskLevel: "high",
      });
    }
  }

  if (proposals.length === 0) {
    console.log(`[PROPOSE] No improvements needed for "${skillName}" (status: ${report.status})`);
  } else {
    console.log(`\n[PROPOSE] ${proposals.length} improvement(s) for "${skillName}":`);
    proposals.forEach((p, i) => {
      console.log(`  ${i + 1}. [${p.riskLevel.toUpperCase()}] ${p.description}`);
      console.log(`     Impact: ${p.impact}`);
    });
  }

  return proposals;
}

// --- RECORD improvement ---
function recordImprovement({ skill, diagnosis, action, riskLevel = "low", approved = true, scoreBefore = null }) {
  const improvements = readJsonl(IMPROVEMENTS_FILE);
  const record = {
    id: nextId(improvements, "imp"),
    ts: new Date().toISOString(),
    skill,
    step: "APPLY",
    diagnosis,
    action,
    riskLevel,
    approved,
    scoreBefore: scoreBefore !== null ? parseFloat(scoreBefore) : null,
    scoreAfter: null,
  };
  appendJsonl(IMPROVEMENTS_FILE, record);
  console.log(`[IMPROVEMENT] ${record.id}: Applied "${action}" to ${skill} (risk=${riskLevel})`);
  return record;
}

function listImprovements(skillName) {
  let improvements = readJsonl(IMPROVEMENTS_FILE);
  if (skillName) improvements = improvements.filter((i) => i.skill === skillName);

  if (improvements.length === 0) {
    console.log("[IMPROVEMENTS] No improvements recorded.");
  } else {
    console.log(`[IMPROVEMENTS] ${improvements.length} record(s):`);
    improvements.forEach((i) => {
      const effectiveness =
        i.scoreAfter !== null ? ` (${i.scoreBefore} -> ${i.scoreAfter})` : " (pending evaluation)";
      console.log(`  ${i.id} [${i.riskLevel}] ${i.skill}: ${i.action}${effectiveness}`);
    });
  }
  return improvements;
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
    recordRun(parseArgs(args));
    break;
  case "analyze":
    analyzeSkill(args[0]);
    break;
  case "diagnose":
    diagnoseSkill(args[0]);
    break;
  case "propose":
    proposeImprovements(args[0]);
    break;
  case "improve":
    recordImprovement(parseArgs(args));
    break;
  case "history":
    listImprovements(args[0]);
    break;
  default:
    console.log(`Usage: improve.js <command>
Commands:
  record   --agent <name> --skill <skill> --task <desc> --result <success|failure> --score <0.0-1.0>
  analyze  <skill-name>          Show skill health report
  diagnose <skill-name>          Diagnose failure patterns
  propose  <skill-name>          Suggest improvements
  improve  --skill <name> --diagnosis <text> --action <text> --riskLevel <low|medium|high>
  history  [skill-name]          Show improvement history`);
}
