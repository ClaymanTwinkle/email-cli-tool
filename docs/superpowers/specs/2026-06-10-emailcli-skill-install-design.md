# emailcli skill install — Design

Date: 2026-06-10

## Goal

Add a CLI command that installs the `send-email` agent skill into both
Claude Code and Codex, so users don't have to manually place `SKILL.md`
into agent directories.

## Background

The `send-email` skill currently lives only as a hand-placed file at
`~/.claude/skills/send-email/SKILL.md`. It is a thin wrapper that drives the
`emailcli send` command. There is no skill content shipped inside the package
and no command to install it.

Claude Code and Codex both load skills from a directory containing a
`SKILL.md` file with YAML frontmatter (`name`, `description`). The format is
identical between the two agents, so a single bundled `SKILL.md` can serve
both — only the destination directory differs.

References:
- Codex Agent Skills: https://developers.openai.com/codex/skills
- Claude skills in Codex CLI: https://www.robert-glaser.de/claude-skills-in-codex-cli/

## Scope

- **In scope:** user-level install of the `send-email` skill to Claude and
  Codex via a new `emailcli skill install` command, default to both targets.
- **Out of scope:** `uninstall`, project-level install (`./.claude`,
  `./.codex`), Codex legacy `~/.codex/prompts` format, multi-file skills with
  `scripts/`/`references/`.

## Decisions

- **Install scope:** user-level only.
  - Claude: `~/.claude/skills/send-email/SKILL.md`
  - Codex: `~/.codex/skills/send-email/SKILL.md`
- **Default target:** both Claude and Codex. `--target` selects one.
- **Skill source:** bundle `SKILL.md` as package data (single source of
  truth), read at runtime via `importlib.resources`.

## Command Interface

```bash
emailcli skill install                 # default: claude + codex
emailcli skill install --target claude # Claude Code only
emailcli skill install --target codex  # Codex only
emailcli skill install --target all    # explicit both
```

- New click group `skill` with subcommand `install`.
- `--target` is a `click.Choice(["claude", "codex", "all"])`, default `all`.
- Idempotent: if the destination `SKILL.md` already exists it is overwritten
  (this is our managed skill). For each target, print a result line, e.g.
  `✓ Claude  ~/.claude/skills/send-email/SKILL.md  (updated)` /  `(created)`.
- Hidden `--home` option (mirrors the existing hidden `--config-dir` pattern)
  injects a base directory for tests.

## File Layout / Modules

- `src/emailcli/skills/send-email/SKILL.md` — canonical skill content (moved
  from the existing global copy; the repo becomes the single source of truth).
- `src/emailcli/skill_install.py` — install logic:
  - resolve targets from `--target`
  - compute destination dir per target under a given `home`
  - read bundled `SKILL.md` via `importlib.resources`
  - write it, creating parent dirs
  - return per-target results (target name, path, created-vs-updated)
  - signature accepts `home: Path` so tests can inject `tmp_path`
- `src/emailcli/cli.py` — thin click wiring only; delegates to
  `skill_install`.

## Packaging

Build backend is hatchling, packaging `src/emailcli`. Explicitly ensure the
skill data is included in the wheel:

```toml
[tool.hatch.build.targets.wheel.force-include]
"src/emailcli/skills" = "emailcli/skills"
```

(or the equivalent `artifacts` glob). Verified during implementation by
running `uv build` and inspecting the wheel for `emailcli/skills/send-email/SKILL.md`.

Runtime read:

```python
from importlib.resources import files
content = files("emailcli").joinpath("skills/send-email/SKILL.md").read_text(encoding="utf-8")
```

## Error Handling

- Each target is processed independently. If one write fails (e.g.
  permission error), report that target as failed and continue with the
  others.
- If any target failed, exit with a non-zero status; otherwise exit 0.
- Destination parent directories are created with
  `mkdir(parents=True, exist_ok=True)`.

## Testing (TDD)

Unit tests for `skill_install` (inject `tmp_path` as `home`):
- install `all` → both `~/.claude/.../SKILL.md` and `~/.codex/.../SKILL.md`
  exist and their content equals the bundled `SKILL.md`.
- `--target claude` → only the Claude file is created; Codex path absent.
- `--target codex` → only the Codex file is created.
- running install twice is idempotent (second run reports `updated`, content
  unchanged).

CLI-level tests via `click.testing.CliRunner` using the hidden `--home`
option pointed at `tmp_path`:
- default command writes both targets and prints both result lines.
- exit code is 0 on success.

## Documentation

Add a short section to `README.md` and `README_CN.md` documenting
`emailcli skill install` and what it does.
