#!/usr/bin/env python3
"""High-safety OpenClaw uninstall helper.

This tool models official OpenClaw install traces across macOS, Linux, and
Windows, separates auto-delete targets from manual-review artifacts, and only
applies destructive actions after explicit confirmation.
"""

from __future__ import annotations

import argparse
import json
import os
import platform as py_platform
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator


CONFIRM_PHRASE = "REMOVE OPENCLAW FROM THIS MACHINE"
OFFICIAL_COMPANION_REVIEW = "manual_review"
EXCLUDED = "excluded"

SHELL_PATTERNS = [
    re.compile(r'^\s*#\s*OpenClaw Completion\s*$'),
    re.compile(r'^\s*source\s+["\']?.*?/\.openclaw(?:-[^/"\']+)?/completions/openclaw\.(?:zsh|bash|fish|ps1)["\']?\s*$'),
    re.compile(r'^\s*source\s+["\']?.*openclaw/completions/openclaw\.(?:zsh|bash|fish|ps1)["\']?\s*$'),
    re.compile(r'.*openclaw.*completions/openclaw\.(?:zsh|bash|fish|ps1).*'),
]

AUTOCLAW_MARKERS = [
    ".openclaw-autoclaw",
    "Application Support/autoclaw",
    "com.zhipuai.autoclaw.plist",
    "com.autoclaw.native_host_stub.json",
    "AutoClaw.app",
]


@dataclass
class Artifact:
    kind: str
    display_path: str
    actual_path: Path
    platform: str
    profile: str | None = None
    auto_action: str = "delete"
    requires_privilege: bool = False
    notes: str | None = None
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "path": self.display_path,
            "platform": self.platform,
            "profile": self.profile,
            "auto_action": self.auto_action,
            "requires_privilege": self.requires_privilege,
            "notes": self.notes,
            "evidence": self.evidence,
            "metadata": self.metadata,
        }


@dataclass
class Operation:
    phase: str
    action: str
    artifact: Artifact
    description: str

    def to_json(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "action": self.action,
            "description": self.description,
            "artifact": self.artifact.to_json(),
        }


class PathResolver:
    def __init__(self, platform_name: str, home_display: str, root_prefix: str | None = None) -> None:
        self.platform_name = platform_name
        self.home_display = home_display
        self.root_prefix = Path(root_prefix).expanduser().resolve() if root_prefix else None

    def path(self, display_path: str) -> Path:
        if not self.root_prefix:
            return Path(display_path).expanduser()
        if self.platform_name == "win32":
            normalized = display_path.replace("\\", "/")
            drive_match = re.match(r"^([A-Za-z]):/(.*)$", normalized)
            if drive_match:
                drive, tail = drive_match.groups()
                return self.root_prefix / drive.upper() / tail
            return self.root_prefix / normalized.lstrip("/")
        return self.root_prefix / display_path.lstrip("/")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def detect_platform(explicit: str | None = None) -> str:
    if explicit and explicit != "auto":
        return explicit
    current = sys.platform
    if current.startswith("linux"):
        return "linux"
    if current.startswith("darwin"):
        return "darwin"
    if current.startswith("win"):
        return "win32"
    return current


def default_home(platform_name: str) -> str:
    if platform_name == "win32":
        return os.environ.get("USERPROFILE") or os.environ.get("HOME") or r"C:\Users\agent"
    return str(Path.home())


def privilege_required(display_path: str, platform_name: str) -> bool:
    if platform_name == "win32":
        return display_path.startswith(r"C:\Program Files") or display_path.startswith(r"C:\Windows")
    return display_path.startswith("/usr/") or display_path.startswith("/opt/") or display_path.startswith("/Library/")


def normalize_display_path(display_path: str) -> str:
    normalized = display_path.replace("\\", "/")
    if normalized != "/":
        normalized = normalized.rstrip("/")
    return normalized


def path_has_openclaw_marker(display_path: str) -> bool:
    return "openclaw" in normalize_display_path(display_path).lower()


