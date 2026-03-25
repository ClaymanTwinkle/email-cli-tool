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

## Installation

```bash
# From PyPI
pip install email-cli-tool

# Or with uv
uv tool install email-cli-tool
```

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

### `emailcli init`

Interactively create the configuration file at `~/.emailcli/config.yaml`.

### `emailcli config show`

Display current configuration (password is masked).

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
