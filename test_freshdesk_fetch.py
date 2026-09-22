from datetime import date, datetime, timezone

from freshdesk_fetch import freshdesk_created_between_query, month_ranges_until


def test_month_ranges_cover_year_to_current_month():
    ranges = list(month_ranges_until(date(2026, 3, 15)))

    assert ranges == [
        (
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc),
        ),
        (
            datetime(2026, 2, 1, tzinfo=timezone.utc),
            datetime(2026, 2, 28, 23, 59, 59, tzinfo=timezone.utc),
        ),
        (
            datetime(2026, 3, 1, tzinfo=timezone.utc),
            datetime(2026, 3, 31, 23, 59, 59, tzinfo=timezone.utc),
        ),
    ]


def test_freshdesk_created_between_query_uses_utc_date_fields():
    query = freshdesk_created_between_query(
        datetime(2026, 3, 1, tzinfo=timezone.utc),
        datetime(2026, 3, 31, 23, 59, 59, tzinfo=timezone.utc),
    )

    assert query == (
        "created_at:>'2026-03-01' "
        "AND created_at:<'2026-03-31'"
    )


if __name__ == "__main__":
    test_month_ranges_cover_year_to_current_month()
    test_freshdesk_created_between_query_uses_utc_date_fields()
