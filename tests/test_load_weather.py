import datetime

import duckdb
import pytest
import requests

from ingest.load_weather import STATE_LOCATIONS, load_weather, to_rows

FAKE_DAILY = {
    "time": ["2011-01-29", "2011-01-30"],
    "temperature_2m_max": [18.1, 13.1],
    "temperature_2m_min": [6.1, 7.6],
    "precipitation_sum": [0.0, 1.0],
}


def fake_fetch(location):
    return FAKE_DAILY


def test_to_rows_turns_columns_into_rows():
    assert to_rows("CA", FAKE_DAILY) == [
        ("CA", "2011-01-29", 18.1, 6.1, 0.0),
        ("CA", "2011-01-30", 13.1, 7.6, 1.0),
    ]


def test_to_rows_rejects_uneven_lists():
    uneven = {**FAKE_DAILY, "precipitation_sum": [0.0]}
    with pytest.raises(ValueError, match="different lengths"):
        to_rows("CA", uneven)


def test_rerun_does_not_duplicate_rows(tmp_path):
    db_path = tmp_path / "test.duckdb"
    expected = 2 * len(STATE_LOCATIONS)

    assert load_weather(db_path=db_path, fetch=fake_fetch) == expected
    assert load_weather(db_path=db_path, fetch=fake_fetch) == expected

    with duckdb.connect(str(db_path)) as con:
        assert con.execute("SELECT count(*) FROM raw.weather").fetchone()[0] == expected
        unique_keys = con.execute("SELECT count(DISTINCT (state_id, date)) FROM raw.weather").fetchone()[0]
        first_date = con.execute("SELECT min(date) FROM raw.weather").fetchone()[0]

    assert unique_keys == expected
    assert first_date == datetime.date(2011, 1, 29)


def test_failed_fetch_keeps_previous_table(tmp_path):
    db_path = tmp_path / "test.duckdb"
    load_weather(db_path=db_path, fetch=fake_fetch)

    def broken_fetch(location):
        raise requests.HTTPError("503 Service Unavailable")

    with pytest.raises(requests.HTTPError):
        load_weather(db_path=db_path, fetch=broken_fetch)

    with duckdb.connect(str(db_path)) as con:
        assert con.execute("SELECT count(*) FROM raw.weather").fetchone()[0] == 2 * len(STATE_LOCATIONS)
