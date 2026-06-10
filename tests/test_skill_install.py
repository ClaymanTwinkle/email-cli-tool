import pytest
from importlib.resources import files

from emailcli.skill_install import install_skill, load_skill_content


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
