import mimetypes
from email.message import EmailMessage
from pathlib import Path

from emailcli.exceptions import MessageError


def build_message(
    from_addr: str,
    to_addrs: list[str],
    subject: str,
    body: str | None = None,
    html: str | None = None,
    html_file: Path | None = None,
    attachments: list[Path] | None = None,
) -> EmailMessage:
    # Resolve html_file to html string
    if html_file is not None:
        if not html_file.exists():
            raise MessageError(f"HTML file not found: {html_file}")
        html = html_file.read_text(encoding="utf-8")

    if not body and not html:
        raise MessageError("Must provide at least one of: --body, --html, --html-file")

    # Validate attachments exist before building
    if attachments:
        for path in attachments:
            if not path.exists():
                raise MessageError(f"Attachment not found: {path}")

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = subject

    # Build content
    if body and html:
        msg.set_content(body)
        msg.add_alternative(html, subtype="html")
    elif body:
        msg.set_content(body)
    else:
        msg.set_content(html, subtype="html")

    # Add attachments
    if attachments:
        for path in attachments:
            mime_type, _ = mimetypes.guess_type(str(path))
            if mime_type is None:
                maintype, subtype = "application", "octet-stream"
            else:
                maintype, subtype = mime_type.split("/", 1)

            with open(path, "rb") as f:
                data = f.read()

            msg.add_attachment(
                data,
                maintype=maintype,
                subtype=subtype,
                filename=path.name,
            )

    return msg
