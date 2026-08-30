from dataclasses import dataclass
from pathlib import Path

import yaml

from emailcli.exceptions import ConfigError


@dataclass(frozen=True)
class ImapConfig:
    host: str
    port: int
    username: str
    password: str
    encryption: str  # "ssl" | "starttls" | "none"


@dataclass(frozen=True)
class ConfigData:
    from_addr: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_encryption: str  # "starttls" | "ssl" | "none"
    imap: ImapConfig | None = None


def load_config(config_dir: Path | None = None) -> ConfigData:
    if config_dir is None:
        config_dir = Path.home() / ".emailcli"

    config_file = config_dir / "config.yaml"

    if not config_file.exists():
        raise ConfigError(
            f"Config file not found: {config_file}\n"
            "Run 'emailcli init' to create one."
        )

    with open(config_file) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ConfigError(f"Invalid config format in {config_file}")

    smtp = data.get("smtp", {})
    if not isinstance(smtp, dict):
        raise ConfigError("'smtp' must be a mapping")

    required = ["host", "username", "password"]
    for field in required:
        if field not in smtp:
            raise ConfigError(f"Missing required smtp field: '{field}'")

    imap_data = data.get("imap")
    imap = None
    if imap_data is not None:
        if not isinstance(imap_data, dict):
            raise ConfigError("'imap' must be a mapping")
        if "host" not in imap_data:
            raise ConfigError("Missing required imap field: 'host'")
        # Username/password default to the SMTP credentials (common case:
        # same account, e.g. a Gmail app password works for both).
        imap = ImapConfig(
            host=imap_data["host"],
            port=imap_data.get("port", 993),
            username=imap_data.get("username", smtp["username"]),
            password=imap_data.get("password", smtp["password"]),
            encryption=imap_data.get("encryption", "ssl"),
        )

    return ConfigData(
        from_addr=data.get("from", ""),
        smtp_host=smtp["host"],
        smtp_port=smtp.get("port", 587),
        smtp_username=smtp["username"],
        smtp_password=smtp["password"],
        smtp_encryption=smtp.get("encryption", "starttls"),
        imap=imap,
    )
