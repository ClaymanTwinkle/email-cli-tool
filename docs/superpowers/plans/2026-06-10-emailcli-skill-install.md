# emailcli skill install Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `emailcli skill install` command that installs the bundled `send-email` agent skill into Claude Code (`~/.claude/skills`) and Codex (`~/.codex/skills`), defaulting to both.

**Architecture:** Ship `SKILL.md` as package data inside `emailcli`. A standalone `skill_install` module reads the bundled file via `importlib.resources` and writes it to per-target user-level directories. `cli.py` adds a thin `skill install` click command that delegates to the module.

**Tech Stack:** Python 3.10+, click, hatchling (build), pytest + click.testing.CliRunner.

---

## File Structure

- **Create** `src/emailcli/skills/send-email/SKILL.md` — canonical skill content (single source of truth, shipped as package data).
- **Create** `src/emailcli/skill_install.py` — install logic: load bundled content, compute destinations, write per target, return results.
- **Modify** `pyproject.toml` — force-include the `skills/` data dir into the wheel.
- **Modify** `src/emailcli/cli.py` — add the `skill` group + `install` subcommand.
- **Create** `tests/test_skill_install.py` — unit tests for packaging + install logic + CLI command.
- **Modify** `README.md`, `README_CN.md` — document the command.

Reference spec: `docs/superpowers/specs/2026-06-10-emailcli-skill-install-design.md`

---

### Task 1: Bundle the skill content as package data

**Files:**
- Create: `src/emailcli/skills/send-email/SKILL.md`
- Modify: `pyproject.toml:41-42`
- Test: `tests/test_skill_install.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_skill_install.py`:

```python
from importlib.resources import files


def test_bundled_skill_md_is_packaged():
    content = files("emailcli").joinpath("skills/send-email/SKILL.md").read_text(encoding="utf-8")
    assert content.startswith("---")
    assert "name: send-email" in content
    assert "emailcli send" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_skill_install.py::test_bundled_skill_md_is_packaged -v`
Expected: FAIL — `FileNotFoundError` / `IsADirectoryError` (the data file does not exist yet).

- [ ] **Step 3: Create the bundled SKILL.md**

Create `src/emailcli/skills/send-email/SKILL.md` with exactly this content:

````markdown
---
name: send-email
description: "Send emails with attachments via emailcli. Supports plain text, HTML, multiple recipients, and file/image attachments."
---

# Send Email

Send emails directly from Claude Code using the `emailcli` CLI tool.

## Usage

Invoke with `/send-email` followed by natural language describing what to send:

```
/send-email 发送测试邮件给 test@example.com
/send-email 把 report.pdf 发给 alice@example.com，主题是"月度报告"
/send-email 给 a@example.com 和 b@example.com 发一封 HTML 邮件
```

## Workflow

### 1. Parse user intent

Extract from the user's message:
- **Recipients** (`--to`): one or more email addresses
- **Subject** (`--subject`): email subject line
- **Body** (`--body` or `--html`): email content
- **Attachments** (`--attach`): file paths if mentioned

### 2. Validate inputs

- If recipients are missing, ask the user.
- If subject is missing, ask the user.
- If body is missing, ask the user.
- If attachments are mentioned, verify the files exist using Glob or ls before sending.

### 3. Send (no confirmation needed)

Run the `emailcli send` command with the appropriate arguments.

```bash
emailcli send \
  --to recipient@example.com \
  --subject "测试邮件" \
  --body "Hello World" \
  --attach report.pdf \
  --attach photo.png
```

### 5. Report result

Tell the user whether the email was sent successfully or if there was an error.

## Command Reference

```bash
# Plain text
emailcli send --to <email> --subject <subject> --body <text>

# HTML
emailcli send --to <email> --subject <subject> --html <html>

# HTML from file
emailcli send --to <email> --subject <subject> --html-file <path>

# With attachments (repeatable)
emailcli send --to <email> --subject <subject> --body <text> --attach <file>

# Multiple recipients (repeatable)
emailcli send --to <email1> --to <email2> --subject <subject> --body <text>

# Override sender
emailcli send --to <email> --subject <subject> --body <text> --from <sender>

# Body from stdin
echo "content" | emailcli send --to <email> --subject <subject> --body -
```

## Important

- Do NOT ask for confirmation — send directly once inputs are ready.
- Verify attachment files exist before running the command.
- If the command fails, show the error message to the user.
- The tool must be configured first via `emailcli init`. If sending fails with a config error, tell the user to run `emailcli init`.
````

- [ ] **Step 4: Force-include the data dir in the wheel**

