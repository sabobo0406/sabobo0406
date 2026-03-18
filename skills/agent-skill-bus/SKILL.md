---
name: agent-skill-bus
emoji: "\U0001F40D"
description: "Ouroboros: Orchestrates AI agent task management by integrating Prompt Request Bus, Self-Improving Skills, and Knowledge Watcher into a unified self-improving closed loop."
user-invocable: true
requires:
  bins:
    - node
---

# Agent Skill Bus

A unified orchestrator that integrates the three core modules of the Agent Skill Bus framework into a closed-loop system for AI agent task management and self-improvement.

## When to Use

Use this skill when the user wants to:
- Run the full agent task lifecycle (queue -> execute -> record -> improve)
- Get an overview of the entire system status
- Orchestrate tasks across multiple agents
- Run the self-improvement loop end-to-end

## Architecture Overview

```
                    +-------------------+
                    |  Knowledge Watcher |
                    |  (External Changes)|
                    +--------+----------+
                             |
                             v triggers
+------------------+    +-----------+    +---------------------+
| Prompt Request   |--->| Agent     |--->| Self-Improving      |
| Bus (Task Queue) |    | Execution |    | Skills (Quality)    |
+------------------+    +-----------+    +---------------------+
        ^                                         |
        |              feedback loop              |
        +-----------------------------------------+
```

The three modules form a closed loop:
1. **Prompt Request Bus** queues and dispatches tasks
2. **Agents** execute tasks and produce results
3. **Self-Improving Skills** monitors quality and proposes fixes
4. **Knowledge Watcher** detects external changes and queues adaptation tasks
5. Improvements feed back into the queue as new tasks

## Orchestration Commands

### System Status

Show the overall health of the Agent Skill Bus system:

1. Run `node {baseDir}/../prompt-request-bus/bus.js list` to get queue status
2. Run `node {baseDir}/../prompt-request-bus/bus.js dispatch` to show ready tasks
3. Run `node {baseDir}/../knowledge-watcher/watcher.js list --status new` to show new diffs
4. Summarize: total queued, ready, blocked, running tasks; unresolved knowledge diffs

### Full Task Lifecycle

When the user wants to process a task end-to-end:

1. **Enqueue**: Use prompt-request-bus to add the task
   ```bash
   node {baseDir}/../prompt-request-bus/bus.js enqueue --agent <agent> --task "<desc>" --priority <priority>
   ```

2. **Dispatch**: Check if the task is ready (dependencies resolved)
   ```bash
   node {baseDir}/../prompt-request-bus/bus.js dispatch
   ```

3. **Lock & Execute**: Update task to running status
   ```bash
   node {baseDir}/../prompt-request-bus/bus.js update <task-id> running
   ```

4. **Record Result**: After execution, record the outcome
   ```bash
   node {baseDir}/../self-improving-skills/improve.js record --agent <agent> --skill <skill> --task "<desc>" --result <success|failure> --score <0.0-1.0>
   ```

5. **Complete**: Mark the task as done or failed
   ```bash
   node {baseDir}/../prompt-request-bus/bus.js update <task-id> <done|failed>
   ```

6. **Analyze**: Check if the skill needs improvement
   ```bash
   node {baseDir}/../self-improving-skills/improve.js analyze <skill>
   ```

### Self-Improvement Loop

Run the complete OBSERVE -> ANALYZE -> DIAGNOSE -> PROPOSE cycle:

1. Analyze skill health for all active skills
2. For any skill in `warning` or `critical` state:
   a. Run diagnosis
   b. Generate proposals
   c. Auto-apply low-risk improvements
   d. Report high-risk proposals for human review
3. Record all applied improvements

### Knowledge-Driven Updates

When external changes are detected:

1. Run `watcher.js scan` to detect dependency changes
2. For each high-impact diff:
   a. Identify affected skills
   b. Auto-enqueue adaptation tasks into the Prompt Request Bus
   c. Set appropriate priority based on impact level

## Data Files

All data is stored as plain JSONL in the `data/` directory:

| File | Module | Content |
|---|---|---|
| `queue.jsonl` | Prompt Request Bus | Task queue |
| `active-locks.jsonl` | Prompt Request Bus | File locks |
| `skill-runs.jsonl` | Self-Improving Skills | Execution history |
| `improvements.jsonl` | Self-Improving Skills | Applied improvements |
| `knowledge-diffs.jsonl` | Knowledge Watcher | Detected changes |
| `dep-baseline.json` | Knowledge Watcher | Dependency baseline |

## Usage Examples

User: "Show me the system status"
Action: Run system status across all modules

User: "Process the next task"
Action: Dispatch highest priority ready task, execute lifecycle

User: "Run the improvement loop"
Action: Analyze all skills, diagnose issues, propose and apply fixes

User: "Check for external changes and adapt"
Action: Scan for changes, enqueue adaptation tasks

User: "Give me a daily report"
Action: Combine queue status + skill health + knowledge diffs into report
