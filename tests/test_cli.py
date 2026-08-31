from importlib.metadata import version as pkg_version
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from emailcli.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def config_home(tmp_path):
    config_dir = tmp_path / ".emailcli"
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
    return config_dir


@patch("emailcli.cli.SmtpSender")
def test_send_plain_text(mock_sender_cls, runner, config_home):
    mock_sender = MagicMock()
    mock_sender_cls.return_value = mock_sender

    result = runner.invoke(cli, [
        "send",
        "--to", "recipient@example.com",
        "--subject", "Hello",
        "--body", "Hello World",
        "--config-dir", str(config_home),
    ])
    assert result.exit_code == 0
    mock_sender.send.assert_called_once()


@patch("emailcli.cli.SmtpSender")
def test_send_html(mock_sender_cls, runner, config_home):
    mock_sender = MagicMock()
    mock_sender_cls.return_value = mock_sender

    result = runner.invoke(cli, [
        "send",
        "--to", "recipient@example.com",
        "--subject", "Report",
        "--html", "<h1>Report</h1>",
        "--config-dir", str(config_home),
    ])
    assert result.exit_code == 0
    mock_sender.send.assert_called_once()


@patch("emailcli.cli.SmtpSender")
def test_send_with_attachment(mock_sender_cls, runner, config_home, tmp_path):
    mock_sender = MagicMock()
    mock_sender_cls.return_value = mock_sender

    attach_file = tmp_path / "report.pdf"
    attach_file.write_bytes(b"%PDF-1.4")

    result = runner.invoke(cli, [
        "send",
        "--to", "recipient@example.com",
        "--subject", "Report",
        "--body", "See attached",
        "--attach", str(attach_file),
        "--config-dir", str(config_home),
    ])
    assert result.exit_code == 0
    mock_sender.send.assert_called_once()


@patch("emailcli.cli.SmtpSender")
def test_send_multiple_recipients(mock_sender_cls, runner, config_home):
    mock_sender = MagicMock()
    mock_sender_cls.return_value = mock_sender

    result = runner.invoke(cli, [
        "send",
        "--to", "a@example.com",
        "--to", "b@example.com",
        "--subject", "Multi",
        "--body", "Hello",
        "--config-dir", str(config_home),
    ])
    assert result.exit_code == 0


def test_send_no_body_or_html(runner, config_home):
    result = runner.invoke(cli, [
        "send",
        "--to", "recipient@example.com",
        "--subject", "Empty",
        "--config-dir", str(config_home),
    ])
    assert result.exit_code != 0
    assert "body" in result.output.lower() or "html" in result.output.lower()


def test_send_no_config(runner, tmp_path):
    result = runner.invoke(cli, [
        "send",
        "--to", "recipient@example.com",
        "--subject", "Hello",
        "--body", "text",
        "--config-dir", str(tmp_path / "nonexistent"),
    ])
    assert result.exit_code != 0
    assert "init" in result.output.lower()


@patch("emailcli.cli.SmtpSender")
def test_send_from_override(mock_sender_cls, runner, config_home):
    mock_sender = MagicMock()
    mock_sender_cls.return_value = mock_sender

    result = runner.invoke(cli, [
        "send",
        "--to", "recipient@example.com",
        "--subject", "Override",
        "--body", "text",
        "--from", "other@example.com",
        "--config-dir", str(config_home),
    ])
    assert result.exit_code == 0
    # Verify the message was built with overridden from
    sent_msg = mock_sender.send.call_args[0][0]
    assert sent_msg["From"] == "other@example.com"


@patch("emailcli.cli.SmtpSender")
def test_send_stdin_body(mock_sender_cls, runner, config_home):
    mock_sender = MagicMock()
    mock_sender_cls.return_value = mock_sender

    result = runner.invoke(cli, [
        "send",
        "--to", "recipient@example.com",
        "--subject", "Stdin",
        "--body", "-",
        "--config-dir", str(config_home),
    ], input="Hello from stdin\n")
    assert result.exit_code == 0
    mock_sender.send.assert_called_once()


def test_send_html_and_html_file_exclusive(runner, config_home, tmp_path):
    html_file = tmp_path / "template.html"
    html_file.write_text("<h1>Test</h1>")

    result = runner.invoke(cli, [
        "send",
        "--to", "recipient@example.com",
        "--subject", "Conflict",
        "--html", "<p>inline</p>",
        "--html-file", str(html_file),
        "--config-dir", str(config_home),
    ])
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output.lower() or "exclusive" in result.output.lower()


