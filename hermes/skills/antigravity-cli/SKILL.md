---
name: antigravity-cli
description: "Operate the Antigravity CLI (agy): plugins, auth, sandbox, and delegation."
version: 0.2.0
author: Tony Simons (asimons81), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, Antigravity, CLI, Auth, Plugins, Sandbox]
    related_skills: [grok, codex, claude-code, hermes-agent]
---

# Antigravity CLI (`agy`)

Operator guide for the Antigravity CLI, invoked as `agy`. Run all `agy`
commands through the Hermes `terminal` tool; inspect its config and logs with
`read_file`. This skill is reference + procedure — it does not wrap a network
API, so there is nothing to authenticate from Hermes itself.

## When to Use

- Installing, updating, or smoke-testing the `agy` binary
- Driving non-interactive `agy --print` / `agy -p` one-shots
- Debugging Antigravity auth, sandbox, permissions, or plugin state
- Reading Antigravity settings, keybindings, conversations, or logs
- Delegating coding, architecture review, and multi-file code tasks to Antigravity

## Mental Model

Antigravity has two layers — keep them distinct or the guidance will be wrong:

1. **Shell wrapper commands** — `agy help`, `agy install`, `agy plugin`,
   `agy update`, `agy changelog`, `agy models`. Run these through the `terminal` tool.
2. **Interactive in-session slash commands** — `/config`, `/permissions`,
   `/skills`, `/agents`, etc. These only exist inside a running `agy` TUI
   session, not on the shell wrapper.

`agy help` shows the shell wrapper surface, NOT the in-session slash commands.

## Prerequisites

- The `agy` binary on PATH (`/usr/local/bin/agy`). Verify through the `terminal` tool:
  `command -v agy && agy --version`.
- No env vars or API keys required by this skill — Antigravity manages its own
  auth via the OS keyring / browser sign-in cached under `~/.gemini/antigravity-cli/`
  (persisted on `/opt/data/.gemini`).

## How to Run

Invoke every `agy` command through the `terminal` tool. Examples:

```bash
terminal(command="agy --version")
terminal(command="agy help")
terminal(command="agy plugin list")
terminal(command="agy --print 'Summarize the repo in 3 bullets'", workdir="/path/to/project")
```

For one-shot smoke tests and scripted prompts, prefer `agy --print` (or `-p`) non-interactive.

## Delegation Patterns

`agy` is a coding-agent backend in the same family as `codex` / `claude-code`,
so the same delegation shapes apply. Use these when handing real work (features,
fixes, reviews, second opinions) to Antigravity rather than just smoke-testing.

### One-shot (preferred for scripted prompts and second opinions)

```bash
terminal(command="agy -p 'Review this diff for bugs and security issues' --model 'Gemini 3.1 Pro (High)'", workdir="/path/to/repo", timeout=300)
```

`-p` is non-interactive: it runs the prompt and exits. Pick the engine with
`--model` (run `agy models` for the exact display strings, e.g.
`'Gemini 3.1 Pro (High)'`, `'Claude Opus 4.6 (Thinking)'`). Add extra context
roots with repeatable `--add-dir`.

### Bounded runs (tests, builds, multi-file changes)

Always pass `--dangerously-skip-permissions` to prevent interactive approval pauses:

```bash
terminal(command="agy -p 'Implement the requested change and verify tests pass' --dangerously-skip-permissions", workdir="/path/to/repo")
```

## Core Paths (Persisted on Volume)

- App data dir: `~/.gemini/antigravity-cli/` (symlinked to `/opt/data/.gemini/antigravity-cli/`)
- Settings file: `~/.gemini/antigravity-cli/settings.json`
- Logs: `~/.gemini/antigravity-cli/log/cli-*.log`
- Conversations: `~/.gemini/antigravity-cli/conversations/`
- History: `~/.gemini/antigravity-cli/history.jsonl`
