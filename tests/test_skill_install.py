from importlib.resources import files
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from emailcli.cli import cli
from emailcli.skill_install import InstallResult, install_skill, load_skill_content


def test_bundled_skill_md_is_packaged():
    content = files("emailcli").joinpath("skills/send-email/SKILL.md").read_text(encoding="utf-8")
    assert content.startswith("---")
    assert "name: send-email" in content
    assert "emailcli send" in content


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


def test_install_unknown_target_raises(tmp_path):
    with pytest.raises(ValueError):
        install_skill(tmp_path, ["vim"])


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


def test_cli_skill_install_failure_exit_code(tmp_path):
    failed = [InstallResult("claude", tmp_path / "SKILL.md", "failed", "boom")]
    runner = CliRunner()
    with patch("emailcli.skill_install.install_skill", return_value=failed):
        result = runner.invoke(cli, ["skill", "install", "--home", str(tmp_path)])
    assert result.exit_code == 1
