# OpenClaw Uninstall Skill Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a publishable open source skill and deterministic helper CLI for high-safety OpenClaw uninstall across macOS, Linux, and Windows.

**Architecture:** The repo combines a concise agent skill with a standard-library Python helper that models official install traces, builds an uninstall plan, executes only after strong confirmation, and verifies leftovers. Research notes and artifact policy documents keep the skill itself lean while preserving justification for future contributors.

**Tech Stack:** Markdown, YAML, Python 3.10+, unittest, GitHub Actions

---

### Task 1: Capture research and scope

**Files:**
- Create: `references/research-notes.md`
- Create: `references/artifact-matrix.md`
- Create: `references/safety-model.md`

**Step 1:** Summarize official uninstall and installer behavior.

**Step 2:** Separate official traces from companion-app traces.

**Step 3:** Document explicit exclusions such as Codex skill folders.

### Task 2: Design the skill contract

**Files:**
- Create: `SKILL.md`
- Create: `agents/openai.yaml`

**Step 1:** Encode the scan -> plan -> approval -> apply -> verify workflow.

**Step 2:** Document hard boundaries and confirmation gates.

### Task 3: Implement deterministic helper CLI

**Files:**
- Create: `scripts/openclaw_uninstall.py`

**Step 1:** Implement cross-platform artifact scanning.

**Step 2:** Implement ordered uninstall planning.

**Step 3:** Implement guarded apply mode.

**Step 4:** Implement post-apply verification and manual command suggestions.

### Task 4: Add tests

**Files:**
- Create: `tests/test_openclaw_uninstall.py`

**Step 1:** Cover macOS scan paths and shell injection.

**Step 2:** Cover explicit exclusions.

**Step 3:** Cover manual-review-only companion traces.

**Step 4:** Cover Windows Startup fallback detection.

### Task 5: Add open source repo essentials

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `CONTRIBUTING.md`
- Create: `SECURITY.md`
- Create: `CODE_OF_CONDUCT.md`
- Create: `.gitignore`
- Create: `.github/workflows/ci.yml`
- Create: `.github/pull_request_template.md`
- Create: `.github/ISSUE_TEMPLATE/bug_report.yml`
- Create: `.github/ISSUE_TEMPLATE/feature_request.yml`
- Create: `.github/ISSUE_TEMPLATE/config.yml`

**Step 1:** Document the project for users and contributors.

**Step 2:** Add CI for standard-library tests.

**Step 3:** Add issue and PR templates.
