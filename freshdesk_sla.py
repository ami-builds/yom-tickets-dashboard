import pandas as pd


def _freshdesk_true(value):
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    try:
        return bool(value == 1)
    except (TypeError, ValueError):
        return False


def _ticket_flag(row, *names):
    stats = row.get('stats')
    for name in names:
        if _freshdesk_true(row.get(name)):
            return True
        if isinstance(stats, dict) and _freshdesk_true(stats.get(name)):
            return True
    return False


def _timestamp(value):
    if value is None:
        return pd.NaT
    return pd.to_datetime(value, errors='coerce', utc=True)


def _row_timestamp(row, name):
    value = row.get(name)
    if value is None:
        stats = row.get('stats')
        if isinstance(stats, dict):
            value = stats.get(name)
    return _timestamp(value)


def is_resolution_sla_breached(row):
    if _ticket_flag(row, 'is_escalated', 'resolution_escalated'):
        return True

    due = _row_timestamp(row, 'due_by')
    resolved = _row_timestamp(row, 'resolved_at')
    closed = _row_timestamp(row, 'closed_at')
    resolved_or_closed = resolved if pd.notna(resolved) else closed

    return pd.notna(due) and pd.notna(resolved_or_closed) and resolved_or_closed > due


def is_first_response_sla_breached(row):
    return _ticket_flag(row, 'fr_escalated', 'first_response_escalated')
