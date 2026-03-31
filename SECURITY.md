# Security Policy

This repository automates high-risk local uninstall behavior.

## Reporting a vulnerability

Please do not open a public issue for:

- privilege escalation flaws
- path traversal or unintended deletion cases
- confirmation bypasses
- exclusion-rule bypasses

Instead, contact the maintainer privately and include:

- affected platform
- command used
- minimal reproduction
- expected vs actual deletion behavior

## Safe testing guidance

- prefer synthetic fixture roots using `--root`
- prefer `--dry-run` before live apply
- never test destructive changes on a machine you cannot rebuild
