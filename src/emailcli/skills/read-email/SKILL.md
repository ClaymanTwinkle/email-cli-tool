---
name: read-email
description: "List and read existing emails in the inbox via emailcli. Prints sender/subject/body and downloads attachments. Use when the user wants to check the inbox, list recent emails, or read an email that already arrived."
---

# Read Email

List and read existing emails from Claude Code using the `emailcli list` and `emailcli read` commands.

## Usage

Invoke with `/read-email` followed by natural language describing what to read:

```
/read-email 看下最近的邮件
/read-email 读最新一封
/read-email 找到主题带"发票"的那封，把附件存到 ./downloads
```

## Workflow

### 1. List recent messages (skip if the user just wants the latest one)

```bash
emailcli list --limit 10
```

One message per line, newest first: UID, date, sender, subject (tab-separated). Use `--limit` to see more, `--mailbox` for folders other than INBOX.

### 2. Read the message

```bash
# Read the newest message
emailcli read

# Read a specific message by UID from `emailcli list`
emailcli read 1774452489 --save-attachments ./downloads
```

If the user described the email (by sender, subject, or time), find its UID in the `list` output first, then `read` that UID.

### 3. Report result

By exit code:
- **0** — report From / Subject / Date, the body (or the specific detail the user asked for, e.g. a verification code), and any saved attachment paths.
- **2** — mailbox is empty: tell the user.
- **1** — error: show the message. If it says IMAP settings are missing, tell the user to re-run `emailcli init` or add an `imap:` section to `~/.emailcli/config.yaml`.

## Command Reference

```bash
emailcli list \
  [--limit N]        # default: 10
  [--mailbox NAME]   # default: INBOX

emailcli read [UID] \
  [--save-attachments DIR] \
  [--mailbox NAME]   # default: INBOX
```

## Important

- Requires email-cli-tool **0.4.0+** with IMAP configured (`emailcli init`).
- Both commands open the mailbox read-only — nothing is marked as read.
- To wait for a NEW email that has not arrived yet, use the wait-email skill (`emailcli watch`) instead.
- Do NOT ask for confirmation — run once inputs are clear.
