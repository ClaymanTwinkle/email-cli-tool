---
name: send-email
description: "Send emails with attachments via emailcli. Supports plain text, HTML, multiple recipients, and file/image attachments."
---

# Send Email

Send emails directly from Claude Code using the `emailcli` CLI tool.

## Usage

Invoke with `/send-email` followed by natural language describing what to send:

```
/send-email 发送测试邮件给 test@example.com
/send-email 把 report.pdf 发给 alice@example.com，主题是"月度报告"
/send-email 给 a@example.com 和 b@example.com 发一封 HTML 邮件
```

## Workflow

### 1. Parse user intent

Extract from the user's message:
- **Recipients** (`--to`): one or more email addresses
- **Subject** (`--subject`): email subject line
- **Body** (`--body` or `--html`): email content
- **Attachments** (`--attach`): file paths if mentioned

### 2. Validate inputs

- If recipients are missing, ask the user.
- If subject is missing, ask the user.
- If body is missing, ask the user.
- If attachments are mentioned, verify the files exist using Glob or ls before sending.

### 3. Send (no confirmation needed)

Run the `emailcli send` command with the appropriate arguments.

```bash
emailcli send \
  --to recipient@example.com \
  --subject "测试邮件" \
  --body "Hello World" \
  --attach report.pdf \
  --attach photo.png
```

### 4. Report result

Tell the user whether the email was sent successfully or if there was an error.

## Command Reference

```bash
# Plain text
emailcli send --to <email> --subject <subject> --body <text>

# HTML
emailcli send --to <email> --subject <subject> --html <html>

# HTML from file
emailcli send --to <email> --subject <subject> --html-file <path>

# With attachments (repeatable)
emailcli send --to <email> --subject <subject> --body <text> --attach <file>

# Multiple recipients (repeatable)
emailcli send --to <email1> --to <email2> --subject <subject> --body <text>

# Override sender
emailcli send --to <email> --subject <subject> --body <text> --from <sender>

# Body from stdin
echo "content" | emailcli send --to <email> --subject <subject> --body -
```

## Important

- Do NOT ask for confirmation — send directly once inputs are ready.
- Verify attachment files exist before running the command.
- If the command fails, show the error message to the user.
- The tool must be configured first via `emailcli init`. If sending fails with a config error, tell the user to run `emailcli init`.
