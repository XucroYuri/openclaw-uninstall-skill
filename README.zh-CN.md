# openclaw-uninstall-skill

[![CI](https://github.com/XucroYuri/openclaw-uninstall-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/XucroYuri/openclaw-uninstall-skill/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-informational)](#开发)
[![Template Repository](https://img.shields.io/badge/github-template-success)](https://github.com/XucroYuri/openclaw-uninstall-skill/generate)

**语言版本：** [English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [Español](README.es.md)

一个面向高风险本机卸载场景的 Agent Skill 与验证工具集，用于在 macOS、Linux、Windows 上安全清理 OpenClaw，而不是靠字符串匹配后直接暴力删除。

> 本项目的默认流程永远是：
> `scan -> plan -> explicit approval -> apply -> verify`

## 项目速览

| 主题 | 说明 |
| --- | --- |
| 核心目标 | 扫描、规划并验证 OpenClaw 的完整卸载 |
| 风险策略 | 没有强确认语句就不执行 destructive apply |
| 平台覆盖 | macOS、Linux、Windows |
| 设计重点 | 区分官方 OpenClaw 痕迹与伴生/误匹配痕迹 |
| 适用对象 | Agent 构建者、运维人员、高级用户、工具维护者 |

## 为什么需要这个项目

OpenClaw 的卸载不是一句 `rm -rf ~/.openclaw` 就能正确完成。

在不同安装方式和不同系统下，机器上可能留下：

- 后台服务痕迹：
  - macOS `launchd`
  - Linux `systemd --user`
  - Windows `schtasks`
  - Windows Startup-folder 回退登录项
- 多配置档状态目录，例如 `~/.openclaw-dev`、`~/.openclaw-<profile>`
- shell init 和 completion 注入
- 用户级或系统级 CLI wrapper
- 全局包目录
- source checkout / git 安装残留
- macOS app bundle 或附加支持文件

本仓库把这些卸载痕迹编码为一个可测试、可解释、可审计的 artifact 模型。

## 工具实际做什么

项目由两部分组成：

1. [SKILL.md](SKILL.md) 中的 agent 卸载技能
2. [scripts/openclaw_uninstall.py](scripts/openclaw_uninstall.py) 中的确定性 CLI

CLI 提供四种模式：

- `scan`：发现官方痕迹、人工复核痕迹、显式排除项
- `plan`：把扫描结果转成有顺序的卸载计划
- `apply`：只有在强确认通过后才执行 destructive 操作
- `verify`：重新扫描并报告剩余项

## 检测范围

### 官方 OpenClaw 痕迹

| 平台 | 典型例子 |
| --- | --- |
| macOS | `~/Library/LaunchAgents/ai.openclaw.gateway.plist`、`~/.openclaw`、`/Applications/OpenClaw.app`、shell completion 注入 |
| Linux | `~/.config/systemd/user/openclaw-gateway.service`、`~/.openclaw`、`~/.openclaw-<profile>`、wrapper 安装 |
| Windows | `OpenClaw Gateway`、Startup-folder 回退 launcher、`%USERPROFILE%\.openclaw\gateway.cmd` |

### 默认不会直接删除的对象

扫描器会报告但不会默认删除：

- `AutoClaw` 一类伴生应用痕迹
- 不属于官方 OpenClaw 核心安装路径的浏览器桥接文件
- `.codex/skills` 和 `.agents/skills` 下的 skill 目录
- 只是文本上包含 `openclaw` 的普通文件

## 安全保证

- 不会因为路径里有 `openclaw` 这个单词就直接删除。
- `apply` 必须同时具备：
  - `--yes`
  - `--acknowledge-risk`
  - `--confirm "REMOVE OPENCLAW FROM THIS MACHINE"`
- 修改 shell init 文件时采用精确删行，并自动保留备份。
- 遇到 root 权限残留时，返回精确手动命令，不会谎称“已完全卸载”。
- 显式输出 `excluded`，让 agent 能说明哪些路径是有意跳过的。

## 快速开始

### 1. 只扫描

```bash
python3 scripts/openclaw_uninstall.py scan --json
```

### 2. 生成卸载计划

```bash
python3 scripts/openclaw_uninstall.py plan --json
```

### 3. 先 dry-run 演练

```bash
python3 scripts/openclaw_uninstall.py apply \
  --dry-run \
  --yes \
  --acknowledge-risk \
  --confirm "REMOVE OPENCLAW FROM THIS MACHINE" \
  --json
```

### 4. 正式执行

```bash
python3 scripts/openclaw_uninstall.py apply \
  --yes \
  --acknowledge-risk \
  --confirm "REMOVE OPENCLAW FROM THIS MACHINE" \
  --json
```

### 5. 验证剩余项

```bash
python3 scripts/openclaw_uninstall.py verify --json
```

## 常见工作流

### 本机完整清理

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

### 指定 profile 扫描

```bash
python3 scripts/openclaw_uninstall.py scan --profile rescue --json
```

### 对 synthetic filesystem 做测试

```bash
python3 scripts/openclaw_uninstall.py scan \
  --platform darwin \
  --home /Users/tester \
  --root /tmp/openclaw-fixture \
  --json
```

### 处理需要提权的残留

例如工具可能返回：

```bash
sudo rm -f "/usr/local/bin/openclaw"
sudo rm -rf "/usr/local/lib/node_modules/openclaw"
```

## 输出风格示例

扫描结果会同时表达“可删除项”和“边界项”：

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

这不是“多输出一点信息”，而是本项目的核心安全设计。

## 仓库结构

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

### 关键文件

- [SKILL.md](SKILL.md)：Agent 卸载流程主说明
- [agents/openai.yaml](agents/openai.yaml)：技能入口元数据
- [references/research-notes.md](references/research-notes.md)：调研依据
- [references/artifact-matrix.md](references/artifact-matrix.md)：官方痕迹与人工复核痕迹矩阵
- [references/safety-model.md](references/safety-model.md)：风险边界
- [scripts/openclaw_uninstall.py](scripts/openclaw_uninstall.py)：执行脚本
- [tests/test_openclaw_uninstall.py](tests/test_openclaw_uninstall.py)：回归测试

## 文档索引

- 调研说明：[references/research-notes.md](references/research-notes.md)
- Artifact 策略：[references/artifact-matrix.md](references/artifact-matrix.md)
- 安全模型：[references/safety-model.md](references/safety-model.md)
- 初版实现计划：[docs/plans/2026-03-31-openclaw-uninstall-skill.md](docs/plans/2026-03-31-openclaw-uninstall-skill.md)

## 开发

运行环境仅需 Python 3.9+。

测试命令：

```bash
python3 -m unittest discover -s tests -v
```

## 非目标

- 不是通用卸载器
- 不是“机器里所有含 openclaw 名称的东西都删掉”的脚本
- 不是伴生应用或企业自定义安装的自动处置器
- 不是因为目录名含 `openclaw` 就删除 Codex skills 的工具

## License

MIT。见 [LICENSE](LICENSE)。
