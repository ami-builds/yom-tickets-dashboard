from zoneinfo import ZoneInfo

import pandas as pd

from operational_sla import (
    apply_operational_sla,
    business_hours_between,
    effective_priority,
    operational_sla_result,
)


CHILE_TZ = ZoneInfo("America/Santiago")


def test_business_hours_between_uses_chile_workday_window():
    hours = business_hours_between(
        pd.Timestamp('2026-03-06T20:00:00Z'),
        pd.Timestamp('2026-03-09T14:00:00Z'),
        CHILE_TZ,
    )

    assert hours == 5


def test_effective_priority_prefers_freshdesk_support_level_tags():
    row = pd.Series({
        'priority': 1,
        'tags': ['soporte', 'N2'],
        'custom_fields': {},
    })

    assert effective_priority(row) == 2


def test_operational_sla_marks_high_priority_ticket_late_by_business_hours():
    row = pd.Series({
        'id': 668,
        'priority': 1,
        'tags': ['N1'],
        'created_at': '2026-03-02T11:00:00Z',
        'resolved_at': '2026-03-03T17:00:00Z',
        'closed_at': pd.NaT,
    })

    result = operational_sla_result(row, [], CHILE_TZ)

    assert result['limit_hours'] == 9
    assert result['business_hours'] == 17
    assert result['sla_met'] is False


def test_operational_sla_subtracts_customer_waiting_business_hours():
    row = pd.Series({
        'id': 669,
        'priority': 2,
        'tags': [],
        'created_at': '2026-03-02T11:00:00Z',
        'resolved_at': '2026-03-03T17:00:00Z',
        'closed_at': pd.NaT,
    })
    convs = [
        {'created_at': '2026-03-02T14:00:00Z', 'incoming': False, 'private': False},
        {'created_at': '2026-03-03T14:00:00Z', 'incoming': True, 'private': False},
    ]

    result = operational_sla_result(row, convs, CHILE_TZ)

    assert result['business_hours'] == 6
    assert result['sla_met'] is True


def test_apply_operational_sla_updates_closed_ticket_status():
    df = pd.DataFrame([{
        'id': 670,
        'status': 5,
        'priority': 3,
        'tags': [],
        'created_at': pd.Timestamp('2026-03-02T11:00:00Z'),
        'resolved_at': pd.Timestamp('2026-03-03T17:00:00Z'),
        'closed_at': pd.NaT,
        'sla_met': True,
        'sla_status': 'Resuelto a tiempo',
    }])

    enriched = apply_operational_sla(df, {}, CHILE_TZ)

    assert enriched.loc[0, 'sla_met'] == False
    assert enriched.loc[0, 'sla_status'] == 'Resuelto tarde'


if __name__ == "__main__":
    test_business_hours_between_uses_chile_workday_window()
    test_effective_priority_prefers_freshdesk_support_level_tags()
    test_operational_sla_marks_high_priority_ticket_late_by_business_hours()
    test_operational_sla_subtracts_customer_waiting_business_hours()
    test_apply_operational_sla_updates_closed_ticket_status()
