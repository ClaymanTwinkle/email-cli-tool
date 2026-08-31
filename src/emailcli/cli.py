import sys
from pathlib import Path

import click

from emailcli.config import load_config
from emailcli.exceptions import EmailCliError
from emailcli.message import build_message
from emailcli.receiver import ImapReceiver, extract_body, save_attachments
from emailcli.sender import SmtpSender
from emailcli import skill_install


@click.group()
@click.version_option(package_name="email-cli-tool")
def cli():
    """CLI tool for sending emails with attachments."""


@cli.command()
@click.option("--to", "to_addrs", required=True, multiple=True, help="Recipient email address (repeatable).")
@click.option("--subject", required=True, help="Email subject.")
@click.option("--body", default=None, help="Plain text body. Use '-' to read from stdin.")
@click.option("--html", "html_content", default=None, help="HTML body string.")
@click.option("--html-file", "html_file_path", default=None, type=click.Path(exists=True), help="Read HTML body from file.")
@click.option("--attach", "attachments", multiple=True, type=click.Path(exists=True), help="Attachment file path (repeatable).")
@click.option("--from", "from_addr", default=None, help="Sender address (overrides config).")
@click.option("--config-dir", default=None, type=click.Path(), hidden=True, help="Config directory (for testing).")
def send(to_addrs, subject, body, html_content, html_file_path, attachments, from_addr, config_dir):
    """Send an email."""
    try:
        # Validate --html and --html-file mutual exclusivity
        if html_content and html_file_path:
            raise click.UsageError("--html and --html-file are mutually exclusive.")

        # Read stdin if body is "-"
        if body == "-":
            body = click.get_text_stream("stdin").read()

        # Load config
        cfg_dir = Path(config_dir) if config_dir else None
        config = load_config(cfg_dir)

        # Determine from address
        sender_addr = from_addr or config.from_addr
        if not sender_addr:
            raise EmailCliError("No sender address. Set 'from' in config or use --from.")

        # Build message
        msg = build_message(
            from_addr=sender_addr,
            to_addrs=list(to_addrs),
            subject=subject,
            body=body,
            html=html_content,
            html_file=Path(html_file_path) if html_file_path else None,
            attachments=[Path(a) for a in attachments] if attachments else None,
        )

        # Send
        sender = SmtpSender(
            host=config.smtp_host,
            port=config.smtp_port,
            username=config.smtp_username,
            password=config.smtp_password,
            encryption=config.smtp_encryption,
        )
        sender.send(msg)

        click.echo("Email sent successfully.")
    except click.UsageError:
        raise
    except EmailCliError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@cli.command()
@click.option("--timeout", default=0.0, type=float, help="Max seconds to wait for a new email (0 = wait forever).")
@click.option("--poll-interval", default=10.0, type=float, show_default=True, help="Seconds between mailbox checks.")
@click.option("--save-attachments", "attachments_dir", default=None, type=click.Path(file_okay=False), help="Directory to save attachments into.")
@click.option("--mailbox", default="INBOX", show_default=True, help="Mailbox to watch.")
@click.option("--config-dir", default=None, type=click.Path(), hidden=True, help="Config directory (for testing).")
def watch(timeout, poll_interval, attachments_dir, mailbox, config_dir):
    """Wait for the next incoming email, print it, then exit.

    Only emails arriving after the command starts are matched. Exits with
    code 0 when an email was received, 2 on timeout.
    """
    try:
        cfg_dir = Path(config_dir) if config_dir else None
        config = load_config(cfg_dir)

        if config.imap is None:
            raise EmailCliError(
                "No IMAP settings in config. Re-run 'emailcli init' "
                "or add an 'imap' section to config.yaml."
            )

        receiver = ImapReceiver(
            host=config.imap.host,
            port=config.imap.port,
            username=config.imap.username,
            password=config.imap.password,
            encryption=config.imap.encryption,
        )

        click.echo(f"Waiting for new email in {mailbox}... (Ctrl-C to stop)", err=True)
        msg = receiver.wait_for_message(
            mailbox=mailbox, timeout=timeout, poll_interval=poll_interval
        )
        if msg is None:
            click.echo(f"Timed out after {timeout:g}s with no new email.", err=True)
            raise SystemExit(2)

        click.echo(f"From:    {msg.get('From', '')}")
        click.echo(f"To:      {msg.get('To', '')}")
        click.echo(f"Subject: {msg.get('Subject', '')}")
        click.echo(f"Date:    {msg.get('Date', '')}")
        click.echo("")

        body, kind = extract_body(msg)
        if body:
            if kind == "html":
                click.echo("(HTML body)", err=True)
            click.echo(body)
        else:
            click.echo("(no text body)", err=True)

        if attachments_dir:
            saved = save_attachments(msg, Path(attachments_dir))
            if saved:
                for path in saved:
                    click.echo(f"Saved attachment: {path}", err=True)
            else:
                click.echo("No attachments.", err=True)
    except EmailCliError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)



