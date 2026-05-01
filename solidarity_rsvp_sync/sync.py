from .solidarity import SolidarityClient
from .sheets import (
    open_worksheet,
    read_rows,
    read_service_account_email,
    write_counts,
    COUNT_COL,
)
from .utils import create_logger, ok, warn, err, hl


def run_sync(api_token, credentials_path, sheet_id, sheet_name):
    logger = create_logger('[sync]')

    logger(f'using service account {hl(read_service_account_email(credentials_path))}')
    logger(f'opening sheet {hl(sheet_id)} / tab {hl(sheet_name)}')
    worksheet = open_worksheet(credentials_path, sheet_id, sheet_name)
    header_to_col, rows = read_rows(worksheet)
    count_col = header_to_col[COUNT_COL]

    logger(f'found {hl(len(rows))} rows')

    client = SolidarityClient(api_token, logger=create_logger('[api]'))

    updates = []
    failed = 0
    skipped = 0

    for row in rows:
        event_id = row['event_id']
        session_id = row['session_id']

        if not event_id and not session_id:
            skipped += 1
            continue

        if not event_id and session_id:
            logger(
                err(f'row {row["row"]}: session id without event id — skipping')
            )
            failed += 1
            continue

        try:
            count = client.count_rsvps(event_id, session_id)
            label = f'event={event_id}'
            if session_id:
                label += f' session={session_id}'
            logger(f'row {row["row"]} {label} → {hl(count)}')
            updates.append((row['row'], count))
        except Exception as e:
            logger(err(f'row {row["row"]} event={event_id} session={session_id}: {e}'))
            failed += 1

    write_failed = False
    if updates:
        logger(f'writing {hl(len(updates))} rows to sheet')
        try:
            write_counts(worksheet, count_col, updates)
        except Exception as e:
            logger(err(f'sheet write failed: {e}'))
            logger(
                err(
                    'if the message mentions a protected cell, give the service '
                    'account edit access to the RSVP Count range (or remove the '
                    'protection). see README.'
                )
            )
            write_failed = True
    else:
        logger(warn('no successful counts to write'))

    logger(
        f'done — {ok(f"{len(updates)} updated") if not write_failed else err(f"{len(updates)} computed but not written")}, '
        f'{warn(f"{skipped} skipped")}, '
        f'{err(f"{failed} failed")}'
    )

    return failed + (1 if write_failed else 0)