In `pyproject.toml`, the wheel target currently is:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/emailcli"]
```

Replace it with:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/emailcli"]

[tool.hatch.build.targets.wheel.force-include]
"src/emailcli/skills" = "emailcli/skills"
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_skill_install.py::test_bundled_skill_md_is_packaged -v`
Expected: PASS.

- [ ] **Step 6: Verify the wheel actually contains the data file**

Run: `uv build 2>/dev/null && python -c "import zipfile,glob; w=sorted(glob.glob('dist/*.whl'))[-1]; names=zipfile.ZipFile(w).namelist(); print('emailcli/skills/send-email/SKILL.md' in names)"`
Expected: prints `True`. Then clean up: `rm -rf dist`.

- [ ] **Step 7: Commit**

```bash
git add src/emailcli/skills/send-email/SKILL.md pyproject.toml tests/test_skill_install.py
git commit -m "feat: bundle send-email SKILL.md as package data

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Implement the install logic in `skill_install.py`

**Files:**
- Create: `src/emailcli/skill_install.py`
- Test: `tests/test_skill_install.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_skill_install.py`:

```python
from emailcli.skill_install import install_skill, load_skill_content


def test_install_all_writes_both_targets(tmp_path):
    results = install_skill(tmp_path, ["claude", "codex"])

    claude_path = tmp_path / ".claude" / "skills" / "send-email" / "SKILL.md"
    codex_path = tmp_path / ".codex" / "skills" / "send-email" / "SKILL.md"
    bundled = load_skill_content()

    assert claude_path.read_text(encoding="utf-8") == bundled
    assert codex_path.read_text(encoding="utf-8") == bundled
    assert {r.target for r in results} == {"claude", "codex"}
    assert all(r.status == "created" for r in results)


def test_install_claude_only(tmp_path):
    install_skill(tmp_path, ["claude"])

    assert (tmp_path / ".claude" / "skills" / "send-email" / "SKILL.md").exists()
    assert not (tmp_path / ".codex").exists()


def test_install_is_idempotent(tmp_path):
    install_skill(tmp_path, ["claude"])
    results = install_skill(tmp_path, ["claude"])

    assert results[0].status == "updated"
    path = tmp_path / ".claude" / "skills" / "send-email" / "SKILL.md"
    assert path.read_text(encoding="utf-8") == load_skill_content()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_skill_install.py -k "install" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'emailcli.skill_install'`.

- [ ] **Step 3: Write the implementation**

Create `src/emailcli/skill_install.py`:

```python
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

SKILL_NAME = "send-email"

# target name -> home subdirectory that holds the agent's skills
TARGET_HOME_DIRS = {
    "claude": ".claude",
    "codex": ".codex",
}

# human-facing label per target
TARGET_LABELS = {
    "claude": "Claude",
    "codex": "Codex",
}


def load_skill_content() -> str:
    """Read the bundled SKILL.md shipped as package data."""
    return (
        files("emailcli")
        .joinpath(f"skills/{SKILL_NAME}/SKILL.md")
        .read_text(encoding="utf-8")
    )


def skill_dest(home: Path, target: str) -> Path:
    """Destination SKILL.md path for a target under the given home dir."""
    return home / TARGET_HOME_DIRS[target] / "skills" / SKILL_NAME / "SKILL.md"


@dataclass
class InstallResult:
    target: str
    path: Path
    status: str  # "created" | "updated" | "failed"
    error: str | None = None


def install_skill(home: Path, targets: list[str]) -> list[InstallResult]:
    """Write the bundled skill into each target's user-level skills dir.

    Each target is handled independently; a write failure on one target is
    recorded and does not stop the others.
    """
    content = load_skill_content()
    results: list[InstallResult] = []
    for target in targets:
        dest = skill_dest(home, target)
        try:
            existed = dest.exists()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            results.append(
                InstallResult(target, dest, "updated" if existed else "created")
            )
        except OSError as exc:
            results.append(InstallResult(target, dest, "failed", str(exc)))
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_skill_install.py -k "install" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/emailcli/skill_install.py tests/test_skill_install.py
git commit -m "feat: add skill_install module for writing SKILL.md to agent dirs

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Wire up the `skill install` CLI command

**Files:**
- Modify: `src/emailcli/cli.py` (add imports near `cli.py:1-9`; add new group/command after the `config` group at `cli.py:121-142`)
- Test: `tests/test_skill_install.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_skill_install.py`:

