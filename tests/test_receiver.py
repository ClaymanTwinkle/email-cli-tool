from email.message import EmailMessage
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from emailcli.exceptions import ReceiveError
from emailcli.receiver import ImapReceiver, extract_body, save_attachments


def make_raw_message(body="Hello", html=None, attachments=None):
    msg = EmailMessage()
    msg["From"] = "sender@example.com"
    msg["To"] = "me@example.com"
    msg["Subject"] = "Test mail"
    if body:
        msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")
    for name, data in (attachments or []):
        msg.add_attachment(
            data, maintype="application", subtype="octet-stream", filename=name
        )
    return bytes(msg)


def make_conn(search_results, raw=None, uidnext=100):
    """Mock IMAP connection. search_results: list of SEARCH data bytes per poll."""
    conn = MagicMock()
    conn.status.return_value = ("OK", [b"INBOX (UIDNEXT %d)" % uidnext])
    conn.select.return_value = ("OK", [b"3"])
    conn.noop.return_value = ("OK", [b""])
    results = iter(search_results)

    def uid(cmd, *args):
        if cmd == "search":
            return ("OK", [next(results)])
        if cmd == "fetch":
            return ("OK", [(b"1 (RFC822 {123}", raw), b")"])
        raise AssertionError(f"unexpected uid command: {cmd}")

    conn.uid.side_effect = uid
    return conn


def make_receiver():
    return ImapReceiver(
        host="imap.example.com",
        port=993,
        username="me@example.com",
        password="secret",
        encryption="ssl",
    )


@patch("emailcli.receiver.imaplib.IMAP4_SSL")
def test_wait_returns_new_message(mock_imap_cls):
    raw = make_raw_message(body="Hello there")
    conn = make_conn([b"100"], raw=raw)
    mock_imap_cls.return_value = conn

    msg = make_receiver().wait_for_message(timeout=5, poll_interval=0.01)

    assert msg is not None
    assert msg["Subject"] == "Test mail"
    conn.login.assert_called_once_with("me@example.com", "secret")
    conn.uid.assert_any_call("search", "UID", "100:*")


@patch("emailcli.receiver.imaplib.IMAP4_SSL")
def test_wait_ignores_existing_mail(mock_imap_cls):
    # "100:*" matches the last existing message (UID 99) even though it is
    # older than UIDNEXT; it must be ignored, then UID 100 arrives.
    raw = make_raw_message()
    conn = make_conn([b"99", b"99 100"], raw=raw)
    mock_imap_cls.return_value = conn

    msg = make_receiver().wait_for_message(timeout=5, poll_interval=0.01)

    assert msg is not None
    # Fetched the new message, not the old one
    conn.uid.assert_any_call("fetch", "100", "(RFC822)")


@patch("emailcli.receiver.imaplib.IMAP4_SSL")
def test_wait_timeout_returns_none(mock_imap_cls):
    conn = make_conn([b"", b"", b"", b"", b""])
    mock_imap_cls.return_value = conn

    msg = make_receiver().wait_for_message(timeout=0.03, poll_interval=0.01)

    assert msg is None
    conn.logout.assert_called_once()


@patch("emailcli.receiver.imaplib.IMAP4_SSL")
def test_connect_failure_raises_receive_error(mock_imap_cls):
    mock_imap_cls.side_effect = OSError("connection refused")

    with pytest.raises(ReceiveError, match="connect"):
        make_receiver().wait_for_message(timeout=1, poll_interval=0.01)


@patch("emailcli.receiver.imaplib.IMAP4_SSL")
def test_bad_status_raises(mock_imap_cls):
    conn = MagicMock()
    conn.status.return_value = ("NO", [b"error"])
    mock_imap_cls.return_value = conn

    with pytest.raises(ReceiveError, match="STATUS"):
        make_receiver().wait_for_message(timeout=1, poll_interval=0.01)


@patch("emailcli.receiver.imaplib.IMAP4")
def test_starttls_connection(mock_imap_cls):
    raw = make_raw_message()
    conn = make_conn([b"100"], raw=raw)
    mock_imap_cls.return_value = conn

    receiver = ImapReceiver(
        host="imap.example.com",
        port=143,
        username="me@example.com",
        password="secret",
        encryption="starttls",
    )
    msg = receiver.wait_for_message(timeout=5, poll_interval=0.01)

    assert msg is not None
    conn.starttls.assert_called_once()


def parse(raw):
    import email
    import email.policy

    return email.message_from_bytes(raw, policy=email.policy.default)


def test_extract_body_plain():
    msg = parse(make_raw_message(body="Plain text"))
    body, kind = extract_body(msg)
    assert body.strip() == "Plain text"
    assert kind == "text"


def test_extract_body_prefers_plain_over_html():
    msg = parse(make_raw_message(body="Plain", html="<p>HTML</p>"))
    body, kind = extract_body(msg)
    assert body.strip() == "Plain"
    assert kind == "text"


def test_extract_body_html_only():
    msg = EmailMessage()
    msg["Subject"] = "html"
    msg.set_content("<p>HTML only</p>", subtype="html")
    body, kind = extract_body(parse(bytes(msg)))
    assert "HTML only" in body
    assert kind == "html"


def test_save_attachments(tmp_path):
    raw = make_raw_message(attachments=[("report.pdf", b"%PDF-1.4")])
    saved = save_attachments(parse(raw), tmp_path / "downloads")

    assert len(saved) == 1
    assert saved[0].name == "report.pdf"
    assert saved[0].read_bytes() == b"%PDF-1.4"


def test_save_attachments_sanitizes_path(tmp_path):
    raw = make_raw_message(attachments=[("../../evil.sh", b"#!/bin/sh")])
    dest = tmp_path / "downloads"
    saved = save_attachments(parse(raw), dest)

    assert saved[0].parent == dest
    assert saved[0].name == "evil.sh"
    assert not (tmp_path / "evil.sh").exists()


def test_save_attachments_deduplicates(tmp_path):
    raw = make_raw_message(
        attachments=[("a.txt", b"one"), ("a.txt", b"two")]
    )
    saved = save_attachments(parse(raw), tmp_path)

    assert [p.name for p in saved] == ["a.txt", "a-1.txt"]
    assert (tmp_path / "a-1.txt").read_bytes() == b"two"


def test_save_attachments_none(tmp_path):
    raw = make_raw_message(body="no attachments")
    assert save_attachments(parse(raw), tmp_path) == []
