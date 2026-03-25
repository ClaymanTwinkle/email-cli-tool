class EmailCliError(Exception):
    """Base exception for emailcli."""


class ConfigError(EmailCliError):
    """Configuration file errors."""


class MessageError(EmailCliError):
    """Email message building errors."""


class SendError(EmailCliError):
    """Email sending errors."""
