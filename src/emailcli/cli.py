import sys
from pathlib import Path

import click

from emailcli.config import load_config
from emailcli.exceptions import EmailCliError
from emailcli.message import build_message
from emailcli.sender import SmtpSender


@click.group()
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
    except EmailCliError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