def test_init_creates_config(runner, tmp_path):
    config_dir = tmp_path / ".emailcli"
    result = runner.invoke(cli, [
        "init",
        "--config-dir", str(config_dir),
    ], input="me@163.com\nsmtp.163.com\n465\nme@163.com\nmypassword\nssl\nn\n")
    assert result.exit_code == 0
    assert (config_dir / "config.yaml").exists()


def test_init_sets_file_permissions(runner, tmp_path):
    import stat

    config_dir = tmp_path / ".emailcli"
    result = runner.invoke(cli, [
        "init",
        "--config-dir", str(config_dir),
    ], input="me@163.com\nsmtp.163.com\n465\nme@163.com\nmypassword\nssl\nn\n")
    assert result.exit_code == 0

    config_file = config_dir / "config.yaml"
    mode = config_file.stat().st_mode & 0o777
    assert mode == 0o600


def test_config_show(runner, config_home):
    result = runner.invoke(cli, [
        "config", "show",
        "--config-dir", str(config_home),
    ])
    assert result.exit_code == 0
    assert "smtp.example.com" in result.output
    assert "me@example.com" in result.output
    # Password should be masked
    assert "secret" not in result.output
    assert "***" in result.output


def test_config_show_no_config(runner, tmp_path):
    result = runner.invoke(cli, [
        "config", "show",
        "--config-dir", str(tmp_path / "nonexistent"),
    ])
    assert result.exit_code != 0


def test_version_option(runner):
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert pkg_version("email-cli-tool") in result.output


@pytest.fixture
def config_home_imap(tmp_path):
    config_dir = tmp_path / ".emailcli"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(yaml.dump({
        "from": "me@example.com",
        "smtp": {
            "host": "smtp.example.com",
            "port": 587,
            "username": "me@example.com",
            "password": "secret",
            "encryption": "starttls",
        },
        "imap": {
            "host": "imap.example.com",
        },
    }))
    return config_dir


def _sample_incoming_message(attachments=None):
    import email
    import email.policy
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["From"] = "sender@example.com"
    msg["To"] = "me@example.com"
    msg["Subject"] = "Incoming"
    msg["Date"] = "Mon, 31 Aug 2026 10:00:00 +0800"
    msg.set_content("Incoming body")
    for name, data in (attachments or []):
        msg.add_attachment(
            data, maintype="application", subtype="octet-stream", filename=name
        )
    return email.message_from_bytes(bytes(msg), policy=email.policy.default)


@patch("emailcli.cli.ImapReceiver")
def test_watch_receives_message(mock_receiver_cls, runner, config_home_imap):
    mock_receiver = MagicMock()
    mock_receiver.wait_for_message.return_value = _sample_incoming_message()
    mock_receiver_cls.return_value = mock_receiver

    result = runner.invoke(cli, ["watch", "--config-dir", str(config_home_imap)])

    assert result.exit_code == 0
    assert "Subject: Incoming" in result.output
    assert "Incoming body" in result.output
    # IMAP credentials fall back to SMTP ones
    mock_receiver_cls.assert_called_once_with(
        host="imap.example.com",
        port=993,
        username="me@example.com",
        password="secret",
        encryption="ssl",
    )


@patch("emailcli.cli.ImapReceiver")
def test_watch_saves_attachments(mock_receiver_cls, runner, config_home_imap, tmp_path):
    mock_receiver = MagicMock()
    mock_receiver.wait_for_message.return_value = _sample_incoming_message(
        attachments=[("report.pdf", b"%PDF-1.4")]
    )
    mock_receiver_cls.return_value = mock_receiver

    dest = tmp_path / "downloads"
    result = runner.invoke(cli, [
        "watch",
        "--config-dir", str(config_home_imap),
        "--save-attachments", str(dest),
    ])

    assert result.exit_code == 0
    assert (dest / "report.pdf").read_bytes() == b"%PDF-1.4"


@patch("emailcli.cli.ImapReceiver")
def test_watch_timeout_exits_2(mock_receiver_cls, runner, config_home_imap):
    mock_receiver = MagicMock()
    mock_receiver.wait_for_message.return_value = None
    mock_receiver_cls.return_value = mock_receiver

    result = runner.invoke(cli, [
        "watch", "--timeout", "1", "--config-dir", str(config_home_imap),
    ])

    assert result.exit_code == 2
    assert "Timed out" in result.output


