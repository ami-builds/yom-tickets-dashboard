from datetime import date, datetime, timedelta, timezone


def month_ranges_until(today=None):
    today = today or date.today()
    for month in range(1, today.month + 1):
        start = datetime(today.year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            next_month = datetime(today.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month = datetime(today.year, month + 1, 1, tzinfo=timezone.utc)
        yield start, next_month - timedelta(seconds=1)


def freshdesk_created_between_query(start, end):
    start_utc = start.astimezone(timezone.utc)
    end_utc = end.astimezone(timezone.utc)
    return (
        "created_at:>'{start}' AND created_at:<'{end}'"
    ).format(
        start=start_utc.strftime('%Y-%m-%d'),
        end=end_utc.strftime('%Y-%m-%d'),
    )
