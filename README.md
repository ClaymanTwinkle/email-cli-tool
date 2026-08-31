# email-cli-tool

> A simple CLI tool for sending emails with plain text, HTML, and file attachments.
>
> [中文文档](README_CN.md)

## Features

- Send plain text / HTML / mixed format emails
- Attach multiple files and images
- Multiple recipients support
- Direct SMTP connection (SSL / STARTTLS)
- Interactive configuration wizard
- Read body content from stdin
- Wait for the next incoming email (IMAP) and download its attachments

## Installation

```bash
# From PyPI (latest)
pip install email-cli-tool

# Install a specific version
pip install email-cli-tool==0.2.0

# Upgrade an existing install
pip install --upgrade email-cli-tool

# Or with uv
uv tool install email-cli-tool          # latest
uv tool install email-cli-tool==0.2.0   # specific version
```

> The `emailcli skill install` command requires version **0.2.0** or newer.

## Quick Start

### 1. Initialize Configuration

```bash
emailcli init
```

Follow the prompts to enter your SMTP settings. Example for Gmail:

| Field | Value |
|-------|-------|
| From address | `yourname@gmail.com` |
| SMTP host | `smtp.gmail.com` |
| SMTP port | `465` |
| SMTP username | `yourname@gmail.com` |
| SMTP password | App password |
| Encryption | `ssl` |

### 2. Send Emails

```bash
# Plain text
emailcli send --to user@example.com --subject "Hello" --body "Hello World"

# HTML format
emailcli send --to user@example.com --subject "Notice" \
  --html "<h1>Title</h1><p>Body content</p>"

# With attachments
emailcli send --to user@example.com --subject "Report" \
  --body "Please see attachments" \
  --attach report.pdf \
  --attach photo.png

# Multiple recipients
emailcli send \
  --to a@example.com \
  --to b@example.com \
  --subject "Broadcast" --body "Hello everyone"

# HTML body from file
emailcli send --to user@example.com --subject "Newsletter" \
  --html-file template.html

# Read body from stdin
echo "Content" | emailcli send \
  --to user@example.com --subject "Piped" --body -
```

### 3. Wait for Incoming Email

```bash
# Block until the next email arrives, print it, then exit
emailcli watch

# Wait up to 5 minutes and save attachments
emailcli watch --timeout 300 --save-attachments ./downloads
```

Requires IMAP settings — `emailcli init` asks for them, or add an `imap` section to the config (see below).

### 4. Read Existing Emails

```bash
# List the 10 newest emails (UID, date, sender, subject)
emailcli list

# Read the newest email
emailcli read

# Read a specific email by UID and save its attachments
emailcli read 1774452489 --save-attachments ./downloads
```

Also requires IMAP settings. Both commands open the mailbox read-only, so nothing is marked as read.

## Command Reference

### `emailcli send`

| Option | Required | Repeatable | Description |
|--------|:--------:|:----------:|-------------|
| `--to` | ✅ | ✅ | Recipient email address |
| `--subject` | ✅ | | Email subject |
| `--body` | | | Plain text body, `-` reads from stdin |
| `--html` | | | HTML body string (mutually exclusive with `--html-file`) |
| `--html-file` | | | Read HTML body from file (mutually exclusive with `--html`) |
| `--attach` | | ✅ | Attachment file path |
| `--from` | | | Override sender address from config |

> At least one of `--body`, `--html`, or `--html-file` is required.

### `emailcli watch`

Wait for the next incoming email (via IMAP polling), print headers and body to stdout, then exit. Only emails arriving **after** the command starts are matched; the received email is marked as read.

| Option | Default | Description |
|--------|---------|-------------|
| `--timeout` | `0` (wait forever) | Max seconds to wait; exits with code `2` on timeout |
| `--poll-interval` | `10` | Seconds between mailbox checks |
| `--save-attachments` | | Directory to save attachments into |
| `--mailbox` | `INBOX` | Mailbox to watch |

### `emailcli list`

List the newest emails, newest first — one per line: UID, date, sender, subject (tab-separated). The mailbox is opened read-only, so nothing is marked as read.

| Option | Default | Description |
|--------|---------|-------------|
| `--limit` | `10` | Number of newest messages to show |
| `--mailbox` | `INBOX` | Mailbox to list |

### `emailcli read [UID]`

Read one email by UID (as shown by `emailcli list`), or the newest one when no UID is given. Prints headers and body like `watch`. The mailbox is opened read-only, so the message is not marked as read. Exits with code `2` when the mailbox is empty.

| Option | Default | Description |
|--------|---------|-------------|
| `--save-attachments` | | Directory to save attachments into |
| `--mailbox` | `INBOX` | Mailbox to read from |

### `emailcli init`

Interactively create the configuration file at `~/.emailcli/config.yaml`.

### `emailcli config show`

Display current configuration (password is masked).

### `emailcli skill install`

Install the `send-email`, `wait-email`, and `read-email` agent skills so Claude Code or Codex can send, receive, and read mail for you.

```bash
# Install for both Claude Code and Codex (default)
emailcli skill install

# Only one agent
emailcli skill install --target claude
emailcli skill install --target codex
```

Writes each skill's `SKILL.md` under `~/.claude/skills/` and/or `~/.codex/skills/`.

## Configuration

Path: `~/.emailcli/config.yaml`

```yaml
from: yourname@gmail.com
smtp:
  host: smtp.gmail.com
  port: 465
  username: yourname@gmail.com
  password: your-app-password
  encryption: ssl  # ssl | starttls | none

# Optional, only needed for `emailcli watch`
imap:
  host: imap.gmail.com
  port: 993        # default: 993
  encryption: ssl  # default: ssl
  # username/password default to the smtp values
```

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest -v

# Run locally
uv run emailcli --help
```

## License

MIT
