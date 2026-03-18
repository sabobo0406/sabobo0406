- 👋 Hi, I’m @sabobo0406
- 👀 I’m interested in AI and medicine.
- 🌱 I’m currently learning AI
- 💞️ I’m looking to collaborate on making Ai to improve womens health
- 📫 How to reach me DM me on instagram
- 😄 Pronouns: ...
- ⚡ Fun fact: ...

## Ouroboros - OpenClaw Sub-Agent

Self-improving task orchestration sub-agent for AI agent systems, powered by [agent-skill-bus](https://github.com/ShunsukeHayashi/agent-skill-bus).
Like the serpent that devours its own tail, Ouroboros forms an eternal closed loop of execution, monitoring, and self-improvement.

### Skills

| Skill | Description |
|---|---|
| `prompt-request-bus` | JSONL-based task queue with DAG dependency resolution, file locking, and priority routing |
| `self-improving-skills` | 7-step quality loop (OBSERVE->ANALYZE->DIAGNOSE->PROPOSE->EVALUATE->APPLY->RECORD) |
| `knowledge-watcher` | External change monitoring across 3 tiers (immediate/daily/weekly) |
| `agent-skill-bus` | Unified orchestrator integrating all modules into a closed-loop system |

### Quick Start

```bash
# Enqueue a task
node skills/prompt-request-bus/bus.js enqueue --agent dev-agent --task "Fix login bug" --priority high

# View ready tasks
node skills/prompt-request-bus/bus.js dispatch

# Record a skill execution
node skills/self-improving-skills/improve.js record --agent dev-agent --skill code-review --task "Review PR" --result success --score 0.85

# Check skill health
node skills/self-improving-skills/improve.js analyze code-review

# Scan for dependency changes
node skills/knowledge-watcher/watcher.js scan ./package.json

# View knowledge diffs
node skills/knowledge-watcher/watcher.js list --status new
```

### Directory Structure

```
AGENTS.md                         # Sub-agent delegation rules
openclaw.json                     # Agent configuration
.agents/ouroboros/                 # Ouroboros sub-agent
├── soul.md                       #   Identity & response format
└── agent.md                      #   Module instructions
skills/
├── agent-skill-bus/              # Orchestrator skill
│   └── SKILL.md
├── prompt-request-bus/           # Task queue
│   ├── SKILL.md
│   └── bus.js
├── self-improving-skills/        # Quality loop
│   ├── SKILL.md
│   └── improve.js
└── knowledge-watcher/            # Change monitoring
    ├── SKILL.md
    └── watcher.js
data/                             # JSONL data files (auto-created)
```

<!---
sabobo0406/sabobo0406 is a ✨ special ✨ repository because its `README.md` (this file) appears on your GitHub profile.
You can click the Preview link to take a look at your changes.
--->
