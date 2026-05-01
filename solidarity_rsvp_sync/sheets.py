import json
import gspread
from gspread.utils import rowcol_to_a1
from google.oauth2.service_account import Credentials


SCOPES = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive',
]

EVENT_COL = 'Event ID'
SESSION_COL = 'Session ID'
COUNT_COL = 'RSVP Count'


def read_service_account_email(credentials_path):
    with open(credentials_path) as f:
        return json.load(f).get('client_email', '<unknown>')


def open_worksheet(credentials_path, sheet_id, sheet_name):
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(sheet_id)
    return spreadsheet.worksheet(sheet_name)


def read_rows(worksheet):
    """Return (header_to_col, data_rows) where data_rows is a list of dicts:
    {'row': 1-indexed sheet row, 'event_id': str|None, 'session_id': str|None}.
    """
    grid = worksheet.get_all_values()
    if not grid:
        raise ValueError('sheet is empty')

    headers = grid[0]
    header_to_col = {h.strip(): i + 1 for i, h in enumerate(headers)}

    for required in (EVENT_COL, COUNT_COL):
        if required not in header_to_col:
            raise ValueError(f'sheet is missing required column: {required!r}')

    event_idx = header_to_col[EVENT_COL] - 1
    session_idx = header_to_col.get(SESSION_COL, 0) - 1

    rows = []
    for r, row in enumerate(grid[1:], start=2):
        event_id = row[event_idx].strip() if event_idx < len(row) else ''
        session_id = (
            row[session_idx].strip()
            if SESSION_COL in header_to_col and session_idx < len(row)
            else ''
        )
        rows.append(
            {
                'row': r,
                'event_id': event_id or None,
                'session_id': session_id or None,
            }
        )

    return header_to_col, rows


def write_counts(worksheet, count_col, updates):
    """Write the RSVP Count column in a single batched API call.

    `updates` is a list of (row_index, value) tuples — only those rows are written;
    other cells in the column are left untouched.
    """
    if not updates:
        return

    data = []
    for row, value in updates:
        cell = rowcol_to_a1(row, count_col)
        data.append({'range': cell, 'values': [[value]]})

    worksheet.batch_update(data, value_input_option='USER_ENTERED')
