import os
from pathlib import Path

import pytest
import yaml

from emailcli.config import load_config, ConfigData


@pytest.fixture
def config_dir(tmp_path):
    return tmp_path / ".emailcli"


@pytest.fixture
def valid_config(config_dir):
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(yaml.dump({
        "from": "me@example.com",
        "smtp": {
            "host": "smtp.example.com",
            "port": 587,
            "username": "me@example.com",
            "password": "secret",
            "encryption": "starttls",
        },
    }))
    return config_file


def test_load_valid_config(valid_config, config_dir):
    config = load_config(config_dir)
    assert config.from_addr == "me@example.com"
    assert config.smtp_host == "smtp.example.com"
    assert config.smtp_port == 587
    assert config.smtp_username == "me@example.com"
    assert config.smtp_password == "secret"
    assert config.smtp_encryption == "starttls"


def test_load_config_file_not_found(config_dir):
    from emailcli.exceptions import ConfigError

    with pytest.raises(ConfigError, match="not found"):
        load_config(config_dir)


def test_load_config_missing_smtp_host(config_dir):
    from emailcli.exceptions import ConfigError

    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(yaml.dump({
        "from": "me@example.com",
        "smtp": {"port": 587},
    }))
    with pytest.raises(ConfigError, match="host"):
        load_config(config_dir)


def test_load_config_ssl_encryption(config_dir):
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(yaml.dump({
        "from": "me@example.com",
        "smtp": {
            "host": "smtp.163.com",
            "port": 465,
            "username": "me@163.com",
            "password": "authcode",
            "encryption": "ssl",
        },
    }))
    config = load_config(config_dir)
    assert config.smtp_encryption == "ssl"
    assert config.smtp_port == 465


def test_load_config_without_imap(valid_config, config_dir):
    config = load_config(config_dir)
    assert config.imap is None


def test_load_config_with_imap(config_dir):
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(yaml.dump({
        "from": "me@example.com",
        "smtp": {
            "host": "smtp.example.com",
            "username": "me@example.com",
            "password": "secret",
        },
        "imap": {
            "host": "imap.example.com",
            "port": 143,
            "username": "other@example.com",
            "password": "imap-secret",
            "encryption": "starttls",
        },
    }))
    config = load_config(config_dir)
    assert config.imap is not None
    assert config.imap.host == "imap.example.com"
    assert config.imap.port == 143
    assert config.imap.username == "other@example.com"
    assert config.imap.password == "imap-secret"
    assert config.imap.encryption == "starttls"


def test_load_config_imap_defaults_from_smtp(config_dir):
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(yaml.dump({
        "from": "me@example.com",
        "smtp": {
            "host": "smtp.example.com",
            "username": "me@example.com",
            "password": "secret",
        },
        "imap": {
            "host": "imap.example.com",
        },
    }))
    config = load_config(config_dir)
    assert config.imap.port == 993
    assert config.imap.encryption == "ssl"
    assert config.imap.username == "me@example.com"
    assert config.imap.password == "secret"


def test_load_config_imap_missing_host(config_dir):
    from emailcli.exceptions import ConfigError

    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(yaml.dump({
        "from": "me@example.com",
        "smtp": {
            "host": "smtp.example.com",
            "username": "me@example.com",
            "password": "secret",
        },
        "imap": {"port": 993},
    }))
    with pytest.raises(ConfigError, match="imap.*host"):
        load_config(config_dir)
