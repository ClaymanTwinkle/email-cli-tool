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
def test_status_without_uidnext_falls_back_to_max_uid(mock_imap_cls):
    # 163.com answers STATUS with OK but omits UIDNEXT; the watermark must
    # then come from the highest existing UID (99 -> watch from 100).
    raw = make_raw_message()
    conn = make_conn([b"1 2 99", b"99 100"], raw=raw)
    conn.status.return_value = ("OK", [b'"INBOX" ()'])
    mock_imap_cls.return_value = conn

    msg = make_receiver().wait_for_message(timeout=5, poll_interval=0.01)

    assert msg is not None
    conn.uid.assert_any_call("search", "UID", "1:*")
    conn.uid.assert_any_call("search", "UID", "100:*")
    conn.uid.assert_any_call("fetch", "100", "(RFC822)")


@patch("emailcli.receiver.imaplib.IMAP4_SSL")
def test_status_failure_falls_back(mock_imap_cls):
    raw = make_raw_message()
    conn = make_conn([b"99", b"100"], raw=raw)
    conn.status.return_value = ("NO", [b"STATUS unsupported"])
    mock_imap_cls.return_value = conn

    msg = make_receiver().wait_for_message(timeout=5, poll_interval=0.01)

    assert msg is not None
    conn.uid.assert_any_call("fetch", "100", "(RFC822)")


@patch("emailcli.receiver.imaplib.IMAP4_SSL")
def test_fallback_on_empty_mailbox_watches_from_uid_1(mock_imap_cls):
    raw = make_raw_message()
    conn = make_conn([b"", b"1"], raw=raw)
    conn.status.return_value = ("OK", [b'"INBOX" ()'])
    mock_imap_cls.return_value = conn

    msg = make_receiver().wait_for_message(timeout=5, poll_interval=0.01)

    assert msg is not None
    conn.uid.assert_any_call("fetch", "1", "(RFC822)")


@patch("emailcli.receiver.imaplib.IMAP4_SSL")
def test_sends_imap_id_when_supported(mock_imap_cls):
    # NetEase (163.com) rejects SELECT with "Unsafe Login" unless the client
    # introduces itself via the ID extension right after login.
    raw = make_raw_message()
    conn = make_conn([b"100"], raw=raw)
    conn.capabilities = ("IMAP4REV1", "ID")
    mock_imap_cls.return_value = conn

    msg = make_receiver().wait_for_message(timeout=5, poll_interval=0.01)

    assert msg is not None
    conn.xatom.assert_called_once()
    assert conn.xatom.call_args[0][0] == "ID"


@patch("emailcli.receiver.imaplib.IMAP4_SSL")
def test_no_imap_id_when_unsupported(mock_imap_cls):
    raw = make_raw_message()
    conn = make_conn([b"100"], raw=raw)
    conn.capabilities = ("IMAP4REV1",)
    mock_imap_cls.return_value = conn

    msg = make_receiver().wait_for_message(timeout=5, poll_interval=0.01)

    assert msg is not None
    conn.xatom.assert_not_called()


@patch("emailcli.receiver.imaplib.IMAP4_SSL")
def test_bad_select_raises(mock_imap_cls):
    conn = MagicMock()
    conn.status.return_value = ("OK", [b"INBOX (UIDNEXT 100)"])
    conn.select.return_value = ("NO", [b"no such mailbox"])
    mock_imap_cls.return_value = conn

    with pytest.raises(ReceiveError, match="select"):
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


@patch("emailcli.receiver.imaplib.IMAP4_SSL")
def test_list_messages_newest_first(mock_imap_cls):
    raw = make_raw_message()
    conn = make_conn([b"5 7 9"], raw=raw)
    mock_imap_cls.return_value = conn

    rows = make_receiver().list_messages(limit=2)

    assert [uid for uid, _ in rows] == [9, 7]
    assert rows[0][1]["Subject"] == "Test mail"
    conn.select.assert_called_once_with("INBOX", readonly=True)
    conn.uid.assert_any_call(
        "fetch", "9", "(BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE)])"
    )


@patch("emailcli.receiver.imaplib.IMAP4_SSL")
def test_list_messages_empty_mailbox(mock_imap_cls):
    conn = make_conn([b""])
    mock_imap_cls.return_value = conn

    assert make_receiver().list_messages() == []


@patch("emailcli.receiver.imaplib.IMAP4_SSL")
def test_get_message_latest(mock_imap_cls):
    raw = make_raw_message()
    conn = make_conn([b"5 9 7"], raw=raw)
    mock_imap_cls.return_value = conn

    uid, msg = make_receiver().get_message()

    assert uid == 9
    assert msg["Subject"] == "Test mail"
    conn.select.assert_called_once_with("INBOX", readonly=True)
    conn.uid.assert_any_call("fetch", "9", "(RFC822)")


@patch("emailcli.receiver.imaplib.IMAP4_SSL")
def test_get_message_by_missing_uid_raises(mock_imap_cls):
    conn = make_conn([b"5 7"])
    mock_imap_cls.return_value = conn

    with pytest.raises(ReceiveError, match="UID 6"):
        make_receiver().get_message(uid=6)


@patch("emailcli.receiver.imaplib.IMAP4_SSL")
def test_get_message_empty_mailbox_returns_none(mock_imap_cls):
    conn = make_conn([b""])
    mock_imap_cls.return_value = conn

    assert make_receiver().get_message() is None


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
