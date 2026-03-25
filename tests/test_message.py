from email.message import EmailMessage
from pathlib import Path

import pytest

from emailcli.message import build_message


def test_plain_text_message():
    msg = build_message(
        from_addr="sender@example.com",
        to_addrs=["recipient@example.com"],
        subject="Hello",
        body="Hello World",
    )
    assert msg["From"] == "sender@example.com"
    assert msg["To"] == "recipient@example.com"
    assert msg["Subject"] == "Hello"
    assert msg.get_content_type() == "text/plain"
    assert msg.get_content().strip() == "Hello World"


def test_html_message():
    msg = build_message(
        from_addr="sender@example.com",
        to_addrs=["recipient@example.com"],
        subject="Report",
        html="<h1>Report</h1>",
    )
    assert msg.get_content_type() == "text/html"
    assert "<h1>Report</h1>" in msg.get_content()


def test_text_and_html_message():
    msg = build_message(
        from_addr="sender@example.com",
        to_addrs=["recipient@example.com"],
        subject="Both",
        body="Plain text",
        html="<p>HTML</p>",
    )
    assert msg.get_content_type() == "multipart/alternative"
    parts = list(msg.iter_parts())
    assert len(parts) == 2
    assert parts[0].get_content_type() == "text/plain"
    assert parts[1].get_content_type() == "text/html"


def test_multiple_recipients():
    msg = build_message(
        from_addr="sender@example.com",
        to_addrs=["a@example.com", "b@example.com"],
        subject="Multi",
        body="Hello",
    )
    assert msg["To"] == "a@example.com, b@example.com"


def test_message_with_attachment(tmp_path):
    attach_file = tmp_path / "report.txt"
    attach_file.write_text("file content")

    msg = build_message(
        from_addr="sender@example.com",
        to_addrs=["recipient@example.com"],
        subject="With Attachment",
        body="See attached",
        attachments=[attach_file],
    )
    assert msg.get_content_type() == "multipart/mixed"
    parts = list(msg.iter_parts())
    assert parts[0].get_content_type() == "text/plain"
    assert parts[1].get_content_type() == "text/plain"  # .txt attachment
    assert parts[1].get_filename() == "report.txt"


def test_message_with_image_attachment(tmp_path):
    img_file = tmp_path / "photo.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    msg = build_message(
        from_addr="sender@example.com",
        to_addrs=["recipient@example.com"],
        subject="Photo",
        body="See photo",
        attachments=[img_file],
    )
    parts = list(msg.iter_parts())
    assert parts[1].get_content_type() == "image/png"
    assert parts[1].get_filename() == "photo.png"


def test_html_and_attachment(tmp_path):
    attach_file = tmp_path / "data.csv"
    attach_file.write_text("a,b,c")

    msg = build_message(
        from_addr="sender@example.com",
        to_addrs=["recipient@example.com"],
        subject="Report",
        body="Fallback",
        html="<p>Report</p>",
        attachments=[attach_file],
    )
    # multipart/mixed at top, with multipart/alternative + attachment
    assert msg.get_content_type() == "multipart/mixed"
    parts = list(msg.iter_parts())
    assert parts[0].get_content_type() == "multipart/alternative"
    assert parts[1].get_filename() == "data.csv"


def test_html_file(tmp_path):
    html_file = tmp_path / "template.html"
    html_file.write_text("<h1>Template</h1>")

    msg = build_message(
        from_addr="sender@example.com",
        to_addrs=["recipient@example.com"],
        subject="Newsletter",
        html_file=html_file,
    )
    assert msg.get_content_type() == "text/html"
    assert "<h1>Template</h1>" in msg.get_content()


def test_no_body_or_html_raises():
    from emailcli.exceptions import MessageError

    with pytest.raises(MessageError, match="body.*html"):
        build_message(
            from_addr="sender@example.com",
            to_addrs=["recipient@example.com"],
            subject="Empty",
        )


def test_attachment_not_found():
    from emailcli.exceptions import MessageError

    with pytest.raises(MessageError, match="not found"):
        build_message(
            from_addr="sender@example.com",
            to_addrs=["recipient@example.com"],
            subject="Missing",
            body="text",
            attachments=[Path("/nonexistent/file.txt")],
        )