def classify_custom_state_path(display_path: str) -> tuple[str, str | None]:
    if path_has_openclaw_marker(display_path):
        return "delete", None
    return (
        OFFICIAL_COMPANION_REVIEW,
        "Custom OPENCLAW_STATE_DIR is outside the default path set and lacks an explicit 'openclaw' path marker. Review manually before deleting.",
    )


def file_contains(path: Path, needle: str) -> bool:
    try:
        return needle in path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def is_probable_openclaw_checkout(path: Path) -> bool:
    if not path.is_dir():
        return False
    package_json = path / "package.json"
    if not package_json.exists():
        return False
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except Exception:
        return False
    return data.get("name") == "openclaw"


def backup_file(path: Path, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    backup_name = f"{path.name}.bak.openclaw-uninstall-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    target = report_dir / backup_name
    shutil.copy2(path, target)
    return target


def run_command(args: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(args, check=False, capture_output=True, text=True)
        return proc.returncode, (proc.stderr or proc.stdout or "").strip()
    except Exception as exc:
        return 1, str(exc)


def candidate_shell_files(home: str, platform_name: str) -> list[str]:
    shells = [
        f"{home}/.zshrc",
        f"{home}/.zprofile",
        f"{home}/.bashrc",
        f"{home}/.bash_profile",
        f"{home}/.profile",
        f"{home}/.config/fish/config.fish",
    ]
    if platform_name == "win32":
        shells.append(fr"{home}\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1")
        shells.append(fr"{home}\Documents\PowerShell\Microsoft.PowerShell_profile.ps1")
    return shells


def iter_existing_children(path: Path, prefix: str) -> Iterator[Path]:
    if not path.exists():
        return
    for child in path.iterdir():
        if child.name.startswith(prefix):
            yield child


def discover_profile_dirs(home_display: str, resolver: PathResolver) -> list[tuple[str, str]]:
    home_actual = resolver.path(home_display)
    if not home_actual.exists():
        return []
    profiles: list[tuple[str, str]] = []
    for child in home_actual.iterdir():
        name = child.name
        if not child.is_dir():
            continue
        if name == ".openclaw-dev":
            profiles.append(("dev", f"{home_display}/.openclaw-dev"))
            continue
        match = re.fullmatch(r"\.openclaw-(.+)", name)
        if match and name != ".openclaw-install-backups":
            profiles.append((match.group(1), f"{home_display}/{name}"))
    return profiles


def make_artifact(
    *,
    kind: str,
    display_path: str,
    resolver: PathResolver,
    platform_name: str,
    profile: str | None = None,
    auto_action: str = "delete",
    notes: str | None = None,
    evidence: Iterable[str] | None = None,
    metadata: dict[str, str] | None = None,
) -> Artifact:
    actual = resolver.path(display_path)
    return Artifact(
        kind=kind,
        display_path=display_path,
        actual_path=actual,
        platform=platform_name,
        profile=profile,
        auto_action=auto_action,
        requires_privilege=privilege_required(display_path, platform_name),
        notes=notes,
        evidence=list(evidence or []),
        metadata=metadata or {},
    )


def scan_installation(
    *,
    platform_name: str,
    home_display: str,
    root_prefix: str | None = None,
    profiles: list[str] | None = None,
    git_dir: str | None = None,
) -> list[Artifact]:
    resolver = PathResolver(platform_name, home_display, root_prefix)
    artifacts: list[Artifact] = []
    seen: set[tuple[str, str]] = set()

    def add(artifact: Artifact) -> None:
        key = (artifact.kind, artifact.display_path)
        if key in seen:
            return
        seen.add(key)
        artifacts.append(artifact)

    # Exclude skill folders explicitly.
    for display in [
        f"{home_display}/.codex/skills/openclaw-openclaw-obsidian",
        f"{home_display}/.agents/skills/openclaw-openclaw-obsidian",
    ]:
        actual = resolver.path(display)
        if actual.exists():
            add(
                make_artifact(
                    kind="excluded_path",
                    display_path=display,
                    resolver=resolver,
                    platform_name=platform_name,
                    auto_action=EXCLUDED,
                    notes="Contains 'openclaw' in the path but is a skill directory and outside uninstall scope.",
                )
            )

    # State directories.
    profile_dirs = discover_profile_dirs(home_display, resolver)
    explicit_profiles = profiles or []
    candidate_states = [(None, f"{home_display}/.openclaw")] + profile_dirs
    for profile in explicit_profiles:
        if profile == "default":
            candidate_states.append((None, f"{home_display}/.openclaw"))
        elif profile == "dev":
            candidate_states.append(("dev", f"{home_display}/.openclaw-dev"))
        else:
            candidate_states.append((profile, f"{home_display}/.openclaw-{profile}"))
    custom_state = os.environ.get("OPENCLAW_STATE_DIR")
    if custom_state:
        candidate_states.append(("custom", custom_state))
    for profile_name, display in candidate_states:
        actual = resolver.path(display)
        if actual.exists():
            auto_action = "delete"
            notes = None
            if profile_name == "custom":
                auto_action, notes = classify_custom_state_path(display)
            add(
                make_artifact(
                    kind="state_dir",
                    display_path=display,
                    resolver=resolver,
                    platform_name=platform_name,
                    profile=profile_name,
                    auto_action=auto_action,
                    notes=notes,
                )
            )

    # Shell init snippets.
    for shell_display in candidate_shell_files(home_display, platform_name):
        shell_actual = resolver.path(shell_display)
        if not shell_actual.exists():
            continue
        try:
            lines = shell_actual.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        matches = [line for line in lines if any(pattern.match(line) for pattern in SHELL_PATTERNS)]
        if matches:
            add(
                make_artifact(
                    kind="shell_injection",
                    display_path=shell_display,
                    resolver=resolver,
                    platform_name=platform_name,
                    auto_action="edit",
                    evidence=matches,
                    notes="Removes OpenClaw-specific completion/init lines and keeps a backup before editing.",
                )
            )

    # CLI binaries and package directories.
    binary_candidates = [
        f"{home_display}/.local/bin/openclaw",
        f"{home_display}/.npm-global/bin/openclaw",
        f"{home_display}/bin/openclaw",
        "/usr/local/bin/openclaw",
        "/opt/homebrew/bin/openclaw",
    ]
    if platform_name == "win32":
        binary_candidates = [
            fr"{home_display}\.local\bin\openclaw.cmd",
            fr"{home_display}\AppData\Local\Programs\OpenClaw\openclaw.cmd",
        ]

    for display in binary_candidates:
        actual = resolver.path(display)
        if not actual.exists():
            continue
        add(make_artifact(kind="cli_binary", display_path=display, resolver=resolver, platform_name=platform_name))
        try:
            if actual.is_symlink():
                resolved = actual.resolve()
                if "node_modules" in resolved.as_posix() and "/openclaw/" in resolved.as_posix():
                    package_dir_actual = resolved.parents[0]
                    package_display = package_dir_actual.as_posix()
                    if root_prefix:
                        # Convert fixture path back to host-like path when possible.
                        package_display = package_display.replace(str(Path(root_prefix).resolve()).rstrip("/") + "/", "/")
                    add(
                        make_artifact(
                            kind="package_dir",
                            display_path=package_display,
                            resolver=resolver,
                            platform_name=platform_name,
                        )
                    )
        except OSError:
            pass

    for display in [
        "/usr/local/lib/node_modules/openclaw",
        "/opt/homebrew/lib/node_modules/openclaw",
        f"{home_display}/.npm-global/lib/node_modules/openclaw",
    ]:
        actual = resolver.path(display)
        if actual.exists():
            add(make_artifact(kind="package_dir", display_path=display, resolver=resolver, platform_name=platform_name))

    # Git/source installs.
    git_candidates = [git_dir] if git_dir else []
    git_candidates.extend([f"{home_display}/openclaw", f"{home_display}/Code/openclaw"])
    for display in filter(None, git_candidates):
        actual = resolver.path(display)
        if is_probable_openclaw_checkout(actual):
            add(
                make_artifact(
                    kind="git_checkout",
                    display_path=display,
                    resolver=resolver,
                    platform_name=platform_name,
                    notes="Detected a probable source checkout install.",
                )
            )

    # Platform service files.
    if platform_name == "darwin":
        launch_agents = [
            f"{home_display}/Library/LaunchAgents/ai.openclaw.gateway.plist",
            f"{home_display}/Library/LaunchAgents/ai.openclaw.node.plist",
            f"{home_display}/Library/LaunchAgents/ai.openclaw.ssh-tunnel.plist",
            f"{home_display}/Library/LaunchAgents/bot.molt.gateway.plist",
            f"{home_display}/Library/LaunchAgents/bot.molt.node.plist",
            f"{home_display}/Library/LaunchAgents/bot.molt.ssh-tunnel.plist",
        ]
        for profile_name, _ in profile_dirs:
            launch_agents.extend(
                [
                    f"{home_display}/Library/LaunchAgents/ai.openclaw.{profile_name}.plist",
                    f"{home_display}/Library/LaunchAgents/bot.molt.{profile_name}.plist",
                ]
            )
        launch_dir = resolver.path(f"{home_display}/Library/LaunchAgents")
        if launch_dir.exists():
            for child in launch_dir.iterdir():
                if child.name.startswith("com.openclaw.") and child.suffix == ".plist":
                    launch_agents.append(f"{home_display}/Library/LaunchAgents/{child.name}")
        for display in launch_agents:
            actual = resolver.path(display)
            if actual.exists():
                label = Path(display).stem
                add(
                    make_artifact(
                        kind="launch_agent",
                        display_path=display,
                        resolver=resolver,
                        platform_name=platform_name,
                        metadata={"label": label},
                    )
                )
                extract_custom_service_paths(display, actual, resolver, platform_name, add)

        for display in [
            "/Applications/OpenClaw.app",
            f"{home_display}/Applications/OpenClaw.app",
            f"{home_display}/Library/Preferences/ai.openclaw.mac.plist",
            f"{home_display}/Library/Preferences/ai.openclaw.mac.debug.plist",
            f"{home_display}/Library/Preferences/bot.molt.mac.plist",
            f"{home_display}/Library/Preferences/bot.molt.mac.debug.plist",
            "/Library/Preferences/Logging/Subsystems/ai.openclaw.plist",
            "/Library/Preferences/Logging/Subsystems/bot.molt.plist",
        ]:
            actual = resolver.path(display)
            if actual.exists():
                kind = "app_bundle" if display.endswith(".app") else "support_file"
                add(make_artifact(kind=kind, display_path=display, resolver=resolver, platform_name=platform_name))

    if platform_name == "linux":
        service_names = [
            "openclaw-gateway.service",
            "openclaw-node.service",
            "clawdbot-gateway.service",
            "moltbot-gateway.service",
        ]
        for profile_name, _ in profile_dirs:
            service_names.append(f"openclaw-gateway-{profile_name}.service")
        service_dir_display = f"{home_display}/.config/systemd/user"
        for name in service_names:
            display = f"{service_dir_display}/{name}"
            actual = resolver.path(display)
            if actual.exists():
                add(
                    make_artifact(
                        kind="systemd_unit",
                        display_path=display,
                        resolver=resolver,
                        platform_name=platform_name,
                        metadata={"unit": name},
                    )
                )
                extract_custom_service_paths(display, actual, resolver, platform_name, add)

    if platform_name == "win32":
        profiles_for_windows = [p for p, _ in profile_dirs]
        task_names = ["OpenClaw Gateway", "OpenClaw Node"]
        task_names.extend([f"OpenClaw Gateway ({profile_name})" for profile_name in profiles_for_windows])
        startup_dir = fr"{home_display}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"
        for task_name in task_names:
            startup_display = fr"{startup_dir}\{sanitize_windows_filename(task_name)}.cmd"
            actual = resolver.path(startup_display)
            if actual.exists():
                add(
                    make_artifact(
                        kind="startup_entry",
                        display_path=startup_display,
                        resolver=resolver,
                        platform_name=platform_name,
                        metadata={"task_name": task_name},
                    )
                )
        for profile_name, display in candidate_states:
            actual_state = resolver.path(display)
            if not actual_state.exists():
                continue
            for script_name, task_name in [("gateway.cmd", "OpenClaw Gateway"), ("node.cmd", "OpenClaw Node")]:
                script_display = display.rstrip("\\/") + ("\\" if "\\" in display else "/") + script_name
                actual = resolver.path(script_display)
                if actual.exists():
                    if profile_name and profile_name not in ("custom", "dev"):
                        if script_name == "gateway.cmd":
                            task_name = f"OpenClaw Gateway ({profile_name})"
                    add(
                        make_artifact(
                            kind="task_script",
                            display_path=script_display,
                            resolver=resolver,
                            platform_name=platform_name,
                            profile=profile_name,
                            metadata={"task_name": task_name},
                        )
                    )
                    extract_custom_service_paths(script_display, actual, resolver, platform_name, add)

    # Companion artifacts from real-world cleanup experience: manual review only.
    if platform_name == "darwin":
        companion_candidates = [
            f"{home_display}/.openclaw-autoclaw",
            f"{home_display}/Library/Application Support/autoclaw",
            f"{home_display}/Library/Preferences/com.zhipuai.autoclaw.plist",
            f"{home_display}/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.autoclaw.native_host_stub.json",
            "/Applications/AutoClaw.app",
        ]
        for display in companion_candidates:
            actual = resolver.path(display)
            if actual.exists():
                add(
                    make_artifact(
                        kind="companion_manual_review",
                        display_path=display,
                        resolver=resolver,
                        platform_name=platform_name,
                        auto_action=OFFICIAL_COMPANION_REVIEW,
                        notes="Observed in real uninstall work but not part of official OpenClaw install documentation. Review manually.",
                    )
                )

    return sorted(artifacts, key=lambda item: (item.auto_action, item.kind, item.display_path))


def extract_custom_service_paths(
    display: str,
    actual: Path,
    resolver: PathResolver,
    platform_name: str,
    add_artifact,
) -> None:
    try:
        text = actual.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return
    keys = ["OPENCLAW_CONFIG_PATH", "OPENCLAW_STATE_DIR"]
    for key in keys:
        patterns = [
            rf"{key}[=:\s\"']+([^\"'\r\n<]+)",
            rf"<key>\s*{re.escape(key)}\s*</key>\s*<string>\s*([^<\r\n]+)\s*</string>",
        ]
        seen_values: set[str] = set()
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                value = match.group(1).strip()
                if not value or value in seen_values:
                    continue
                seen_values.add(value)
                if value.startswith("$") or value.startswith("%"):
                    continue
                candidate_actual = resolver.path(value)
                if not candidate_actual.exists():
                    continue
                auto_action = "delete" if key == "OPENCLAW_STATE_DIR" else OFFICIAL_COMPANION_REVIEW
                notes = f"Discovered via {key} inside {display}."
                if key == "OPENCLAW_STATE_DIR":
                    auto_action, override_note = classify_custom_state_path(value)
                    if override_note:
                        notes = f"{notes} {override_note}"
                add_artifact(
                    make_artifact(
                        kind="custom_path",
                        display_path=value,
                        resolver=resolver,
                        platform_name=platform_name,
                        auto_action=auto_action,
                        notes=notes,
                    )
                )


def sanitize_windows_filename(value: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", value)


def build_plan(artifacts: list[Artifact]) -> list[Operation]:
    operations: list[Operation] = []
    for artifact in artifacts:
        if artifact.auto_action in (EXCLUDED, OFFICIAL_COMPANION_REVIEW):
            continue
        if artifact.kind in {"launch_agent", "systemd_unit", "startup_entry", "task_script"}:
            operations.append(Operation("service-unregister", "unregister", artifact, f"Unregister service or login item for {artifact.display_path}"))
        if artifact.kind == "shell_injection":
            operations.append(Operation("shell-cleanup", "edit", artifact, f"Remove OpenClaw-specific lines from {artifact.display_path}"))
        else:
            operations.append(Operation("delete-artifact", "delete", artifact, f"Delete {artifact.kind} at {artifact.display_path}"))
    phase_order = {"service-unregister": 0, "shell-cleanup": 1, "delete-artifact": 2}
    return sorted(operations, key=lambda op: (phase_order.get(op.phase, 99), op.artifact.requires_privilege, op.artifact.display_path))


def remove_shell_injection(artifact: Artifact, report_dir: Path) -> dict[str, object]:
    path = artifact.actual_path
    backup = backup_file(path, report_dir)
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    kept: list[str] = []
    removed: list[str] = []
    previous_removed_comment = False
    for line in lines:
        matches = any(pattern.match(line) for pattern in SHELL_PATTERNS)
        if matches:
            removed.append(line)
            previous_removed_comment = line.strip().lower() == "# openclaw completion"
            continue
        if previous_removed_comment and not line.strip():
            previous_removed_comment = False
            continue
        previous_removed_comment = False
        kept.append(line)
    path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    return {
        "status": "removed_lines",
        "path": artifact.display_path,
        "backup": backup.as_posix(),
        "removed": removed,
    }


def delete_path(artifact: Artifact) -> dict[str, object]:
    path = artifact.actual_path
    if not path.exists() and not path.is_symlink():
        return {"status": "missing", "path": artifact.display_path}
    if (
        artifact.kind == "custom_path" and not path_has_openclaw_marker(artifact.display_path)
    ) or (
        artifact.kind == "state_dir" and artifact.profile == "custom" and not path_has_openclaw_marker(artifact.display_path)
    ):
        return {"status": "refused_unsafe_path", "path": artifact.display_path}
    try:
        if path.is_symlink() or path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path)
        return {"status": "deleted", "path": artifact.display_path}
    except PermissionError:
        return {"status": "permission_denied", "path": artifact.display_path}


def unregister_service(op: Operation) -> dict[str, object]:
    artifact = op.artifact
    platform_name = artifact.platform
    if artifact.actual_path.exists() is False and artifact.kind not in {"startup_entry", "task_script"}:
        return {"status": "missing", "path": artifact.display_path}
    if artifact.actual_path.parts and "tmp" in artifact.actual_path.parts:
        return {"status": "simulated", "path": artifact.display_path}
    if platform_name == "darwin" and artifact.kind == "launch_agent":
        label = artifact.metadata.get("label", Path(artifact.display_path).stem)
        code, detail = run_command(["launchctl", "bootout", f"gui/{os.getuid()}", artifact.display_path])
        return {"status": "ok" if code == 0 else "best_effort", "path": artifact.display_path, "detail": detail, "label": label}
    if platform_name == "linux" and artifact.kind == "systemd_unit":
        unit = artifact.metadata.get("unit", Path(artifact.display_path).name)
        code, detail = run_command(["systemctl", "--user", "disable", "--now", unit])
        return {"status": "ok" if code == 0 else "best_effort", "path": artifact.display_path, "detail": detail, "unit": unit}
    if platform_name == "win32" and artifact.kind in {"startup_entry", "task_script"}:
        task_name = artifact.metadata.get("task_name")
        detail = ""
        if task_name:
            code, detail = run_command(["schtasks", "/Delete", "/F", "/TN", task_name])
            return {"status": "ok" if code == 0 else "best_effort", "path": artifact.display_path, "detail": detail, "task_name": task_name}
        return {"status": "best_effort", "path": artifact.display_path}
    return {"status": "skipped", "path": artifact.display_path}


def daemon_reload_if_needed(operations: list[dict[str, object]]) -> None:
    if not any(item.get("unit") for item in operations):
        return
    run_command(["systemctl", "--user", "daemon-reload"])


def manual_commands_for_remaining(artifacts: list[Artifact]) -> list[str]:
    commands: list[str] = []
    for artifact in artifacts:
        if artifact.auto_action in (EXCLUDED, OFFICIAL_COMPANION_REVIEW):
            continue
        path = artifact.display_path
        if artifact.platform == "darwin" and artifact.kind == "launch_agent":
            label = artifact.metadata.get("label", Path(path).stem)
            commands.append(f'launchctl bootout gui/$UID/{label} || true\nrm -f "{path}"')
        elif artifact.platform == "linux" and artifact.kind == "systemd_unit":
            unit = artifact.metadata.get("unit", Path(path).name)
            commands.append(f'systemctl --user disable --now "{unit}" || true\nrm -f "{path}"\nsystemctl --user daemon-reload')
        elif artifact.platform == "win32" and artifact.kind in {"startup_entry", "task_script"}:
            task_name = artifact.metadata.get("task_name")
            if task_name:
                commands.append(f'schtasks /Delete /F /TN "{task_name}"\nRemove-Item -Force "{path}"')
            else:
                commands.append(f'Remove-Item -Recurse -Force "{path}"')
        else:
            prefix = "sudo " if artifact.requires_privilege and artifact.platform != "win32" else ""
            if artifact.actual_path.is_dir():
                commands.append(f'{prefix}rm -rf "{path}"')
            else:
                commands.append(f'{prefix}rm -f "{path}"')
    return commands


def execute_apply(
    *,
    artifacts: list[Artifact],
    operations: list[Operation],
    report_dir: Path,
) -> dict[str, object]:
    actions: list[dict[str, object]] = []
    report_dir.mkdir(parents=True, exist_ok=True)
    for op in operations:
        if op.action == "unregister":
            result = unregister_service(op)
        elif op.action == "edit":
            result = remove_shell_injection(op.artifact, report_dir)
        else:
            result = delete_path(op.artifact)
        result["phase"] = op.phase
        result["kind"] = op.artifact.kind
        actions.append(result)
    daemon_reload_if_needed(actions)
    return {"actions": actions}


def summarize(artifacts: list[Artifact], operations: list[Operation]) -> dict[str, object]:
    return {
        "timestamp": now_utc(),
        "artifact_count": len(artifacts),
        "operation_count": len(operations),
        "manual_review": [artifact.to_json() for artifact in artifacts if artifact.auto_action == OFFICIAL_COMPANION_REVIEW],
        "excluded": [artifact.to_json() for artifact in artifacts if artifact.auto_action == EXCLUDED],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safe OpenClaw uninstall helper")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("scan", "plan", "verify"):
        command = subparsers.add_parser(name)
        add_common_arguments(command)
    apply_parser = subparsers.add_parser("apply")
    add_common_arguments(apply_parser)
    apply_parser.add_argument("--yes", action="store_true", help="Confirm that destructive actions may run.")
    apply_parser.add_argument("--acknowledge-risk", action="store_true", help="Acknowledge that uninstalling OpenClaw is a high-risk system operation.")
    apply_parser.add_argument("--confirm", default="", help=f'Exact phrase required: {CONFIRM_PHRASE}')
    apply_parser.add_argument("--dry-run", action="store_true", help="Plan only; do not mutate the filesystem.")
    apply_parser.add_argument("--report-dir", default="", help="Directory where reports and backups should be written.")
    return parser.parse_args(argv)


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--platform", choices=["auto", "darwin", "linux", "win32"], default="auto")
    parser.add_argument("--home", default="", help="Override the home directory used for discovery.")
    parser.add_argument("--root", default="", help="Map absolute paths under a synthetic root for testing.")
    parser.add_argument("--profile", action="append", default=[], help="Extra profile names to include during discovery.")
    parser.add_argument("--git-dir", default="", help="Explicit git checkout directory to inspect.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")


def report_path(base: str | None = None) -> Path:
    if base:
        return Path(base).expanduser()
    temp_root = Path.cwd() / "reports"
    return temp_root / f"openclaw-uninstall-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


def emit(data: dict[str, object], as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    if "summary" in data:
        print(f"Artifacts: {data['summary']['artifact_count']}")
        print(f"Operations: {data['summary']['operation_count']}")
    if "artifacts" in data:
        for artifact in data["artifacts"]:
            print(f"- {artifact['auto_action']}: {artifact['kind']} -> {artifact['path']}")
    if "manual_commands" in data and data["manual_commands"]:
        print("\nManual commands:")
        for command in data["manual_commands"]:
            print(command)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    platform_name = detect_platform(args.platform)
    home_display = args.home or default_home(platform_name)
    artifacts = scan_installation(
        platform_name=platform_name,
        home_display=home_display,
        root_prefix=args.root or None,
        profiles=args.profile,
        git_dir=args.git_dir or None,
    )
    operations = build_plan(artifacts)
    base = {
        "platform": platform_name,
        "home": home_display,
        "summary": summarize(artifacts, operations),
        "artifacts": [artifact.to_json() for artifact in artifacts],
        "operations": [operation.to_json() for operation in operations],
    }

    if args.command == "scan":
        emit(base, args.json)
        return 0
    if args.command == "plan":
        base["manual_commands"] = manual_commands_for_remaining([artifact for artifact in artifacts if artifact.requires_privilege])
        emit(base, args.json)
        return 0
    if args.command == "verify":
        remaining = [artifact for artifact in artifacts if artifact.auto_action not in (EXCLUDED, OFFICIAL_COMPANION_REVIEW)]
        base["manual_commands"] = manual_commands_for_remaining([artifact for artifact in remaining if artifact.requires_privilege])
        emit(base, args.json)
        return 0 if not remaining else 1

    if not (args.yes and args.acknowledge_risk and args.confirm == CONFIRM_PHRASE):
        print(
            "Refusing to apply uninstall. Required: --yes --acknowledge-risk "
            f'--confirm "{CONFIRM_PHRASE}"',
            file=sys.stderr,
        )
        return 2

    report_dir = report_path(args.report_dir or None)
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "openclaw-uninstall-scan.json").write_text(json.dumps(base, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.dry_run:
        base["report_dir"] = report_dir.as_posix()
        base["dry_run"] = True
        emit(base, args.json)
        return 0

    apply_result = execute_apply(artifacts=artifacts, operations=operations, report_dir=report_dir)
    remaining = scan_installation(
        platform_name=platform_name,
        home_display=home_display,
        root_prefix=args.root or None,
        profiles=args.profile,
        git_dir=args.git_dir or None,
    )
    report = {
        **base,
        "report_dir": report_dir.as_posix(),
        "apply": apply_result,
        "remaining": [artifact.to_json() for artifact in remaining],
        "manual_commands": manual_commands_for_remaining(
            [artifact for artifact in remaining if artifact.requires_privilege and artifact.auto_action not in (EXCLUDED, OFFICIAL_COMPANION_REVIEW)]
        ),
    }
    (report_dir / "openclaw-uninstall-apply.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    emit(report, args.json)
    hard_remaining = [
        artifact
        for artifact in remaining
        if artifact.auto_action not in (EXCLUDED, OFFICIAL_COMPANION_REVIEW)
    ]
    return 0 if not hard_remaining else 1


if __name__ == "__main__":
    raise SystemExit(main())
