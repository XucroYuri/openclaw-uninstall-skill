# openclaw-uninstall-skill

[![CI](https://github.com/XucroYuri/openclaw-uninstall-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/XucroYuri/openclaw-uninstall-skill/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-informational)](#development)
[![Template Repository](https://img.shields.io/badge/github-template-success)](https://github.com/XucroYuri/openclaw-uninstall-skill/generate)

**Languages:** [English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [Español](README.es.md)

High-safety Agent Skill and validation toolkit for removing OpenClaw from macOS, Linux, and Windows without turning a machine cleanup into a blind destructive sweep.

> This repository is intentionally conservative.
> The default workflow is always:
> `scan -> plan -> explicit approval -> apply -> verify`

## At a glance

| Topic | What this repo does |
| --- | --- |
| Scope | Detects and removes official OpenClaw install traces |
| Safety posture | Refuses to apply destructive actions without a strong confirmation phrase |
| Platform coverage | macOS, Linux, Windows |
| Risk control | Separates official traces from ambiguous companion or lookalike artifacts |
| Intended users | Agent builders, operators, power users, and maintainers who need auditable uninstall logic |

## Why this repository exists

OpenClaw uninstall is not a one-line `rm -rf ~/.openclaw`.

Depending on install path and platform, a machine may contain:

- user services:
  - macOS `launchd`
  - Linux `systemd --user`
  - Windows `schtasks`
  - Windows Startup-folder fallback launchers
- profile-specific state directories such as `~/.openclaw-dev` and `~/.openclaw-<profile>`
- shell init or completion hooks
- wrapper binaries in user or system bin directories
- global package directories
- source-checkout installs and local wrappers
- optional platform-specific support files and app bundles

This repository turns that uninstall surface into a deterministic, testable artifact model instead of relying on ad-hoc shell commands and guesswork.

## What the toolkit actually does

The project combines two pieces:

1. A reusable agent-facing skill in [SKILL.md](SKILL.md)
2. A deterministic helper CLI in [scripts/openclaw_uninstall.py](scripts/openclaw_uninstall.py)

The CLI supports four modes:

- `scan`: discover official traces, manual-review traces, and explicit exclusions
- `plan`: turn the scan into an ordered uninstall sequence
- `apply`: perform destructive actions only after explicit high-risk confirmation
- `verify`: rescan and report what still remains

## Detection coverage

### Official OpenClaw traces

| Platform | Examples |
| --- | --- |
| macOS | `~/Library/LaunchAgents/ai.openclaw.gateway.plist`, `~/.openclaw`, `/Applications/OpenClaw.app`, shell completion hooks |
| Linux | `~/.config/systemd/user/openclaw-gateway.service`, `~/.openclaw`, `~/.openclaw-<profile>`, wrapper installs |
| Windows | `OpenClaw Gateway`, Startup-folder fallback launchers, `%USERPROFILE%\.openclaw\gateway.cmd` |

### Explicitly non-default-delete traces

The scanner reports but does not auto-delete:

- companion-app traces such as `AutoClaw`
- browser bridge artifacts that are not part of the documented official OpenClaw core install
- opaque `OPENCLAW_STATE_DIR` overrides that do not carry an explicit `openclaw` marker in the path
- protected AI tooling roots such as `.codex/skills`, `.agents/skills`, `.claude/skills`, `.claude/agents`, `.claude/commands`, `.gemini/commands`, and OpenCode skill directories
- arbitrary files that merely contain the string `openclaw`

## Safety guarantees

This repo is designed around deletion safety, not convenience theater.

- It never treats keyword matching alone as enough evidence to delete a path.
- It requires all of these flags before `apply`:
  - `--yes`
  - `--acknowledge-risk`
  - `--confirm "REMOVE OPENCLAW FROM THIS MACHINE"`
- It edits shell init files surgically and keeps a backup.
- It reports privileged leftovers as exact manual commands instead of pretending the uninstall fully succeeded.
- It encodes exclusions as first-class output, so the agent can explain what it intentionally skipped.
- It protects neighboring AI extension ecosystems so OpenClaw cleanup cannot spill into Codex, Claude Code, Gemini CLI, or OpenCode customization directories.

## Quick start

### 1. Scan only

```bash
python3 scripts/openclaw_uninstall.py scan --json
```

### 2. Build an uninstall plan

```bash
python3 scripts/openclaw_uninstall.py plan --json
```

### 3. Rehearse with dry-run

```bash
python3 scripts/openclaw_uninstall.py apply \
  --dry-run \
  --yes \
  --acknowledge-risk \
  --confirm "REMOVE OPENCLAW FROM THIS MACHINE" \
  --json
```

### 4. Apply for real

```bash
python3 scripts/openclaw_uninstall.py apply \
  --yes \
  --acknowledge-risk \
  --confirm "REMOVE OPENCLAW FROM THIS MACHINE" \
  --json
```

### 5. Verify what remains

```bash
python3 scripts/openclaw_uninstall.py verify --json
```

## Typical workflows

### Local workstation cleanup

```bash
python3 scripts/openclaw_uninstall.py scan --json
python3 scripts/openclaw_uninstall.py plan --json
python3 scripts/openclaw_uninstall.py apply \
  --yes \
  --acknowledge-risk \
  --confirm "REMOVE OPENCLAW FROM THIS MACHINE" \
  --json
python3 scripts/openclaw_uninstall.py verify --json
```

### Inspect a named profile

```bash
python3 scripts/openclaw_uninstall.py scan --profile rescue --json
```

### Run against a synthetic filesystem

```bash
python3 scripts/openclaw_uninstall.py scan \
  --platform darwin \
  --home /Users/tester \
  --root /tmp/openclaw-fixture \
  --json
```

### Deal with privileged leftovers

When the tool finds root-owned artifacts, it returns exact next-step commands, for example:

```bash
sudo rm -f "/usr/local/bin/openclaw"
sudo rm -rf "/usr/local/lib/node_modules/openclaw"
```

## Example output shape

The scanner reports both actionability and boundaries:

```json
{
  "artifacts": [
    {
      "kind": "cli_binary",
      "path": "/usr/local/bin/openclaw",
      "auto_action": "delete",
      "requires_privilege": true
    },
    {
      "kind": "excluded_path",
      "path": "/Users/example/.codex/skills/openclaw-openclaw-obsidian",
      "auto_action": "excluded"
    }
  ]
}
```

That distinction is deliberate. A safe uninstaller should explain both what it will remove and what it refuses to touch.

## Repository map

```text
.
├── SKILL.md
├── agents/openai.yaml
├── references/
├── scripts/
├── tests/
├── fixtures/
└── .github/
```

### Key files

- [SKILL.md](SKILL.md): agent-facing uninstall workflow
- [agents/openai.yaml](agents/openai.yaml): skill interface metadata
- [references/research-notes.md](references/research-notes.md): uninstall research and evidence
- [references/artifact-matrix.md](references/artifact-matrix.md): official vs manual-review artifact model
- [references/safety-model.md](references/safety-model.md): risk boundaries and operator expectations
- [scripts/openclaw_uninstall.py](scripts/openclaw_uninstall.py): deterministic CLI
- [tests/test_openclaw_uninstall.py](tests/test_openclaw_uninstall.py): regression tests

## Documentation

- Research basis: [references/research-notes.md](references/research-notes.md)
- Artifact policy: [references/artifact-matrix.md](references/artifact-matrix.md)
- Safety boundaries: [references/safety-model.md](references/safety-model.md)
- Initial implementation plan: [docs/plans/2026-03-31-openclaw-uninstall-skill.md](docs/plans/2026-03-31-openclaw-uninstall-skill.md)

## Development

No runtime dependencies beyond Python 3.9+.

Run tests:

```bash
python3 -m unittest discover -s tests -v
```

## Non-goals

This repository is deliberately narrow.

- It is not a generic package uninstaller.
- It is not a machine-wide “delete everything with openclaw in the name” script.
- It is not a replacement for human review on privileged, enterprise, or companion-app installs.
- It is not a tool for deleting Codex skills just because a folder name happens to contain `openclaw`.

## License

MIT. See [LICENSE](LICENSE).