```python
from click.testing import CliRunner

from emailcli.cli import cli


def test_cli_skill_install_default_writes_both(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["skill", "install", "--home", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / ".claude" / "skills" / "send-email" / "SKILL.md").exists()
    assert (tmp_path / ".codex" / "skills" / "send-email" / "SKILL.md").exists()
    assert "Claude" in result.output
    assert "Codex" in result.output


def test_cli_skill_install_target_codex(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        cli, ["skill", "install", "--target", "codex", "--home", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert (tmp_path / ".codex" / "skills" / "send-email" / "SKILL.md").exists()
    assert not (tmp_path / ".claude").exists()


def test_cli_skill_install_invalid_target(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        cli, ["skill", "install", "--target", "vim", "--home", str(tmp_path)]
    )

    assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_skill_install.py -k "cli_skill" -v`
Expected: FAIL — `No such command 'skill'` (exit code 2 / usage error), so the `exit_code == 0` assertions fail.

- [ ] **Step 3: Add the import**

In `src/emailcli/cli.py`, add to the import block (after the existing `from emailcli.sender import SmtpSender` line):

```python
from emailcli import skill_install
```

- [ ] **Step 4: Add the `skill` group and `install` command**

In `src/emailcli/cli.py`, after the `config_group`'s `show` command (end of file), append:

```python
@cli.group(name="skill")
def skill_group():
    """Manage the emailcli agent skill."""


@skill_group.command(name="install")
@click.option(
    "--target",
    type=click.Choice(["claude", "codex", "all"]),
    default="all",
    show_default=True,
    help="Which agent to install the skill for.",
)
@click.option("--home", default=None, type=click.Path(), hidden=True, help="Home directory (for testing).")
def install(target, home):
    """Install the send-email skill into Claude Code and/or Codex."""
    home_dir = Path(home) if home else Path.home()
    targets = ["claude", "codex"] if target == "all" else [target]

    results = skill_install.install_skill(home_dir, targets)

    for r in results:
        label = skill_install.TARGET_LABELS[r.target]
        if r.status == "failed":
            click.echo(f"✗ {label}\t{r.path}\t(failed: {r.error})", err=True)
        else:
            click.echo(f"✓ {label}\t{r.path}\t({r.status})")

    if any(r.status == "failed" for r in results):
        raise SystemExit(1)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_skill_install.py -k "cli_skill" -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Run the whole test file**

Run: `uv run pytest tests/test_skill_install.py -v`
Expected: PASS (all tests).

- [ ] **Step 7: Commit**

```bash
git add src/emailcli/cli.py tests/test_skill_install.py
git commit -m "feat: add 'emailcli skill install' command

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Document the command

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`

- [ ] **Step 1: Add a section to `README.md`**

In `README.md`, after the `### emailcli config show` block and before `## Configuration`, insert:

````markdown
### `emailcli skill install`

Install the `send-email` agent skill so Claude Code or Codex can send mail for you.

```bash
# Install for both Claude Code and Codex (default)
emailcli skill install

# Only one agent
emailcli skill install --target claude
emailcli skill install --target codex
```

Writes `SKILL.md` to `~/.claude/skills/send-email/` and/or `~/.codex/skills/send-email/`.
````

- [ ] **Step 2: Add the equivalent section to `README_CN.md`**

In `README_CN.md`, add a matching section in the command reference area (Chinese):

````markdown
### `emailcli skill install`

安装 `send-email` 技能，让 Claude Code 或 Codex 可以直接帮你发邮件。

```bash
# 默认同时安装到 Claude Code 和 Codex
emailcli skill install

# 只装其中一个
emailcli skill install --target claude
emailcli skill install --target codex
```

会把 `SKILL.md` 写入 `~/.claude/skills/send-email/` 和/或 `~/.codex/skills/send-email/`。
````

- [ ] **Step 3: Commit**

```bash
git add README.md README_CN.md
git commit -m "docs: document 'emailcli skill install' command

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review Notes

- **Spec coverage:** command interface (Task 3), bundled package data (Task 1), `skill_install` module + per-target independent error handling (Task 2), user-level paths for Claude/Codex (Task 2 `skill_dest`), idempotent overwrite with created/updated reporting (Task 2 + 3), hidden `--home` test hook (Task 3), packaging via force-include + wheel verification (Task 1), docs (Task 4). All spec sections mapped.
- **Type consistency:** `install_skill(home, targets) -> list[InstallResult]`, `InstallResult(target, path, status, error)`, `load_skill_content()`, `skill_dest()`, `TARGET_LABELS` used identically across module and CLI.
- **Out of scope (per spec):** no `uninstall`, no project-level install, no Codex legacy prompt format.