@cli.command()
@click.option("--config-dir", default=None, type=click.Path(), hidden=True, help="Config directory (for testing).")
def init(config_dir):
    """Initialize emailcli configuration."""
    import os

    import yaml

    cfg_dir = Path(config_dir) if config_dir else Path.home() / ".emailcli"
    config_file = cfg_dir / "config.yaml"

    if config_file.exists():
        if not click.confirm(f"Config already exists at {config_file}. Overwrite?"):
            click.echo("Aborted.")
            return

    click.echo("Setting up emailcli configuration...\n")

    from_addr = click.prompt("From address (sender email)")
    smtp_host = click.prompt("SMTP host")
    smtp_port = click.prompt("SMTP port", type=int, default=465)
    smtp_username = click.prompt("SMTP username")
    smtp_password = click.prompt("SMTP password", hide_input=True)
    smtp_encryption = click.prompt(
        "Encryption (starttls/ssl/none)", default="ssl"
    )

    imap_section = None
    if click.confirm("\nConfigure IMAP (needed for 'emailcli watch')?", default=False):
        imap_host = click.prompt("IMAP host")
        imap_port = click.prompt("IMAP port", type=int, default=993)
        imap_username = click.prompt("IMAP username", default=smtp_username)
        imap_password = click.prompt(
            "IMAP password (empty = same as SMTP)",
            hide_input=True, default="", show_default=False,
        )
        imap_encryption = click.prompt("IMAP encryption (ssl/starttls/none)", default="ssl")
        imap_section = {
            "host": imap_host,
            "port": imap_port,
            "username": imap_username,
            "encryption": imap_encryption,
        }
        if imap_password:
            imap_section["password"] = imap_password

    config_data = {
        "from": from_addr,
        "smtp": {
            "host": smtp_host,
            "port": smtp_port,
            "username": smtp_username,
            "password": smtp_password,
            "encryption": smtp_encryption,
        },
    }
    if imap_section:
        config_data["imap"] = imap_section

    cfg_dir.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w") as f:
        yaml.dump(config_data, f, default_flow_style=False)
    os.chmod(config_file, 0o600)

    click.echo(f"\nConfig saved to {config_file}")


@cli.group(name="config")
def config_group():
    """Manage emailcli configuration."""


@config_group.command()
@click.option("--config-dir", default=None, type=click.Path(), hidden=True, help="Config directory (for testing).")
def show(config_dir):
    """Show current configuration."""
    try:
        cfg_dir = Path(config_dir) if config_dir else None
        cfg = load_config(cfg_dir)

        click.echo(f"From:       {cfg.from_addr}")
        click.echo(f"SMTP Host:  {cfg.smtp_host}")
        click.echo(f"SMTP Port:  {cfg.smtp_port}")
        click.echo(f"Username:   {cfg.smtp_username}")
        click.echo(f"Password:   ***")
        click.echo(f"Encryption: {cfg.smtp_encryption}")
        if cfg.imap:
            click.echo("")
            click.echo(f"IMAP Host:  {cfg.imap.host}")
            click.echo(f"IMAP Port:  {cfg.imap.port}")
            click.echo(f"IMAP User:  {cfg.imap.username}")
            click.echo(f"IMAP Encryption: {cfg.imap.encryption}")
    except EmailCliError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@cli.group(name="skill")
def skill_group():
    """Manage the emailcli agent skill."""


@skill_group.command(name="install")
@click.option(
    "--target",
    type=click.Choice(["claude", "codex", "all"]),
    default="all",
    show_default=True,
    help="Which agent to install the skill for.",
)
@click.option("--home", default=None, type=click.Path(), hidden=True, help="Home directory (for testing).")
def install(target, home):
    """Install the emailcli agent skills into Claude Code and/or Codex."""
    home_dir = Path(home) if home else Path.home()
    targets = ["claude", "codex"] if target == "all" else [target]

    results = skill_install.install_skill(home_dir, targets)

    for r in results:
        label = skill_install.TARGET_LABELS[r.target]
        if r.status == "failed":
            click.echo(f"✗ {label}\t{r.path}\t(failed: {r.error})", err=True)
        else:
            click.echo(f"✓ {label}\t{r.path}\t({r.status})")

    if any(r.status == "failed" for r in results):
        raise SystemExit(1)
