from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "openclaw_uninstall.py"

spec = importlib.util.spec_from_file_location("openclaw_uninstall", MODULE_PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class OpenClawUninstallTests(unittest.TestCase):
    def test_scan_macos_detects_state_launchagent_shell_and_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Users" / "tester" / ".openclaw").mkdir(parents=True)
            launch = root / "Users" / "tester" / "Library" / "LaunchAgents"
            launch.mkdir(parents=True)
            (launch / "ai.openclaw.gateway.plist").write_text("<plist/>", encoding="utf-8")
            (root / "Users" / "tester" / ".zshrc").write_text(
                '# OpenClaw Completion\nsource "/Users/tester/.openclaw/completions/openclaw.zsh"\n',
                encoding="utf-8",
            )
            binary = root / "usr" / "local" / "bin"
            binary.mkdir(parents=True)
            (binary / "openclaw").write_text("#!/bin/sh\n", encoding="utf-8")
            artifacts = mod.scan_installation(
                platform_name="darwin",
                home_display="/Users/tester",
                root_prefix=str(root),
            )
            found = {(artifact.kind, artifact.display_path) for artifact in artifacts}
            self.assertIn(("state_dir", "/Users/tester/.openclaw"), found)
            self.assertIn(("launch_agent", "/Users/tester/Library/LaunchAgents/ai.openclaw.gateway.plist"), found)
            self.assertIn(("shell_injection", "/Users/tester/.zshrc"), found)
            self.assertIn(("cli_binary", "/usr/local/bin/openclaw"), found)

    def test_scan_excludes_codex_skill_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / "Users" / "tester" / ".codex" / "skills" / "openclaw-openclaw-obsidian"
            skill_dir.mkdir(parents=True)
            artifacts = mod.scan_installation(
                platform_name="darwin",
                home_display="/Users/tester",
                root_prefix=str(root),
            )
            excluded = [artifact for artifact in artifacts if artifact.auto_action == mod.EXCLUDED]
            self.assertEqual(len(excluded), 1)
            self.assertEqual(excluded[0].display_path, "/Users/tester/.codex/skills/openclaw-openclaw-obsidian")

    def test_scan_excludes_other_agent_tooling_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entries = [
                root / "Users" / "tester" / ".claude" / "agents" / "openclaw-helper.md",
                root / "Users" / "tester" / ".gemini" / "commands" / "openclaw.toml",
                root / "Users" / "tester" / ".config" / "opencode" / "skills" / "openclaw-cleanup" / "SKILL.md",
            ]
            for entry in entries:
                entry.parent.mkdir(parents=True, exist_ok=True)
                entry.write_text("placeholder", encoding="utf-8")
            artifacts = mod.scan_installation(
                platform_name="darwin",
                home_display="/Users/tester",
                root_prefix=str(root),
            )
            excluded = {(artifact.kind, artifact.display_path) for artifact in artifacts if artifact.auto_action == mod.EXCLUDED}
            self.assertIn(("excluded_path", "/Users/tester/.claude/agents/openclaw-helper.md"), excluded)
            self.assertIn(("excluded_path", "/Users/tester/.gemini/commands/openclaw.toml"), excluded)
            self.assertIn(("excluded_path", "/Users/tester/.config/opencode/skills/openclaw-cleanup"), excluded)

    def test_scan_excludes_project_local_tooling_roots_from_git_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "Users" / "tester" / "workspace" / "repo"
            entry = project / ".opencode" / "skills" / "openclaw-guard" / "SKILL.md"
            entry.parent.mkdir(parents=True, exist_ok=True)
            entry.write_text("placeholder", encoding="utf-8")
            artifacts = mod.scan_installation(
                platform_name="darwin",
                home_display="/Users/tester",
                root_prefix=str(root),
                git_dir="/Users/tester/workspace/repo",
            )
            excluded = {(artifact.kind, artifact.display_path) for artifact in artifacts if artifact.auto_action == mod.EXCLUDED}
            self.assertIn(("excluded_path", "/Users/tester/workspace/repo/.opencode/skills/openclaw-guard"), excluded)

    def test_companion_artifacts_are_manual_review_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            companion = root / "Users" / "tester" / "Library" / "Application Support" / "autoclaw"
            companion.mkdir(parents=True)
            artifacts = mod.scan_installation(
                platform_name="darwin",
                home_display="/Users/tester",
                root_prefix=str(root),
            )
            review = [artifact for artifact in artifacts if artifact.auto_action == mod.OFFICIAL_COMPANION_REVIEW]
            self.assertEqual(len(review), 1)
            self.assertIn("autoclaw", review[0].display_path)

    def test_apply_removes_state_dir_and_shell_injection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "Users" / "tester" / ".openclaw"
            state.mkdir(parents=True)
            shell = root / "Users" / "tester" / ".zshrc"
            shell.parent.mkdir(parents=True, exist_ok=True)
            shell.write_text(
                '# OpenClaw Completion\nsource "/Users/tester/.openclaw/completions/openclaw.zsh"\nexport PATH="$HOME/bin:$PATH"\n',
                encoding="utf-8",
            )
            artifacts = mod.scan_installation(
                platform_name="darwin",
                home_display="/Users/tester",
                root_prefix=str(root),
            )
            ops = mod.build_plan(artifacts)
            report_dir = root / "reports"
            result = mod.execute_apply(artifacts=artifacts, operations=ops, report_dir=report_dir)
            self.assertTrue(any(action["status"] == "deleted" for action in result["actions"]))
            self.assertFalse(state.exists())
            remaining_shell = shell.read_text(encoding="utf-8")
            self.assertNotIn("openclaw", remaining_shell)
            self.assertIn("export PATH", remaining_shell)

    def test_windows_startup_fallback_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "C" / "Users" / "tester" / ".openclaw"
            state.mkdir(parents=True)
            (state / "gateway.cmd").write_text("@echo off\n", encoding="utf-8")
            startup = root / "C" / "Users" / "tester" / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            startup.mkdir(parents=True)
            (startup / "OpenClaw Gateway.cmd").write_text("@echo off\n", encoding="utf-8")
            artifacts = mod.scan_installation(
                platform_name="win32",
                home_display=r"C:\Users\tester",
                root_prefix=str(root),
            )
            kinds = {(artifact.kind, artifact.metadata.get("task_name", "")) for artifact in artifacts}
            self.assertIn(("startup_entry", "OpenClaw Gateway"), kinds)
            self.assertIn(("task_script", "OpenClaw Gateway"), kinds)

    def test_symlink_binary_only_adds_openclaw_package_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_dir = root / "usr" / "local" / "lib" / "node_modules" / "openclaw"
            package_dir.mkdir(parents=True)
            target = package_dir / "openclaw.mjs"
            target.write_text("console.log('hi')\n", encoding="utf-8")
            bin_dir = root / "usr" / "local" / "bin"
            bin_dir.mkdir(parents=True)
            os.symlink("../lib/node_modules/openclaw/openclaw.mjs", bin_dir / "openclaw")
            artifacts = mod.scan_installation(
                platform_name="darwin",
                home_display="/Users/tester",
                root_prefix=str(root),
            )
            found = {(artifact.kind, artifact.display_path) for artifact in artifacts}
            self.assertIn(("package_dir", "/usr/local/lib/node_modules/openclaw"), found)
            self.assertNotIn(("package_dir", "/usr/local/lib/node_modules"), found)

    def test_env_custom_state_without_openclaw_marker_is_manual_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            custom_state = root / "Users" / "tester" / "Documents" / "agent-state"
            custom_state.mkdir(parents=True)
            with mock.patch.dict(os.environ, {"OPENCLAW_STATE_DIR": "/Users/tester/Documents/agent-state"}, clear=False):
                artifacts = mod.scan_installation(
                    platform_name="darwin",
                    home_display="/Users/tester",
                    root_prefix=str(root),
                )
            matched = [artifact for artifact in artifacts if artifact.display_path == "/Users/tester/Documents/agent-state"]
            self.assertEqual(len(matched), 1)
            self.assertEqual(matched[0].auto_action, mod.OFFICIAL_COMPANION_REVIEW)

    def test_service_custom_state_without_openclaw_marker_is_manual_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            launch = root / "Users" / "tester" / "Library" / "LaunchAgents"
            launch.mkdir(parents=True)
            (launch / "ai.openclaw.gateway.plist").write_text(
                """
                <plist>
                  <key>EnvironmentVariables</key>
                  <dict>
                    <key>OPENCLAW_STATE_DIR</key>
                    <string>/Users/tester/Documents/agent-state</string>
                  </dict>
                </plist>
                """,
                encoding="utf-8",
            )
            custom_state = root / "Users" / "tester" / "Documents" / "agent-state"
            custom_state.mkdir(parents=True)
            artifacts = mod.scan_installation(
                platform_name="darwin",
                home_display="/Users/tester",
                root_prefix=str(root),
            )
            matched = [artifact for artifact in artifacts if artifact.display_path == "/Users/tester/Documents/agent-state"]
            self.assertEqual(len(matched), 1)
            self.assertEqual(matched[0].auto_action, mod.OFFICIAL_COMPANION_REVIEW)

    def test_delete_path_refuses_unsafe_custom_state_without_openclaw_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            custom_state = root / "Users" / "tester" / "Documents" / "agent-state"
            custom_state.mkdir(parents=True)
            resolver = mod.PathResolver("darwin", "/Users/tester", str(root))
            artifact = mod.make_artifact(
                kind="state_dir",
                display_path="/Users/tester/Documents/agent-state",
                resolver=resolver,
                platform_name="darwin",
                profile="custom",
            )
            result = mod.delete_path(artifact)
            self.assertEqual(result["status"], "refused_unsafe_path")
            self.assertTrue(custom_state.exists())

    def test_protected_tooling_custom_state_is_excluded_and_not_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected_dir = root / "Users" / "tester" / ".claude" / "agents" / "openclaw-helper"
            protected_dir.mkdir(parents=True)
            with mock.patch.dict(os.environ, {"OPENCLAW_STATE_DIR": "/Users/tester/.claude/agents/openclaw-helper"}, clear=False):
                artifacts = mod.scan_installation(
                    platform_name="darwin",
                    home_display="/Users/tester",
                    root_prefix=str(root),
                )
            matched = [artifact for artifact in artifacts if artifact.display_path == "/Users/tester/.claude/agents/openclaw-helper"]
            self.assertEqual(len(matched), 1)
            self.assertEqual(matched[0].auto_action, mod.EXCLUDED)
            result = mod.delete_path(matched[0])
            self.assertEqual(result["status"], "refused_protected_path")
            self.assertTrue(protected_dir.exists())


if __name__ == "__main__":
    unittest.main()
