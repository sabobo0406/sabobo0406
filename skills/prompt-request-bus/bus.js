#!/usr/bin/env node
/**
 * Prompt Request Bus - JSONL-based task queue with DAG dependency resolution
 * Part of the Agent Skill Bus framework
 */

const fs = require("fs");
const path = require("path");

const DATA_DIR = path.resolve(__dirname, "../../data");
const QUEUE_FILE = path.join(DATA_DIR, "queue.jsonl");
const LOCKS_FILE = path.join(DATA_DIR, "active-locks.jsonl");
const DEFAULT_TTL = 3600; // seconds

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

function nextId(tasks) {
  const max = tasks.reduce((m, t) => {
    const num = parseInt(t.id.replace("pr-", ""), 10);
    return isNaN(num) ? m : Math.max(m, num);
  }, 0);
  return `pr-${String(max + 1).padStart(3, "0")}`;
}

function cleanExpiredLocks() {
  const locks = readJsonl(LOCKS_FILE);
  const now = Date.now();
  const active = locks.filter((l) => {
    const lockedAt = new Date(l.lockedAt).getTime();
    return now - lockedAt < (l.ttl || DEFAULT_TTL) * 1000;
  });
  writeJsonl(LOCKS_FILE, active);
  return active;
}

function checkFileLockConflict(affectedFiles) {
  const locks = cleanExpiredLocks();
  const conflicts = [];
  for (const lock of locks) {
    const overlap = lock.files.filter((f) => affectedFiles.includes(f));
    if (overlap.length > 0) {
      conflicts.push({ taskId: lock.taskId, files: overlap });
    }
  }
  return conflicts;
}

// --- Commands ---

function enqueue({ source = "human", priority = "medium", agent, task, dependsOn = [], affectedFiles = [], dagId = null }) {
  const tasks = readJsonl(QUEUE_FILE);

  // Deduplication
  const dup = tasks.find((t) => t.agent === agent && t.task === task && t.status === "queued");
  if (dup) {
    console.log(`[SKIP] Duplicate task already queued: ${dup.id}`);
    return dup;
  }

  // Lock conflict warning
  if (affectedFiles.length > 0) {
    const conflicts = checkFileLockConflict(affectedFiles);
    if (conflicts.length > 0) {
      console.warn(`[WARN] File lock conflicts: ${JSON.stringify(conflicts)}`);
    }
  }

  const record = {
    id: nextId(tasks),
    ts: new Date().toISOString(),
    source,
    priority,
    agent,
    task,
    status: "queued",
    dependsOn,
    affectedFiles,
    dagId,
  };

  appendJsonl(QUEUE_FILE, record);
  console.log(`[ENQUEUED] ${record.id}: ${task} (priority=${priority}, agent=${agent})`);
  return record;
}

function dispatch() {
  const tasks = readJsonl(QUEUE_FILE);
  const doneIds = new Set(tasks.filter((t) => t.status === "done").map((t) => t.id));

  const ready = tasks
    .filter((t) => t.status === "queued" && t.dependsOn.every((dep) => doneIds.has(dep)))
    .sort((a, b) => {
      const order = { critical: 0, high: 1, medium: 2, low: 3 };
      return (order[a.priority] ?? 2) - (order[b.priority] ?? 2);
    });

  if (ready.length === 0) {
    console.log("[DISPATCH] No tasks ready to execute.");
  } else {
    console.log(`[DISPATCH] ${ready.length} task(s) ready:`);
    ready.forEach((t) => console.log(`  ${t.id} [${t.priority}] ${t.agent}: ${t.task}`));
  }
  return ready;
}

function updateStatus(taskId, newStatus) {
  const tasks = readJsonl(QUEUE_FILE);
  const idx = tasks.findIndex((t) => t.id === taskId);
  if (idx === -1) {
    console.error(`[ERROR] Task ${taskId} not found.`);
    return null;
  }

  tasks[idx].status = newStatus;

  if (newStatus === "locked" || newStatus === "running") {
    const lock = {
      taskId,
      files: tasks[idx].affectedFiles || [],
      lockedAt: new Date().toISOString(),
      ttl: DEFAULT_TTL,
    };
    appendJsonl(LOCKS_FILE, lock);
  }

  if (newStatus === "done" || newStatus === "failed") {
    const locks = readJsonl(LOCKS_FILE).filter((l) => l.taskId !== taskId);
    writeJsonl(LOCKS_FILE, locks);
  }

  writeJsonl(QUEUE_FILE, tasks);
  console.log(`[UPDATED] ${taskId} -> ${newStatus}`);
  return tasks[idx];
}

function listBlocked() {
  const tasks = readJsonl(QUEUE_FILE);
  const doneIds = new Set(tasks.filter((t) => t.status === "done").map((t) => t.id));

  const blocked = tasks.filter(
    (t) => t.status === "queued" && t.dependsOn.length > 0 && !t.dependsOn.every((dep) => doneIds.has(dep))
  );

  if (blocked.length === 0) {
    console.log("[BLOCKED] No blocked tasks.");
  } else {
    console.log(`[BLOCKED] ${blocked.length} task(s) blocked:`);
    blocked.forEach((t) => {
      const missing = t.dependsOn.filter((d) => !doneIds.has(d));
      console.log(`  ${t.id}: waiting on ${missing.join(", ")}`);
    });
  }
  return blocked;
}

function listAll() {
  const tasks = readJsonl(QUEUE_FILE);
  if (tasks.length === 0) {
    console.log("[QUEUE] Empty.");
  } else {
    console.log(`[QUEUE] ${tasks.length} task(s):`);
    tasks.forEach((t) => console.log(`  ${t.id} [${t.status}] [${t.priority}] ${t.agent}: ${t.task}`));
  }
  return tasks;
}

// --- CLI ---
const [, , cmd, ...args] = process.argv;

function parseArgs(args) {
  const result = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith("--")) {
      const key = args[i].slice(2);
      const val = args[i + 1] && !args[i + 1].startsWith("--") ? args[++i] : true;
      if (key === "dependsOn" || key === "affectedFiles") {
        result[key] = String(val).split(",").filter(Boolean);
      } else {
        result[key] = val;
      }
    }
  }
  return result;
}

switch (cmd) {
  case "enqueue":
    enqueue(parseArgs(args));
    break;
  case "dispatch":
    dispatch();
    break;
  case "update":
    updateStatus(args[0], args[1]);
    break;
  case "blocked":
    listBlocked();
    break;
  case "list":
    listAll();
    break;
  default:
    console.log(`Usage: bus.js <command>
Commands:
  enqueue  --agent <name> --task <desc> [--priority high] [--source human] [--dependsOn id1,id2] [--affectedFiles f1,f2]
  dispatch                  Show tasks ready to execute
  update   <id> <status>    Update task status (queued|locked|running|done|failed)
  blocked                   Show blocked tasks
  list                      Show all tasks`);
}
