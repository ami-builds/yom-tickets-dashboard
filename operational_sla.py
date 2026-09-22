import re

import pandas as pd
from zoneinfo import ZoneInfo


SLA_HOURS_BY_PRIORITY = {
    4: 9,
    3: 9,
    2: 18,
    1: 40,
}

LEVEL_PRIORITY_PATTERNS = [
    (re.compile(r"\b(?:n1|nivel\s*1|alta)\b", re.IGNORECASE), 3),
    (re.compile(r"\b(?:n2|nivel\s*2|media)\b", re.IGNORECASE), 2),
    (re.compile(r"\b(?:n3|nivel\s*3|baja)\b", re.IGNORECASE), 1),
]


def _timestamp(value):
    if value is None:
        return pd.NaT
    return pd.to_datetime(value, errors='coerce', utc=True)


def _resolution_at(row):
    resolved = _timestamp(row.get('resolved_at'))
    closed = _timestamp(row.get('closed_at'))
    return resolved if pd.notna(resolved) else closed


def _iter_freshdesk_labels(row):
    tags = row.get('tags')
    if isinstance(tags, list):
        for tag in tags:
            yield str(tag)

    custom_fields = row.get('custom_fields')
    if isinstance(custom_fields, dict):
        for key, value in custom_fields.items():
            if value is not None:
                yield f"{key} {value}"

    for name in ('priority_name', 'subject', 'type'):
        value = row.get(name)
        if value is not None:
            yield str(value)


def effective_priority(row):
    """
    Prefer an explicit support level stored in Freshdesk labels/custom fields.
    Freshdesk priority is the fallback because old tickets often defaulted to Low.
    """
    labels = " ".join(_iter_freshdesk_labels(row))
    for pattern, priority in LEVEL_PRIORITY_PATTERNS:
        if pattern.search(labels):
            return priority

    try:
        priority = int(row.get('priority'))
    except (TypeError, ValueError):
        return None
    return priority if priority in SLA_HOURS_BY_PRIORITY else None


def business_hours_between(start, end, local_tz):
    start = _timestamp(start)
    end = _timestamp(end)
    if pd.isna(start) or pd.isna(end) or end <= start:
        return 0.0

    if isinstance(local_tz, str):
        local_tz = ZoneInfo(local_tz)

    start_local = start.tz_convert(local_tz)
    end_local = end.tz_convert(local_tz)
    cursor = start_local.normalize()
    total_seconds = 0.0

    while cursor <= end_local.normalize():
        if cursor.weekday() < 5:
            work_start = cursor + pd.Timedelta(hours=8)
            work_end = cursor + pd.Timedelta(hours=19)
            overlap_start = max(start_local, work_start)
            overlap_end = min(end_local, work_end)
            if overlap_end > overlap_start:
                total_seconds += (overlap_end - overlap_start).total_seconds()
        cursor += pd.Timedelta(days=1)

    return total_seconds / 3600


def waiting_business_hours_from_conversations(convs, start, end, local_tz):
    if not convs:
        return 0.0

    start = _timestamp(start)
    end = _timestamp(end)
    if pd.isna(start) or pd.isna(end) or end <= start:
        return 0.0

    public = []
    for conv in convs:
        if conv.get('private'):
            continue
        ts = _timestamp(conv.get('created_at'))
        if pd.isna(ts):
            continue
        public.append((ts, bool(conv.get('incoming'))))

    public.sort()

    total = 0.0
    last_agent_reply = None
    for ts, incoming in public:
        if incoming:
            if last_agent_reply is not None:
                wait_start = max(last_agent_reply, start)
                wait_end = min(ts, end)
                total += business_hours_between(wait_start, wait_end, local_tz)
                last_agent_reply = None
        elif last_agent_reply is None:
            last_agent_reply = ts

    return total


def operational_sla_result(row, convs=None, local_tz='America/Santiago'):
    priority = effective_priority(row)
    limit_hours = SLA_HOURS_BY_PRIORITY.get(priority)
    created = _timestamp(row.get('created_at'))
    resolved = _resolution_at(row)

    if limit_hours is None or pd.isna(created) or pd.isna(resolved):
        return {
            'sla_met': None,
            'business_hours': None,
            'limit_hours': limit_hours,
        }

    elapsed = business_hours_between(created, resolved, local_tz)
    waiting = waiting_business_hours_from_conversations(convs, created, resolved, local_tz)
    business_hours = max(elapsed - waiting, 0.0)

    return {
        'sla_met': business_hours <= limit_hours,
        'business_hours': round(business_hours, 2),
        'limit_hours': limit_hours,
    }


def apply_operational_sla(df, conversations_by_id=None, local_tz='America/Santiago'):
    if df.empty:
        return df

    conversations_by_id = conversations_by_id or {}
    enriched = df.copy()
    enriched['sla_business_hours'] = None
    enriched['sla_limit_hours'] = None

    closed_mask = enriched['status'].isin([4, 5])
    for idx, row in enriched[closed_mask].iterrows():
        result = operational_sla_result(
            row,
            conversations_by_id.get(row.get('id')),
            local_tz,
        )
        if result['limit_hours'] is not None:
            enriched.at[idx, 'sla_limit_hours'] = result['limit_hours']
        if result['business_hours'] is not None:
            enriched.at[idx, 'sla_business_hours'] = result['business_hours']
        if result['sla_met'] is not None:
            enriched.at[idx, 'sla_met'] = result['sla_met']
            enriched.at[idx, 'sla_status'] = (
                'Resuelto a tiempo' if result['sla_met'] else 'Resuelto tarde'
            )

    return enriched
