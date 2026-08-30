import email
import email.policy
import imaplib
import re
import time
from email.message import EmailMessage
from pathlib import Path

from emailcli.exceptions import ReceiveError

_UIDNEXT_RE = re.compile(rb"UIDNEXT (\d+)")


class ImapReceiver:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        encryption: str,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.encryption = encryption

    def _connect(self) -> imaplib.IMAP4:
        try:
            if self.encryption == "ssl":
                conn = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                conn = imaplib.IMAP4(self.host, self.port)
                if self.encryption == "starttls":
                    conn.starttls()
            conn.login(self.username, self.password)
            return conn
        except Exception as e:
            raise ReceiveError(f"Failed to connect to IMAP server: {e}") from e

    def wait_for_message(
        self,
        mailbox: str = "INBOX",
        timeout: float = 0,
        poll_interval: float = 10.0,
    ) -> EmailMessage | None:
        """Block until a message arrives after this call starts.

        Polls the mailbox every poll_interval seconds and returns the first
        message whose UID is >= the UIDNEXT recorded at start, so existing
        unread mail is ignored. Returns None if timeout (seconds, 0 = no
        limit) expires first.
        """
        conn = self._connect()
        try:
            typ, data = conn.status(mailbox, "(UIDNEXT)")
            if typ != "OK":
                raise ReceiveError(f"IMAP STATUS failed: {data}")
            match = _UIDNEXT_RE.search(data[0])
            if not match:
                raise ReceiveError(f"Could not read UIDNEXT from: {data[0]!r}")
            uidnext = int(match.group(1))

            typ, data = conn.select(mailbox)
            if typ != "OK":
                raise ReceiveError(f"Cannot select mailbox {mailbox!r}: {data}")

            deadline = time.monotonic() + timeout if timeout > 0 else None
            while True:
                # NOOP prompts the server to report newly arrived messages.
                conn.noop()
                typ, data = conn.uid("search", "UID", f"{uidnext}:*")
                if typ != "OK":
                    raise ReceiveError(f"IMAP SEARCH failed: {data}")
                uids = [int(u) for u in data[0].split()] if data and data[0] else []
                # "N:*" also matches the last existing message when its UID
                # is below N, so keep only genuinely new UIDs.
                new = sorted(u for u in uids if u >= uidnext)
                if new:
                    return self._fetch(conn, new[0])
                if deadline is not None and time.monotonic() >= deadline:
                    return None
                sleep_for = poll_interval
                if deadline is not None:
                    sleep_for = min(sleep_for, max(0.0, deadline - time.monotonic()))
                time.sleep(sleep_for)
        except ReceiveError:
            raise
        except Exception as e:
            raise ReceiveError(f"Failed while waiting for email: {e}") from e
        finally:
            try:
                conn.logout()
            except Exception:
                pass

    def _fetch(self, conn: imaplib.IMAP4, uid: int) -> EmailMessage:
        typ, msg_data = conn.uid("fetch", str(uid), "(RFC822)")
        if typ != "OK":
            raise ReceiveError(f"IMAP FETCH failed: {msg_data}")
        raw = None
        for item in msg_data:
            if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], (bytes, bytearray)):
                raw = item[1]
                break
        if raw is None:
            raise ReceiveError(f"Unexpected FETCH response for UID {uid}")
        return email.message_from_bytes(raw, policy=email.policy.default)


def extract_body(msg: EmailMessage) -> tuple[str, str]:
    """Return (content, kind) where kind is "text", "html", or ""."""
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return "", ""
    kind = "html" if part.get_content_subtype() == "html" else "text"
    return part.get_content(), kind


def save_attachments(msg: EmailMessage, dest: Path) -> list[Path]:
    """Save all attachments into dest, returning the written paths.

    Filenames are stripped to their basename and deduplicated with -1, -2...
    suffixes so a crafted attachment name cannot escape dest or overwrite
    an earlier file.
    """
    dest.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for i, part in enumerate(msg.iter_attachments()):
        name = Path(part.get_filename() or f"attachment-{i + 1}").name
        if not name or name in (".", ".."):
            name = f"attachment-{i + 1}"
        target = dest / name
        stem, suffix = target.stem, target.suffix
        n = 1
        while target.exists():
            target = dest / f"{stem}-{n}{suffix}"
            n += 1
        payload = part.get_payload(decode=True)
        if payload is None:
            content = part.get_content()
            payload = content.encode() if isinstance(content, str) else bytes(content)
        target.write_bytes(payload)
        saved.append(target)
    return saved
