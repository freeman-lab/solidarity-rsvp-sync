# solidarity-rsvp-sync

> Utility for syncing Solidarity Tech RSVPs with a Google sheet

## About

Campaigns using Solidarity Tech often manage a separate spreadsheet for tracking their events (with additional metadata like meetup location, turf info, field leads, etc.). It's useful to have RSVP counts regularly synced in that spreadsheet.

With this tool, if your spreadsheet has columns for "Event ID" (and optionally "Session ID") and "RSVP Count", this tool will use the Solidarity Tech API populate the "RSVP Count" column with counts for each combination of event and session ID. 

It's a simple CLI that, once configured, will run whenver you want. Most teams will want to run it every day (or hour).

## Prerequisites

You need a Solidarity Tech account and an API token (we recommend creating one just for this purposes).

You also need a Google service worker account to read/write to your Google sheet. This is mildly annoying to setup, but is a one time cost. See below for a detailed guide. It'll give you an email address that you share your sheet with, and it'll give you a credentials JSON file. 

With those three pieces, the script will run.

## Setup

Specify the following environmental variables:

```
# Solidarity Tech API token
ST_API_TOKEN=

# Google service account JSON key file
GOOGLE_CREDENTIALS=./credentials.json

# Target Google sheet and tab name
SHEET_ID=
SHEET_NAME=Sheet1
```

Then install the dependencies and run the sync using:

```
uv sync
uv run solidarity-rsvp-sync
```

You need [uv](https://docs.astral.sh/uv/) and Python 3.11+.

CLI flags can override the env vars (handy for syncing several sheets from one config):

```
uv run solidarity-rsvp-sync --sheet-id=... --sheet-name=...
```

The script exits non-zero if any row failed to fetch or if the sheet write failed, so a cron job can alert on that.

## Google service worker

This part is the most complicated, but here's a step by step:

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a new project (or use an existing one).
2. From APIs & Services → Library, enable both the **Google Sheets API** and the **Google Drive API**.
3. From IAM & Admin → Service Accounts, click "Create service account". Pick any name; no roles needed.
4. On the new service account, go to Keys → Add Key → Create new key → JSON. A credentials file will download — save it somewhere safe and point `GOOGLE_CREDENTIALS` at it.
5. Copy the service account's email address — it looks like `something@project.iam.gserviceaccount.com`.
6. Open your sheet in Google Sheets and **share it with that email** as an Editor.

The same credentials JSON works for every sheet you share with the service account, so this is a one-time cost.

### Protected ranges

If your sheet uses **protected ranges** on the RSVP Count column, Editor access on the sheet alone is not enough. You need to either give the service account edit access to the protected range, or remove the protection on the RSVP Count column. If you skip this you'll see `You are trying to edit a protected cell or object` on the write step.

## How it works

For each row in the sheet:

- If both `Event ID` and `Session ID` are filled, it counts RSVPs for that specific session.
- If only `Event ID` is filled, it counts RSVPs across all sessions of the event.
- If `Event ID` is missing, the row is skipped.

Counts are written back to the `RSVP Count` column in a single batched API call. Other columns are left untouched.

API calls are throttled to Solidarity's documented limit (60 per 30s, with bursting). On `429 Too Many Requests` the client honors the `Retry-After` header. On `5xx` responses and connection errors it retries with exponential backoff (three tries).

## Regular runs

Run hourly via cron (`crontab -e`):

```
0 * * * * cd /path/to/solidarity-rsvp-sync && /path/to/uv run solidarity-rsvp-sync >> /tmp/solidarity-rsvp-sync.log 2>&1
```

Or use launchd on macOS, a systemd timer, or a scheduled GitHub Actions workflow. Lots of options.
