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


def is_resolution_sla_breached(row):
    return _ticket_flag(row, 'is_escalated', 'resolution_escalated')


def is_first_response_sla_breached(row):
    return _ticket_flag(row, 'fr_escalated', 'first_response_escalated')
