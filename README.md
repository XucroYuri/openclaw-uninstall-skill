# openclaw-uninstall-skill

[![CI](https://github.com/XucroYuri/openclaw-uninstall-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/XucroYuri/openclaw-uninstall-skill/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-informational)](#development)

High-safety Agent Skill and validation toolkit for uninstalling OpenClaw from macOS, Linux, and Windows without treating the machine like disposable infrastructure.

This repository exists for one narrow job:

- model OpenClaw install traces across platforms
- plan a reversible uninstall sequence
- execute only after explicit high-risk confirmation
- verify what remains
- separate official OpenClaw artifacts from adjacent or misleading local traces

It is intentionally conservative. The default flow is `scan -> plan -> explicit human approval -> apply -> verify`.

## Why this exists

OpenClaw removal is not just `rm -rf ~/.openclaw`.

Depending on install method and platform, OpenClaw may leave behind:

- per-user background services:
  - macOS `launchd`
  - Linux `systemd --user`
  - Windows `schtasks` or Startup-folder fallback
- multiple profile state directories such as `~/.openclaw-dev` and `~/.openclaw-<profile>`
- shell completion or shell init snippets
- CLI wrappers and global package directories
- source-checkout wrappers (`~/.local/bin/openclaw`) and git checkouts
- app bundles or logging overrides on macOS

This project codifies those traces into a deterministic artifact model backed by official docs and real-world uninstall experience.

## Safety model

This repo does **not** treat every `openclaw`-looking path as removable.

- It never auto-targets `.codex/skills` or `.agents/skills`.
- It treats known companion-app traces like `AutoClaw` as `manual_review`, not `auto_delete`.
- It requires all of these before applying changes:
  - `--acknowledge-risk`
  - `--yes`
  - `--confirm "REMOVE OPENCLAW FROM THIS MACHINE"`

If a path is root-owned or needs stronger privileges, the tool reports the exact manual cleanup command instead of pretending the uninstall succeeded.

## Repository layout

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

- `SKILL.md`: the agent-facing uninstall workflow
- `references/`: research notes, artifact matrix, safety boundaries
- `scripts/openclaw_uninstall.py`: deterministic scan/plan/apply/verify CLI
- `tests/`: standard-library regression tests
- `fixtures/`: reserved space for future sample manifests and snapshots

## Quick start

### 1. Scan only

```bash
python3 scripts/openclaw_uninstall.py scan --json
```

### 2. Build a plan

```bash
python3 scripts/openclaw_uninstall.py plan --json
```

### 3. Apply with explicit risk acknowledgement

```bash
python3 scripts/openclaw_uninstall.py apply \
  --yes \
  --acknowledge-risk \
  --confirm "REMOVE OPENCLAW FROM THIS MACHINE" \
  --json
```

### 4. Verify leftovers

```bash
python3 scripts/openclaw_uninstall.py verify --json
```

## Common scenarios

### Dry-run a local uninstall

```bash
python3 scripts/openclaw_uninstall.py apply \
  --dry-run \
  --yes \
  --acknowledge-risk \
  --confirm "REMOVE OPENCLAW FROM THIS MACHINE"
```

### Inspect a named profile

```bash
python3 scripts/openclaw_uninstall.py scan --profile rescue --json
```

### Test against a synthetic filesystem

```bash
python3 scripts/openclaw_uninstall.py scan \
  --platform darwin \
  --home /Users/tester \
  --root /tmp/openclaw-fixture \
  --json
```

## Development

No runtime dependencies beyond Python 3.9+.

Run tests:

```bash
python3 -m unittest discover -s tests -v
```

## Research basis

The artifact model in this repo is based on:

- OpenClaw official uninstall docs
- OpenClaw official installer docs
- OpenClaw platform docs for macOS, Linux, and Windows service behavior
- direct inspection of the locally installed `openclaw` package structure and service constants
- real local uninstall traces where non-official companion artifacts had to be separated from official OpenClaw traces

See [references/research-notes.md](references/research-notes.md).

## Non-goals

- not a generic package uninstaller
- not a system-wide “delete everything with openclaw in the name” script
- not a replacement for user judgment on root-owned or custom enterprise installs
- not a tool for deleting Codex skills that merely contain `openclaw` in the folder name

## License

MIT. See [LICENSE](LICENSE).
