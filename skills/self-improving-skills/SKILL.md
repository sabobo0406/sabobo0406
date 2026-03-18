---
name: self-improving-skills
emoji: "\U0001F504"
description: Seven-step quality loop (OBSERVE-ANALYZE-DIAGNOSE-PROPOSE-EVALUATE-APPLY-RECORD) for automatic failure detection, LLM-powered diagnosis, and self-repair of AI agent skills.
user-invocable: true
requires:
  bins:
    - node
---

# Self-Improving Skills

A seven-step quality loop that monitors agent skill execution, detects failures and performance degradation, diagnoses root causes, and applies safe auto-repairs.

## When to Use

Use this skill when the user wants to:
- Record an agent skill execution result (success/failure with a score)
- Analyze skill performance trends and detect degradation
- Diagnose why a skill is failing or declining in quality
- Propose and apply improvements to a skill
- View the improvement history of a skill

## The Seven-Step Quality Loop

```
OBSERVE -> ANALYZE -> DIAGNOSE -> PROPOSE -> EVALUATE -> APPLY -> RECORD
```

1. **OBSERVE** - Record execution results (agent, skill, task, result, score 0.0-1.0)
2. **ANALYZE** - Detect score drops, trends, and anomalies over a rolling window
3. **DIAGNOSE** - Identify root cause using pattern matching and LLM reasoning
4. **PROPOSE** - Generate improvement candidates (prompt changes, parameter tweaks, workflow adjustments)
5. **EVALUATE** - Assess risk level of each proposal (low/medium/high)
6. **APPLY** - Auto-apply low-risk fixes; flag high-risk for human approval
7. **RECORD** - Log the improvement action and its outcome for future learning

## Data Format

Execution records are stored in `{baseDir}/../../data/skill-runs.jsonl`:

```json
{
  "id": "sr-001",
  "ts": "2026-03-18T08:30:00Z",
  "agent": "dev-agent",
  "skill": "code-review",
  "task": "Review PR #42",
  "result": "success",
  "score": 0.85,
  "duration": 120,
  "meta": {}
}
```

Improvement records are stored in `{baseDir}/../../data/improvements.jsonl`:

```json
{
  "id": "imp-001",
  "ts": "2026-03-18T09:00:00Z",
  "skill": "code-review",
  "step": "APPLY",
  "diagnosis": "Prompt too vague for edge cases",
  "action": "Added explicit edge case handling instructions",
  "riskLevel": "low",
  "approved": true,
  "scoreBefore": 0.65,
  "scoreAfter": null
}
```

## Implementation Steps

### Record a Run (OBSERVE)

1. Read `data/skill-runs.jsonl` (create if not exists)
2. Generate unique ID: `sr-XXX`
3. Append the run record with timestamp, agent, skill, task, result, score
4. Output confirmation

### Analyze Skill Health (ANALYZE)

1. Read all runs from `data/skill-runs.jsonl`
2. Filter runs for the specified skill
3. Calculate over a rolling window (default: last 20 runs):
   - Average score
   - Score trend (improving / stable / declining)
   - Failure rate (percentage of `result !== "success"`)
   - Week-over-week score change
4. **Drift Detection**: Flag if week-over-week decline exceeds 15%
5. Display health report with status: `healthy`, `warning`, `critical`

Thresholds:
- `healthy`: avg score >= 0.8, failure rate < 10%
- `warning`: avg score >= 0.6, failure rate < 30%
- `critical`: avg score < 0.6 OR failure rate >= 30% OR drift > 15%

### Diagnose Issues (DIAGNOSE)

When a skill is in `warning` or `critical` state:

1. Gather the last 10 failed runs for the skill
2. Look for common patterns:
   - Same error messages
   - Specific task types that fail more often
   - Time-of-day patterns
   - Duration anomalies (unusually long runs)
3. Summarize the likely root cause
4. Output diagnosis with confidence level

### Propose Improvements (PROPOSE)

Based on diagnosis, generate improvement proposals:

1. For each identified issue, create a proposal with:
   - Description of the change
   - Expected impact
   - Risk level: `low` (parameter tweak), `medium` (prompt change), `high` (workflow restructure)
2. Sort proposals by risk level (low first)
3. Display proposals for review

### Apply Improvements (EVALUATE + APPLY)

1. For `low` risk proposals: apply automatically and log to `data/improvements.jsonl`
2. For `medium` risk proposals: show diff/change preview, ask for confirmation
3. For `high` risk proposals: always require explicit human approval
4. After applying, record the improvement with `scoreBefore`

### Track Improvement History (RECORD)

1. Read `data/improvements.jsonl`
2. For recent improvements, check if subsequent runs show score changes
3. Update `scoreAfter` when enough post-improvement data is available
4. Display improvement effectiveness report

## Usage Examples

User: "Record that dev-agent's code-review skill scored 0.7 on PR #42"
Action: Append run record to skill-runs.jsonl

User: "How is the code-review skill performing?"
Action: Run ANALYZE, show health report

User: "Why is code-review failing so much?"
Action: Run DIAGNOSE on the skill

User: "Suggest improvements for code-review"
Action: Run PROPOSE, show ranked improvement proposals

User: "Show improvement history"
Action: Display improvements.jsonl with effectiveness data
