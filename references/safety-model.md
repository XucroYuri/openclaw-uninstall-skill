# Safety Model

## Core idea

A safe OpenClaw uninstall is not defined as “delete everything containing the word openclaw”.

It is defined as:

1. identify official install traces
2. separate high-confidence traces from adjacent traces
3. remove only the high-confidence set after explicit approval
4. verify what remains
5. report privileged leftovers accurately

## Risk controls

### Control 1: Deterministic scan first

Every run starts with `scan` and builds a structured artifact list before any destructive action.

### Control 2: Strong confirmation phrase

`apply` requires:

- `--yes`
- `--acknowledge-risk`
- `--confirm "REMOVE OPENCLAW FROM THIS MACHINE"`

This prevents accidental execution from a vague prompt.

### Control 3: Exclusions are first-class

The scanner returns excluded paths explicitly so the agent can explain why they were skipped.

### Control 4: Shell edits are backed up

Shell init files are never modified in place without creating a timestamped backup.

### Control 5: Permission failures become manual commands

If a binary or package dir is root-owned, the tool reports the exact manual cleanup command instead of silently failing or pretending the uninstall completed.

### Control 6: Companion-app ambiguity is not auto-resolved

Observed-but-unofficial artifacts such as `AutoClaw` are reported as `manual_review`.

### Control 7: Custom state overrides still need an OpenClaw marker

`OPENCLAW_STATE_DIR` values discovered from the environment or service files are only auto-deleted when the path itself still carries an explicit `openclaw` marker.

If a custom override points at an opaque directory name such as `~/Documents/agent-state`, the scanner downgrades it to `manual_review` instead of deleting it automatically.

## Recommended agent behavior

- explain the plan before `apply`
- call out `manual_review` artifacts clearly
- call out any root/system paths clearly
- treat verification output as the source of truth, not the attempted operation count
