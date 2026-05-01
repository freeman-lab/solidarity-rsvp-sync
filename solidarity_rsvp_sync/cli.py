import os
import sys
import click
from dotenv import load_dotenv

from .sync import run_sync

load_dotenv(override=True)


@click.command()
@click.option('--sheet-id', default=lambda: os.getenv('SHEET_ID'))
@click.option('--sheet-name', default=lambda: os.getenv('SHEET_NAME'))
@click.option('--credentials', default=lambda: os.getenv('GOOGLE_CREDENTIALS'))
def cli(sheet_id, sheet_name, credentials):
    """Sync Solidarity Tech RSVP counts into a Google sheet."""
    api_token = os.getenv('ST_API_TOKEN')

    missing = []
    if not api_token:
        missing.append('ST_API_TOKEN')
    if not credentials:
        missing.append('GOOGLE_CREDENTIALS')
    if not sheet_id:
        missing.append('SHEET_ID')
    if not sheet_name:
        missing.append('SHEET_NAME')
    if missing:
        click.echo(f'missing config: {", ".join(missing)}', err=True)
        sys.exit(2)

    failed = run_sync(api_token, credentials, sheet_id, sheet_name)
    sys.exit(1 if failed else 0)
