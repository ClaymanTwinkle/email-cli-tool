---
name: wait-email
description: "Wait for the next incoming email via emailcli. Prints sender/subject/body and downloads attachments. Use when the user wants to wait for, receive, or read an incoming email."
---

# Wait for Email

Wait for the next incoming email from Claude Code using the `emailcli watch` command.

## Usage

Invoke with `/wait-email` followed by natural language describing what to wait for:

```
/wait-email 等下一封新邮件
/wait-email 等 5 分钟，附件存到 ./downloads
/wait-email 等一封验证码邮件，把验证码读出来
```

## Workflow

### 1. Parse user intent

Extract from the user's message:
- **Timeout** (`--timeout`): seconds to wait. Default to 300 if the user gives no limit; use 0 (wait forever) only if the user explicitly asks to wait indefinitely.
- **Attachment directory** (`--save-attachments`): where to save attachments, if the user mentions them.
- **Mailbox** (`--mailbox`): defaults to INBOX.

### 2. Run the command

```bash
emailcli watch --timeout 300 --save-attachments ./downloads
```

- The command blocks until an email arrives, so set the Bash tool timeout comfortably larger than `--timeout` (or run it in the background for long waits).
- Headers and body go to stdout; progress messages and saved-attachment paths go to stderr.
- Only emails arriving **after** the command starts are matched; existing unread mail is ignored.

### 3. Report result

By exit code:
- **0** — email received: report From / Subject / Date, the body (or the specific detail the user asked for, e.g. a verification code), and any saved attachment paths.
- **2** — timed out with no new email: tell the user.
- **1** — error: show the message. If it says IMAP settings are missing, tell the user to re-run `emailcli init` or add an `imap:` section to `~/.emailcli/config.yaml`.

## Command Reference

```bash
emailcli watch \
  [--timeout SECONDS]        # 0 = wait forever
  [--poll-interval SECONDS]  # default: 10
  [--save-attachments DIR] \
  [--mailbox NAME]           # default: INBOX
```

## Important

- Requires email-cli-tool **0.3.0+** with IMAP configured (`emailcli init`).
- The received email is marked as read on the server.
- Do NOT ask for confirmation — start waiting once inputs are clear, and tell the user you are waiting.
