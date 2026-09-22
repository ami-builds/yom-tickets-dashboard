from datetime import date
from zoneinfo import ZoneInfo

import pandas as pd

from freshdesk_sla import is_first_response_sla_breached, is_resolution_sla_breached
from monthly_metrics import build_monthly_comparison


CHILE_TZ = ZoneInfo("America/Santiago")


def test_resolution_sla_breach_reads_stats_flags():
    row = pd.Series({
        'is_escalated': False,
        'stats': {'resolution_escalated': True},
    })

    assert is_resolution_sla_breached(row) is True


def test_resolution_sla_breach_accepts_pandas_boolean_scalars():
    row = pd.DataFrame([{'is_escalated': True, 'stats': {}}]).iloc[0]

    assert is_resolution_sla_breached(row) is True


def test_first_response_breach_does_not_count_as_resolution_breach():
    row = pd.Series({
        'fr_escalated': True,
        'is_escalated': False,
        'stats': {'resolution_escalated': False},
    })

    assert is_first_response_sla_breached(row) is True
    assert is_resolution_sla_breached(row) is False


def test_null_sla_flags_are_not_breaches():
    row = pd.Series({
        'is_escalated': pd.NA,
        'stats': {'resolution_escalated': pd.NA},
    })

    assert is_resolution_sla_breached(row) is False


def test_march_compliance_drops_when_closed_ticket_has_stats_resolution_breach():
    rows = [
        {
            'id': 1,
            'status': 5,
            'created_at': pd.Timestamp('2026-03-02T12:00:00Z'),
            'resolved_at': pd.Timestamp('2026-03-03T12:00:00Z'),
            'closed_at': pd.NaT,
            'due_by': pd.Timestamp('2026-03-03T13:00:00Z'),
            'stats': {'resolution_escalated': False},
        },
        {
            'id': 2,
            'status': 5,
            'created_at': pd.Timestamp('2026-03-04T12:00:00Z'),
            'resolved_at': pd.Timestamp('2026-03-06T12:00:00Z'),
            'closed_at': pd.NaT,
            'due_by': pd.Timestamp('2026-03-05T12:00:00Z'),
            'stats': {'resolution_escalated': True},
        },
    ]
    df = pd.DataFrame(rows)
    df['sla_met'] = df.apply(lambda row: not is_resolution_sla_breached(row), axis=1)
    df['sla_status'] = df['sla_met'].map({
        True: 'Resuelto a tiempo',
        False: 'Resuelto tarde',
    })

    table = build_monthly_comparison(
        df,
        ['Marzo'],
        ['Cerrados', 'SLA Vencido', 'SLA Compliance %'],
        date(2026, 9, 22),
        CHILE_TZ,
    )

    march = table.iloc[0]
    assert march['Cerrados'] == 2
    assert march['SLA Vencido'] == 1
    assert march['SLA Compliance %'] == 50


if __name__ == "__main__":
    test_resolution_sla_breach_reads_stats_flags()
    test_resolution_sla_breach_accepts_pandas_boolean_scalars()
    test_first_response_breach_does_not_count_as_resolution_breach()
    test_null_sla_flags_are_not_breaches()
    test_march_compliance_drops_when_closed_ticket_has_stats_resolution_breach()
