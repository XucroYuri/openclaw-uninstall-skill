# Artifact Matrix

## Official auto-delete candidates

| Category | Examples | Default action |
| --- | --- | --- |
| State dirs | `~/.openclaw`, `~/.openclaw-dev`, `~/.openclaw-<profile>` | Delete after confirmation |
| macOS LaunchAgents | `~/Library/LaunchAgents/ai.openclaw.gateway.plist` | Bootout if possible, then delete |
| Linux user units | `~/.config/systemd/user/openclaw-gateway.service` | Disable/stop if possible, then delete |
| Windows task scripts | `%USERPROFILE%\.openclaw\gateway.cmd` | Delete after `schtasks /Delete` attempt |
| Windows Startup fallback | `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\OpenClaw Gateway.cmd` | Delete |
| CLI wrappers | `/usr/local/bin/openclaw`, `~/.local/bin/openclaw` | Delete if removable |
| Package dirs | `/usr/local/lib/node_modules/openclaw` | Delete if removable |
| Git checkout | `~/openclaw` or explicit `--git-dir` | Delete only when confirmed |
| Shell injections | `source ".../.openclaw/completions/openclaw.zsh"` | Edit surgically with backup |
| macOS app bundle | `/Applications/OpenClaw.app` | Delete if present |

## Manual-review-only candidates

| Category | Examples | Why manual review |
| --- | --- | --- |
| Companion app traces | `AutoClaw.app`, `autoclaw` app support | Not part of official OpenClaw uninstall docs |
| Browser bridges from companion apps | `com.autoclaw.native_host_stub.json` | Adjacent ecosystem artifact, not official OpenClaw core |
| Codex skill folders | `.codex/skills/openclaw-openclaw-obsidian` | Name collision does not imply uninstall target |
| Claude Code / Gemini CLI / OpenCode extension roots | `.claude/agents/openclaw-helper.md`, `.gemini/commands/openclaw.toml`, `.opencode/skills/openclaw-guard/` | Neighboring AI tooling customization must never be swept by OpenClaw uninstall |
| Custom state override without OpenClaw marker | `~/Documents/agent-state` from `OPENCLAW_STATE_DIR` | Too risky to auto-delete because it may not be a dedicated OpenClaw directory |

## Explicit exclusions

- `.codex/skills/**`
- `.agents/skills/**`
- `.claude/skills/**`
- `.claude/agents/**`
- `.claude/commands/**`
- `.gemini/commands/**`
- `.opencode/skills/**`
- `.config/opencode/skills/**`
- arbitrary docs, notes, backups, or reports that merely mention OpenClaw
- any path discovered only by substring matching without a supported install-path rule
