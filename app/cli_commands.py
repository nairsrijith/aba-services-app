"""Flask CLI commands for invoice reminders."""

import click
from flask.cli import with_appcontext
from app.utils.invoice_reminder import process_invoice_reminders


@click.command()
@with_appcontext
def send_invoice_reminders():
    """Process and send invoice reminder emails."""
    click.echo('Processing invoice reminders...')
    process_invoice_reminders()
    click.echo('Done!')
