# CLAUDE.md

Guidance for AI assistants (e.g. Claude Code) working in this repository.

## Repository purpose

This is a **GitHub profile repository**: `sabobo0406/sabobo0406`. Because the repo name matches the GitHub username, `README.md` is rendered on the owner's public GitHub profile page (https://github.com/sabobo0406). There is no application code, build system, package manager, or test suite — the deliverable is the rendered Markdown.

Owner context (from the README):
- Interested in AI and medicine
- Currently learning AI
- Looking to collaborate on AI for women's health

## Structure

```
.
├── README.md   # Rendered on the GitHub profile page
└── CLAUDE.md   # This file
```

That's the whole repo. Do not introduce build tooling, CI configs, package manifests, or source directories unless the user explicitly asks for them.

## Working in this repo

### Editing `README.md`
- Keep it GitHub-flavored Markdown — GitHub renders it directly with no preprocessor.
- Preserve the HTML comment block at the bottom (`<!--- ... --->`); it's the default template note and harmless.
- Emojis are part of the existing style. Match the tone of the surrounding lines when adding bullets; otherwise follow the global rule of not introducing emojis.
- Images, badges, and GitHub stats widgets are fine if requested, but reference only external URLs the user provides — don't invent URLs.
- Anything visible on the profile must be public-safe. No emails, phone numbers, addresses, or other personal contact info beyond what the user has already chosen to publish.

### What not to do
- Don't create new top-level files (LICENSE, .gitignore, package.json, workflows, etc.) unless asked. This repo is intentionally minimal.
- Don't reformat the existing README into a different structure (e.g. tables, sections, badges) without explicit instruction — the bullet style is the user's choice.
- Don't push to `main` directly. Use the branch specified in the task instructions and open a PR.

## Git workflow

- Default branch: `main`.
- Feature work happens on task-specified branches (e.g. `claude/<topic>-<id>`). Create the branch locally if it doesn't exist.
- Push with `git push -u origin <branch-name>`; on network failure, retry with exponential backoff (2s, 4s, 8s, 16s) up to 4 times.
- After pushing, open a **draft** PR against `main` if one doesn't already exist.
- Never force-push to `main`. Never skip hooks (`--no-verify`) unless the user explicitly asks.

## Verification

There is nothing to build, lint, or test. To "verify" a README change:
1. Confirm the diff is what was intended (`git diff`).
2. Mentally render the Markdown — check that headings, bullets, links, and images parse correctly.
3. If the change includes external links or images, note in the PR description that GitHub will render them on the live profile; the user should eyeball the rendered result after merging.

## GitHub integration (this environment)

- Use `mcp__github__*` tools for any GitHub interaction (PRs, comments, file ops). The `gh` CLI is **not** available.
- Repository scope is restricted to `sabobo0406/sabobo0406`; do not try to read or write other repos.
- Be frugal with PR comments — comment only when genuinely necessary.
