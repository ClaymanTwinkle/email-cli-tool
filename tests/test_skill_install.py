from importlib.resources import files


def test_bundled_skill_md_is_packaged():
    content = files("emailcli").joinpath("skills/send-email/SKILL.md").read_text(encoding="utf-8")
    assert content.startswith("---")
    assert "name: send-email" in content
    assert "emailcli send" in content
