---
name: prompt-request-bus
emoji: "\U0001F4EC"
description: JSONL-based task queue with DAG dependency resolution, file-level locking, priority routing, and deduplication for AI agent orchestration.
user-invocable: true
requires:
  bins:
    - node
    - jq
---

# Prompt Request Bus

A JSONL-based task queue that manages AI agent task orchestration with DAG dependency resolution, file-level locking, and priority routing.

## When to Use

Use this skill when the user wants to:
- Queue a new task for an AI agent
- View pending or ready-to-dispatch tasks
- Check task status or dependencies
- Manage the task queue (enqueue, dequeue, prioritize)
- Resolve task dependencies using DAG

## Data Format

All tasks are stored in `{baseDir}/../../data/queue.jsonl`. Each line is a JSON object:

```json
{
  "id": "pr-001",
  "ts": "2026-03-18T08:00:00Z",
  "source": "human",
  "priority": "high",
  "agent": "dev-agent",
  "task": "Fix authentication bug in auth.ts",
  "status": "queued",
  "dependsOn": [],
  "affectedFiles": ["src/auth.ts"],
  "dagId": null
}
```

### Fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique task identifier (format: `pr-XXX`) |
| `ts` | ISO 8601 | Timestamp of task creation |
| `source` | string | Origin: `human`, `cron`, `webhook`, `agent` |
| `priority` | string | One of: `critical`, `high`, `medium`, `low` |
| `agent` | string | Target agent name |
| `task` | string | Task description |
| `status` | string | One of: `queued`, `locked`, `running`, `done`, `failed` |
| `dependsOn` | string[] | Array of task IDs this task depends on |
| `affectedFiles` | string[] | Files this task will modify |
| `dagId` | string/null | DAG group identifier for linked tasks |

## Implementation Steps

### Enqueue a Task

1. Read the current `data/queue.jsonl` file (create if not exists)
2. Generate a unique ID by finding the highest existing `pr-XXX` number and incrementing
3. Check for duplicates: if same `agent` + `task` + `status=queued` exists, skip and inform user
4. Check for file lock conflicts: if any `affectedFiles` overlap with a `locked` or `running` task, warn the user
5. Append the new task as a single JSON line to `data/queue.jsonl`
6. Output confirmation with the task ID

### Dispatch (View Ready Tasks)

1. Read all tasks from `data/queue.jsonl`
2. Filter tasks where `status` is `queued`
3. For each queued task, check if ALL `dependsOn` task IDs have `status: done`
4. Sort ready tasks by priority: `critical` > `high` > `medium` > `low`
5. Display the sorted list of ready-to-execute tasks

### Update Task Status

1. Read `data/queue.jsonl`
2. Find the task by ID
3. Update the `status` field
4. If setting to `locked` or `running`, create a lock entry in `data/active-locks.jsonl`:
   ```json
   {"taskId": "pr-001", "files": ["src/auth.ts"], "lockedAt": "2026-03-18T08:00:00Z", "ttl": 3600}
   ```
5. If setting to `done` or `failed`, remove corresponding lock entries
6. Rewrite the full `data/queue.jsonl` with the updated task

### Lock Management

- Before any file modification, check `data/active-locks.jsonl` for conflicts
- Locks have a TTL (default: 3600 seconds). Expired locks are automatically cleared
- If a lock conflict exists, report which task holds the lock and its remaining TTL

## Priority Routing Order

Always process tasks in this order:
1. `critical` - Security incidents, production outages
2. `high` - Bugs, urgent features
3. `medium` - Standard tasks (default)
4. `low` - Refactoring, documentation

## Usage Examples

User: "Queue a high priority task for dev-agent to fix the login bug"
Action: Enqueue with priority=high, agent=dev-agent

User: "Show me what tasks are ready to run"
Action: Run dispatch logic, show ready tasks

User: "Mark task pr-005 as done"
Action: Update status, clear locks

User: "What tasks are blocked?"
Action: Show queued tasks whose dependencies are not all done