def test_watch_without_imap_config(runner, config_home):
    result = runner.invoke(cli, ["watch", "--config-dir", str(config_home)])

    assert result.exit_code == 1
    assert "IMAP" in result.output


@patch("emailcli.cli.ImapReceiver")
def test_watch_passes_options(mock_receiver_cls, runner, config_home_imap):
    mock_receiver = MagicMock()
    mock_receiver.wait_for_message.return_value = _sample_incoming_message()
    mock_receiver_cls.return_value = mock_receiver

    result = runner.invoke(cli, [
        "watch",
        "--timeout", "300",
        "--poll-interval", "5",
        "--mailbox", "Work",
        "--config-dir", str(config_home_imap),
    ])

    assert result.exit_code == 0
    mock_receiver.wait_for_message.assert_called_once_with(
        mailbox="Work", timeout=300.0, poll_interval=5.0
    )


@patch("emailcli.cli.ImapReceiver")
def test_list_prints_rows(mock_receiver_cls, runner, config_home_imap):
    mock_receiver = MagicMock()
    mock_receiver.list_messages.return_value = [
        (9, _sample_incoming_message()),
        (7, _sample_incoming_message()),
    ]
    mock_receiver_cls.return_value = mock_receiver

    result = runner.invoke(cli, ["list", "--config-dir", str(config_home_imap)])

    assert result.exit_code == 0
    lines = [line for line in result.output.splitlines() if line]
    assert lines[0].startswith("9\t")
    assert "sender@example.com" in lines[0]
    assert "Incoming" in lines[0]
    mock_receiver.list_messages.assert_called_once_with(mailbox="INBOX", limit=10)


@patch("emailcli.cli.ImapReceiver")
def test_read_latest(mock_receiver_cls, runner, config_home_imap):
    mock_receiver = MagicMock()
    mock_receiver.get_message.return_value = (9, _sample_incoming_message())
    mock_receiver_cls.return_value = mock_receiver

    result = runner.invoke(cli, ["read", "--config-dir", str(config_home_imap)])

    assert result.exit_code == 0
    assert "Subject: Incoming" in result.output
    assert "Incoming body" in result.output
    mock_receiver.get_message.assert_called_once_with(uid=None, mailbox="INBOX")


@patch("emailcli.cli.ImapReceiver")
def test_read_by_uid_saves_attachments(mock_receiver_cls, runner, config_home_imap, tmp_path):
    mock_receiver = MagicMock()
    mock_receiver.get_message.return_value = (
        9, _sample_incoming_message(attachments=[("report.pdf", b"%PDF-1.4")])
    )
    mock_receiver_cls.return_value = mock_receiver

    dest = tmp_path / "downloads"
    result = runner.invoke(cli, [
        "read", "9",
        "--config-dir", str(config_home_imap),
        "--save-attachments", str(dest),
    ])

    assert result.exit_code == 0
    assert (dest / "report.pdf").read_bytes() == b"%PDF-1.4"
    mock_receiver.get_message.assert_called_once_with(uid=9, mailbox="INBOX")


@patch("emailcli.cli.ImapReceiver")
def test_read_empty_mailbox_exits_2(mock_receiver_cls, runner, config_home_imap):
    mock_receiver = MagicMock()
    mock_receiver.get_message.return_value = None
    mock_receiver_cls.return_value = mock_receiver

    result = runner.invoke(cli, ["read", "--config-dir", str(config_home_imap)])

    assert result.exit_code == 2
    assert "No messages" in result.output


def test_init_with_imap(runner, tmp_path):
    config_dir = tmp_path / ".emailcli"
    result = runner.invoke(cli, [
        "init",
        "--config-dir", str(config_dir),
    ], input=(
        "me@163.com\nsmtp.163.com\n465\nme@163.com\nmypassword\nssl\n"  # smtp
        "y\nimap.163.com\n993\nme@163.com\n\nssl\n"  # imap, empty password = reuse
    ))
    assert result.exit_code == 0

    data = yaml.safe_load((config_dir / "config.yaml").read_text())
    assert data["imap"]["host"] == "imap.163.com"
    assert data["imap"]["port"] == 993
    assert "password" not in data["imap"]  # falls back to smtp password


def test_config_show_with_imap(runner, config_home_imap):
    result = runner.invoke(cli, ["config", "show", "--config-dir", str(config_home_imap)])
    assert result.exit_code == 0
    assert "imap.example.com" in result.output
    assert "secret" not in result.output
