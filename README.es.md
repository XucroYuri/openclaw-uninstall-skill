# openclaw-uninstall-skill

[![CI](https://github.com/XucroYuri/openclaw-uninstall-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/XucroYuri/openclaw-uninstall-skill/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-informational)](#desarrollo)
[![Template Repository](https://img.shields.io/badge/github-template-success)](https://github.com/XucroYuri/openclaw-uninstall-skill/generate)

**Idiomas:** [English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [Español](README.es.md)

Skill para agentes y toolkit de validación con enfoque de alta seguridad para desinstalar OpenClaw en macOS, Linux y Windows sin convertir una limpieza local en una eliminación ciega y destructiva.

> El flujo por defecto siempre es:
> `scan -> plan -> explicit approval -> apply -> verify`

## Resumen rápido

| Tema | Qué hace este repositorio |
| --- | --- |
| Objetivo | Detectar y eliminar rastros oficiales de instalación de OpenClaw |
| Seguridad | No ejecuta acciones destructivas sin una confirmación fuerte |
| Plataformas | macOS, Linux, Windows |
| Enfoque | Separa rastros oficiales de artefactos ambiguos o adyacentes |
| Público | Constructores de agentes, operadores, usuarios avanzados y mantenedores |

## Por qué existe este proyecto

Desinstalar OpenClaw no es simplemente `rm -rf ~/.openclaw`.

Dependiendo de la instalación y del sistema, pueden quedar:

- servicios en segundo plano
  - macOS `launchd`
  - Linux `systemd --user`
  - Windows `schtasks`
  - fallback en la carpeta Startup de Windows
- directorios de estado por perfil como `~/.openclaw-dev` y `~/.openclaw-<profile>`
- hooks en shell init o completions
- wrappers de CLI en rutas de usuario o del sistema
- directorios de paquetes globales
- checkouts fuente o instalaciones desde git
- app bundles o archivos auxiliares específicos de plataforma

Este repositorio convierte esa superficie de desinstalación en un modelo de artefactos determinista y verificable.

## Qué incluye el toolkit

El proyecto combina dos piezas:

1. Un skill orientado a agentes en [SKILL.md](SKILL.md)
2. Un CLI determinista en [scripts/openclaw_uninstall.py](scripts/openclaw_uninstall.py)

Modos disponibles:

- `scan`: detecta rastros oficiales, artefactos de revisión manual y exclusiones
- `plan`: construye una secuencia ordenada de desinstalación
- `apply`: ejecuta cambios destructivos solo tras confirmación explícita
- `verify`: vuelve a escanear e informa qué sigue presente

## Cobertura de detección

### Rastros oficiales de OpenClaw

| Plataforma | Ejemplos |
| --- | --- |
| macOS | `~/Library/LaunchAgents/ai.openclaw.gateway.plist`, `~/.openclaw`, `/Applications/OpenClaw.app` |
| Linux | `~/.config/systemd/user/openclaw-gateway.service`, `~/.openclaw`, `~/.openclaw-<profile>` |
| Windows | `OpenClaw Gateway`, lanzadores en Startup, `%USERPROFILE%\.openclaw\gateway.cmd` |

### Objetos que no se eliminan por defecto

- rastros de apps acompañantes como `AutoClaw`
- puentes de navegador no documentados como parte del núcleo oficial
- directorios bajo `.codex/skills` y `.agents/skills`
- archivos que solo contienen la palabra `openclaw`

## Garantías de seguridad

- No elimina rutas solo por coincidencia textual.
- `apply` exige:
  - `--yes`
  - `--acknowledge-risk`
  - `--confirm "REMOVE OPENCLAW FROM THIS MACHINE"`
- Las ediciones de archivos de shell son quirúrgicas y guardan copia de seguridad.
- Si quedan rutas con privilegios, devuelve comandos manuales exactos.
- Las exclusiones se informan explícitamente como `excluded`.

## Inicio rápido

### 1. Solo escanear

```bash
python3 scripts/openclaw_uninstall.py scan --json
```

### 2. Generar el plan

```bash
python3 scripts/openclaw_uninstall.py plan --json
```

### 3. Ensayar con dry-run

```bash
python3 scripts/openclaw_uninstall.py apply \
  --dry-run \
  --yes \
  --acknowledge-risk \
  --confirm "REMOVE OPENCLAW FROM THIS MACHINE" \
  --json
```

### 4. Aplicar de verdad

```bash
python3 scripts/openclaw_uninstall.py apply \
  --yes \
  --acknowledge-risk \
  --confirm "REMOVE OPENCLAW FROM THIS MACHINE" \
  --json
```

### 5. Verificar remanentes

```bash
python3 scripts/openclaw_uninstall.py verify --json
```

## Flujos comunes

### Limpieza completa de una estación local

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

### Inspeccionar un perfil concreto

```bash
python3 scripts/openclaw_uninstall.py scan --profile rescue --json
```

### Probar contra un filesystem sintético

```bash
python3 scripts/openclaw_uninstall.py scan \
  --platform darwin \
  --home /Users/tester \
  --root /tmp/openclaw-fixture \
  --json
```

## Estructura del repositorio

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

### Archivos clave

- [SKILL.md](SKILL.md): flujo orientado a agentes
- [agents/openai.yaml](agents/openai.yaml): metadatos del skill
- [references/research-notes.md](references/research-notes.md): base de investigación
- [references/artifact-matrix.md](references/artifact-matrix.md): matriz de artefactos
- [references/safety-model.md](references/safety-model.md): límites de seguridad
- [scripts/openclaw_uninstall.py](scripts/openclaw_uninstall.py): CLI principal
- [tests/test_openclaw_uninstall.py](tests/test_openclaw_uninstall.py): pruebas de regresión

## Desarrollo

Sin dependencias de runtime fuera de Python 3.9+.

```bash
python3 -m unittest discover -s tests -v
```

## No objetivos

- no es un desinstalador genérico
- no es un script para borrar todo lo que contenga `openclaw`
- no sustituye la revisión humana para instalaciones privilegiadas o empresariales
- no sirve para eliminar skills de Codex solo porque el nombre del directorio contiene `openclaw`

## Licencia

MIT. Ver [LICENSE](LICENSE).
