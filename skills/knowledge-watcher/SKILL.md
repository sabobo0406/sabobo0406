---
name: knowledge-watcher
emoji: "\U0001F441"
description: Monitors external changes across three tiers (immediate, daily, weekly) and triggers improvement workflows for AI agent skills.
user-invocable: true
requires:
  bins:
    - node
---

# Knowledge Watcher

Monitors external changes (dependency updates, API changes, community patterns, industry trends) and triggers skill improvement workflows when relevant changes are detected.

## When to Use

Use this skill when the user wants to:
- Check for dependency or API changes that may affect agent skills
- Monitor community patterns and best practices
- Track industry trends and competitor updates
- View detected knowledge diffs
- Trigger improvement workflows based on external changes

## Three-Tier Monitoring

### Tier 1 - Immediate (Continuous)
- Dependency version changes (package.json, requirements.txt, etc.)
- API endpoint changes or deprecations
- Configuration drift from baseline

### Tier 2 - Daily
- Community pattern changes (popular libraries, common approaches)
- User feedback aggregation
- Platform update announcements

### Tier 3 - Weekly
- Industry trend analysis
- Competitor feature releases
- Emerging best practices

## Data Format

Knowledge diffs are stored in `{baseDir}/../../data/knowledge-diffs.jsonl`:

```json
{
  "id": "kd-001",
  "ts": "2026-03-18T10:00:00Z",
  "tier": 1,
  "category": "dependency",
  "source": "package.json",
  "summary": "express updated from 4.18.2 to 4.19.0",
  "impact": "medium",
  "affectedSkills": ["api-handler", "server-setup"],
  "status": "new",
  "action": null
}
```

### Fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique identifier (format: `kd-XXX`) |
| `ts` | ISO 8601 | Detection timestamp |
| `tier` | number | Monitoring tier (1, 2, or 3) |
| `category` | string | `dependency`, `api`, `config`, `community`, `platform`, `industry`, `competitor` |
| `source` | string | Where the change was detected |
| `summary` | string | Human-readable description of the change |
| `impact` | string | `low`, `medium`, `high`, `critical` |
| `affectedSkills` | string[] | Skills potentially affected by this change |
| `status` | string | `new`, `acknowledged`, `acted`, `dismissed` |
| `action` | string/null | Action taken (links to improvement ID if applicable) |

## Implementation Steps

### Record a Knowledge Diff

1. Read `data/knowledge-diffs.jsonl` (create if not exists)
2. Generate unique ID: `kd-XXX`
3. Validate tier (1, 2, or 3) and category
4. Append the diff record
5. If `impact` is `high` or `critical`, immediately alert the user

### Scan for Changes (Tier 1)

1. Read project's `package.json` (or equivalent dependency file)
2. Compare current dependency versions against a stored baseline
3. For each changed dependency:
   - Record a knowledge diff with category `dependency`
   - Assess impact based on semver change type (major=high, minor=medium, patch=low)
   - Map affected skills based on which skills use the dependency
4. Check for API config changes in relevant config files
5. Output a summary of all detected changes

### Review Knowledge Diffs

1. Read all diffs from `data/knowledge-diffs.jsonl`
2. Filter by status (default: `new`)
3. Group by tier and sort by impact
4. Display grouped summary
5. For each `high`/`critical` diff, suggest immediate action

### Acknowledge / Act on Diffs

1. Find the diff by ID
2. Update status to `acknowledged` or `acted`
3. If `acted`, link to the improvement ID from self-improving-skills
4. Rewrite the diffs file

### Generate Monitoring Report

1. Read all diffs from the specified time period
2. Group by tier and category
3. Calculate:
   - Total diffs per tier
   - Unresolved high/critical items
   - Average time to act
4. Display the report

## Usage Examples

User: "Check for dependency changes"
Action: Run Tier 1 scan, record diffs, display summary

User: "Show me new knowledge diffs"
Action: Filter and display status=new diffs grouped by tier

User: "Acknowledge kd-005"
Action: Update diff status to acknowledged

User: "What external changes might affect our code-review skill?"
Action: Filter diffs by affectedSkills containing "code-review"

User: "Generate a monitoring report for this week"
Action: Run report for the past 7 days
