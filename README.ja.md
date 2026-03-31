# openclaw-uninstall-skill

[![CI](https://github.com/XucroYuri/openclaw-uninstall-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/XucroYuri/openclaw-uninstall-skill/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-informational)](#開発)
[![Template Repository](https://img.shields.io/badge/github-template-success)](https://github.com/XucroYuri/openclaw-uninstall-skill/generate)

**言語:** [English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [Español](README.es.md)

macOS、Linux、Windows 上の OpenClaw を安全に削除するための高安全性 Agent Skill と検証ツールキットです。単純な文字列一致で削除対象を広げるのではなく、根拠のあるアンインストール計画を組み立てることを目的としています。

> このリポジトリの基本フローは常に次の順序です。
> `scan -> plan -> explicit approval -> apply -> verify`

## 概要

| 項目 | 内容 |
| --- | --- |
| 目的 | OpenClaw のインストール痕跡を検出し、安全に削除・検証する |
| 安全方針 | 強い確認フレーズなしでは destructive apply を実行しない |
| 対応 OS | macOS、Linux、Windows |
| 設計の中心 | 公式 OpenClaw 痕跡と曖昧な周辺痕跡を分離する |
| 想定利用者 | Agent 開発者、運用担当者、上級ユーザー、保守担当者 |

## なぜ必要か

OpenClaw のアンインストールは `rm -rf ~/.openclaw` だけでは終わりません。

環境によっては以下のような痕跡が残ります。

- バックグラウンドサービス
  - macOS `launchd`
  - Linux `systemd --user`
  - Windows `schtasks`
  - Windows Startup-folder フォールバック
- `~/.openclaw-dev` や `~/.openclaw-<profile>` などの profile 別状態ディレクトリ
- shell init / completion の注入
- ユーザーまたはシステム bin 配下の wrapper
- グローバル package ディレクトリ
- source checkout / git install の残骸
- macOS app bundle や補助ファイル

このリポジトリは、そうしたアンインストール対象をテスト可能な artifact モデルとして定義します。

## このツールキットがすること

本プロジェクトは 2 つの要素で構成されます。

1. [SKILL.md](SKILL.md) の agent 向け skill
2. [scripts/openclaw_uninstall.py](scripts/openclaw_uninstall.py) の決定論的 CLI

CLI のモード:

- `scan`: 公式痕跡、手動確認対象、除外対象を検出
- `plan`: 検出結果から削除順序を構築
- `apply`: 強確認後のみ destructive 操作を実行
- `verify`: 再スキャンして残存物を報告

## 検出範囲

### 公式 OpenClaw 痕跡

| プラットフォーム | 例 |
| --- | --- |
| macOS | `~/Library/LaunchAgents/ai.openclaw.gateway.plist`、`~/.openclaw`、`/Applications/OpenClaw.app` |
| Linux | `~/.config/systemd/user/openclaw-gateway.service`、`~/.openclaw`、`~/.openclaw-<profile>` |
| Windows | `OpenClaw Gateway`、Startup-folder ランチャー、`%USERPROFILE%\.openclaw\gateway.cmd` |

### デフォルトでは自動削除しないもの

- `AutoClaw` のような周辺アプリ痕跡
- 公式 OpenClaw コアのドキュメントに含まれないブラウザ連携ファイル
- `.codex/skills` と `.agents/skills` 配下の skill ディレクトリ
- 単に `openclaw` という文字列を含むだけの一般ファイル

## 安全保証

- 単なるキーワード一致だけで削除しません。
- `apply` には次の 3 つが必須です。
  - `--yes`
  - `--acknowledge-risk`
  - `--confirm "REMOVE OPENCLAW FROM THIS MACHINE"`
- shell init の編集は最小差分で行い、バックアップを残します。
- 権限不足で削除できない場合、正確な手動コマンドを返します。
- `excluded` を明示的に出力し、意図的に触らなかった対象を説明できます。

## クイックスタート

### 1. スキャンのみ

```bash
python3 scripts/openclaw_uninstall.py scan --json
```

### 2. アンインストール計画を作成

```bash
python3 scripts/openclaw_uninstall.py plan --json
```

### 3. dry-run で確認

```bash
python3 scripts/openclaw_uninstall.py apply \
  --dry-run \
  --yes \
  --acknowledge-risk \
  --confirm "REMOVE OPENCLAW FROM THIS MACHINE" \
  --json
```

### 4. 実際に適用

```bash
python3 scripts/openclaw_uninstall.py apply \
  --yes \
  --acknowledge-risk \
  --confirm "REMOVE OPENCLAW FROM THIS MACHINE" \
  --json
```

### 5. 残存物を検証

```bash
python3 scripts/openclaw_uninstall.py verify --json
```

## よくある使い方

### ローカル端末の完全クリーンアップ

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

### 特定 profile の確認

```bash
python3 scripts/openclaw_uninstall.py scan --profile rescue --json
```

### synthetic filesystem に対するテスト

```bash
python3 scripts/openclaw_uninstall.py scan \
  --platform darwin \
  --home /Users/tester \
  --root /tmp/openclaw-fixture \
  --json
```

## リポジトリ構成

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

### 主なファイル

- [SKILL.md](SKILL.md): agent 向けワークフロー
- [agents/openai.yaml](agents/openai.yaml): skill メタデータ
- [references/research-notes.md](references/research-notes.md): 調査根拠
- [references/artifact-matrix.md](references/artifact-matrix.md): 削除対象と手動確認対象の区分
- [references/safety-model.md](references/safety-model.md): 安全境界
- [scripts/openclaw_uninstall.py](scripts/openclaw_uninstall.py): 実行 CLI
- [tests/test_openclaw_uninstall.py](tests/test_openclaw_uninstall.py): 回帰テスト

## 開発

Python 3.9+ 以外の依存はありません。

```bash
python3 -m unittest discover -s tests -v
```

## 非対象

- 汎用アンインストーラではありません
- `openclaw` を含むすべてのパスを削除するツールではありません
- 周辺アプリや企業独自構成を自動処理するものではありません
- フォルダ名に `openclaw` があるだけで Codex skills を削除するものではありません

## License

MIT。詳細は [LICENSE](LICENSE) を参照してください。
