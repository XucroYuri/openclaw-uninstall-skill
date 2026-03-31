---
name: openclaw-safe-uninstall
description: Use when an agent must uninstall OpenClaw from a local machine with high safety requirements, especially when the host may contain macOS launchd, Linux systemd, Windows Scheduled Task or Startup-folder installs, multiple OpenClaw profiles, shell injection, source-checkout wrappers, or misleading non-target artifacts that must not be deleted automatically.
---

# OpenClaw Safe Uninstall

## Overview

This skill performs high-risk local OpenClaw uninstall work through a strict sequence:

1. scan
2. plan
3. explicit human approval
4. apply
5. verify

Do not jump straight to deletion.

Use the deterministic helper script in [scripts/openclaw_uninstall.py](scripts/openclaw_uninstall.py) instead of ad-hoc `rm -rf` unless the user explicitly wants a manual one-off cleanup.

## Hard boundaries

- Never auto-delete anything under `.codex/skills` or `.agents/skills`.
- Never auto-delete anything under protected AI tooling roots such as `.claude/skills`, `.claude/agents`, `.claude/commands`, `.gemini/commands`, `.opencode/skills`, or `.config/opencode/skills`.
- Never treat `openclaw` in a path string as sufficient deletion evidence by itself.
- Known companion traces such as `AutoClaw` must be reported as `manual_review`, not auto-deleted.
- Require explicit user intent before `apply`.
- Require all three apply flags:
  - `--yes`
  - `--acknowledge-risk`
  - `--confirm "REMOVE OPENCLAW FROM THIS MACHINE"`
- If root-owned artifacts remain, report exact manual commands rather than claiming success.

## Required workflow

### Step 1: Scan

Run:

```bash
python3 scripts/openclaw_uninstall.py scan --json
```

Review:

- detected state directories
- service registrations
- CLI/package installs
- shell injection
- manual review artifacts
- excluded paths

### Step 2: Build the uninstall plan

Run:

```bash
python3 scripts/openclaw_uninstall.py plan --json
```

Explain:

- what will be deleted automatically
- what requires privilege
- what is intentionally excluded
- what remains manual review only

### Step 3: Apply only with explicit approval

Run:

```bash
python3 scripts/openclaw_uninstall.py apply \
  --yes \
  --acknowledge-risk \
  --confirm "REMOVE OPENCLAW FROM THIS MACHINE" \
  --json
```

If the user wants rehearsal first, add `--dry-run`.

### Step 4: Verify

Run:

```bash
python3 scripts/openclaw_uninstall.py verify --json
```

Summarize:

- removed artifacts
- remaining privileged artifacts
- remaining manual review artifacts
- exact next-step commands if anything remains

## Platform notes

- macOS:
  - detect LaunchAgents like `ai.openclaw.gateway`, `ai.openclaw.<profile>`, and legacy `com.openclaw.*`
  - detect shell completion injection
  - detect optional app bundle paths
- Linux:
  - detect `systemd --user` units such as `openclaw-gateway[-<profile>].service`
  - detect legacy unit names like `clawdbot-gateway` and `moltbot-gateway`
  - detect wrapper installs and global package paths
- Windows:
  - detect Scheduled Task naming conventions
  - detect Startup-folder fallback launchers
  - detect `gateway.cmd` and `node.cmd` in the state dir
- Neighboring AI tooling ecosystems:
  - protect Claude Code subagent/custom-command directories
  - protect Gemini CLI custom-command directories
  - protect OpenCode skill directories and compatibility skill roots

## References

- [references/research-notes.md](references/research-notes.md)
- [references/artifact-matrix.md](references/artifact-matrix.md)
- [references/safety-model.md](references/safety-model.md)

## Validation

Before you claim the uninstall plan is correct, run:

```bash
python3 -m unittest discover -s tests -v
```
