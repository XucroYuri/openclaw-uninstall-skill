# OpenClaw Uninstall Research Notes

Date: 2026-03-31

This project intentionally encodes only uninstall behavior supported by either official OpenClaw documentation or direct inspection of the installed `openclaw` package, plus one extra safety lesson from real local cleanup work: not every suspicious path should be auto-deleted.

## Official findings

### Built-in uninstaller exists, but CLI may remain

Official uninstall docs recommend:

- `openclaw uninstall`
- `openclaw uninstall --all --yes --non-interactive`

The same guide explicitly states that the CLI install may still need separate removal depending on install method.

Sources:

- https://docs.openclaw.ai/install/uninstall
- local package copy: `docs/install/uninstall.md`

### Install methods materially change uninstall traces

Official installer docs distinguish:

- global package install via `npm` by default
- git/source checkout install that places a wrapper at `~/.local/bin/openclaw`
- Windows PowerShell git install that places a wrapper at `%USERPROFILE%\.local\bin\openclaw.cmd`

Sources:

- https://docs.openclaw.ai/install/installer
- local package copy: `docs/install/installer.md`

### Service supervisors vary by OS

Official docs and shipped constants show:

- macOS LaunchAgent:
  - `ai.openclaw.gateway`
  - `ai.openclaw.<profile>`
  - legacy `com.openclaw.*`
- Linux systemd user unit:
  - `openclaw-gateway.service`
  - `openclaw-gateway-<profile>.service`
  - legacy `clawdbot-gateway`, `moltbot-gateway`
- Windows:
  - task name `OpenClaw Gateway`
  - task name `OpenClaw Gateway (<profile>)`
  - fallback to Startup-folder login item when Scheduled Task creation is denied

Sources:

- https://docs.openclaw.ai/gateway
- https://docs.openclaw.ai/platforms/macos
- local package copy: `dist/constants-yobxBGxY.js`
- local package copy: `dist/service-6gftUGdu.js`

### State is profile-sensitive

Official docs explicitly document:

- default state dir: `~/.openclaw`
- dev state dir: `~/.openclaw-dev`
- named profiles: `~/.openclaw-<profile>`
- state override: `OPENCLAW_STATE_DIR`
- config override: `OPENCLAW_CONFIG_PATH`

This means uninstall tooling must scan more than a single `~/.openclaw` path.

Sources:

- https://docs.openclaw.ai/help/faq
- https://docs.openclaw.ai/gateway/multiple-gateways
- local package copies in `docs/help/faq.md` and `docs/gateway/multiple-gateways.md`

### Windows fallback writes both a task script and a Startup-folder launcher

Direct package inspection shows:

- task script default path: `$OPENCLAW_STATE_DIR/gateway.cmd`
- Startup-folder fallback path:
  - `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\<task-name>.cmd`

Source:

- local package copy: `dist/service-6gftUGdu.js`

## Real-world local cleanup lesson

On one local uninstall, additional traces appeared:

- `~/.openclaw-autoclaw`
- `~/Library/Application Support/autoclaw`
- `~/Library/Preferences/com.zhipuai.autoclaw.plist`
- Chrome native host file for `com.autoclaw.native_host_stub.json`

These were not part of the official OpenClaw docs or package constants. They behaved more like a companion app or distribution shell around OpenClaw.

That led to one core design rule in this repo:

- companion or adjacent artifacts are reported as `manual_review`
- they are not included in default auto-delete operations

## Resulting design rules

- Official OpenClaw traces: eligible for auto-delete when confirmed
- Legacy official traces: eligible for auto-delete when confirmed
- Companion-app traces: detect and report, but do not auto-delete
- Codex/OpenCode skills with `openclaw` in the folder name: excluded from uninstall scope
