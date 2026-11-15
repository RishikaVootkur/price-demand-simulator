import datetime

import duckdb
import pytest
import requests

from ingest import load_weather as weather
from ingest.load_weather import STATE_LOCATIONS, load_weather, to_rows

START, END = "2011-01-29", "2011-01-30"

FAKE_DAILY = {
    "time": [START, END],
    "temperature_2m_max": [18.1, 13.1],
    "temperature_2m_min": [6.1, 7.6],
    "precipitation_sum": [0.0, 1.0],
}


def fake_fetch(location, start_date, end_date):
    return FAKE_DAILY


def test_to_rows_turns_columns_into_rows():
    assert to_rows("CA", FAKE_DAILY, START, END) == [
        ("CA", "2011-01-29", 18.1, 6.1, 0.0),
        ("CA", "2011-01-30", 13.1, 7.6, 1.0),
    ]


def test_to_rows_rejects_uneven_lists():
    uneven = {**FAKE_DAILY, "precipitation_sum": [0.0]}
    with pytest.raises(ValueError, match="different lengths"):
        to_rows("CA", uneven, START, END)


def test_to_rows_rejects_missing_days():
    with pytest.raises(ValueError, match="expected 3"):
        to_rows("CA", FAKE_DAILY, START, "2011-01-31")


def test_to_rows_rejects_missing_field():
    no_rain = {k: v for k, v in FAKE_DAILY.items() if k != "precipitation_sum"}
    with pytest.raises(ValueError, match="missing: precipitation_sum"):
        to_rows("CA", no_rain, START, END)


def test_each_state_is_fetched_with_its_own_location(tmp_path):
    calls = []

    def recording_fetch(location, start_date, end_date):
        calls.append((location, start_date, end_date))
        return FAKE_DAILY

    load_weather(db_path=tmp_path / "test.duckdb", fetch=recording_fetch, start_date=START, end_date=END)

    assert calls == [(loc, START, END) for loc in STATE_LOCATIONS.values()]


def test_rerun_does_not_duplicate_rows(tmp_path):
    db_path = tmp_path / "test.duckdb"
    expected = 2 * len(STATE_LOCATIONS)

    for _ in range(2):
        assert load_weather(db_path=db_path, fetch=fake_fetch, start_date=START, end_date=END) == expected

    with duckdb.connect(str(db_path)) as con:
        assert con.execute("SELECT count(*) FROM raw.weather").fetchone()[0] == expected
        unique_keys = con.execute("SELECT count(DISTINCT (state_id, date)) FROM raw.weather").fetchone()[0]
        first_date = con.execute("SELECT min(date) FROM raw.weather").fetchone()[0]

    assert unique_keys == expected
    assert first_date == datetime.date(2011, 1, 29)


def test_failed_fetch_keeps_previous_table(tmp_path):
    db_path = tmp_path / "test.duckdb"
    load_weather(db_path=db_path, fetch=fake_fetch, start_date=START, end_date=END)

    def broken_fetch(location, start_date, end_date):
        raise requests.HTTPError("503 Service Unavailable")

    with pytest.raises(requests.HTTPError):
        load_weather(db_path=db_path, fetch=broken_fetch, start_date=START, end_date=END)

    with duckdb.connect(str(db_path)) as con:
        assert con.execute("SELECT count(*) FROM raw.weather").fetchone()[0] == 2 * len(STATE_LOCATIONS)


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.ok = status_code < 400
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


def test_api_error_reason_is_shown(monkeypatch):
    monkeypatch.setattr(
        requests.Session, "get",
        lambda self, url, params, timeout: FakeResponse(400, {"error": True, "reason": "bad start_date"}),
    )
    with pytest.raises(requests.HTTPError, match="400 for Los Angeles: bad start_date"):
        weather.fetch_daily_weather(STATE_LOCATIONS["CA"], START, END)


def test_fetch_sends_location_and_fields(monkeypatch):
    sent = {}

    def fake_get(self, url, params, timeout):
        sent.update(params)
        return FakeResponse(200, {"daily": FAKE_DAILY})

    monkeypatch.setattr(requests.Session, "get", fake_get)
    weather.fetch_daily_weather(STATE_LOCATIONS["TX"], START, END)

    assert sent["latitude"] == 32.78 and sent["timezone"] == "America/Chicago"
    assert sent["daily"] == "temperature_2m_max,temperature_2m_min,precipitation_sum"
