"""Load daily historical weather per M5 state from Open-Meteo into DuckDB.

M5 does not say where its stores are, so each state uses one large city.
Each run rebuilds raw.weather, so rerunning never duplicates rows.
"""

from pathlib import Path

import duckdb
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "warehouse.duckdb"

API_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY_FIELDS = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"]

# Same date range as the M5 calendar
START_DATE = "2011-01-29"
END_DATE = "2016-06-19"

STATE_LOCATIONS = {
    "CA": {"city": "Los Angeles", "latitude": 34.05, "longitude": -118.24, "timezone": "America/Los_Angeles"},
    "TX": {"city": "Dallas", "latitude": 32.78, "longitude": -96.80, "timezone": "America/Chicago"},
    "WI": {"city": "Milwaukee", "latitude": 43.04, "longitude": -87.91, "timezone": "America/Chicago"},
}


def fetch_daily_weather(location: dict, start_date: str = START_DATE, end_date: str = END_DATE) -> dict:
    """Call Open-Meteo for one location and return the 'daily' block of the response."""
    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "timezone": location["timezone"],
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join(DAILY_FIELDS),
    }
    response = requests.get(API_URL, params=params, timeout=60)
    response.raise_for_status()
    return response.json()["daily"]


def to_rows(state_id: str, daily: dict) -> list[tuple]:
    """Turn Open-Meteo's column lists into one (state, date, max, min, rain) tuple per day."""
    columns = [daily["time"]] + [daily[field] for field in DAILY_FIELDS]
    if len({len(col) for col in columns}) != 1:
        raise ValueError(f"Open-Meteo returned lists of different lengths for {state_id}")
    return [(state_id, *values) for values in zip(*columns)]


def load_weather(db_path: Path = DB_PATH, fetch=fetch_daily_weather) -> int:
    """Fetch every state, then replace raw.weather in one transaction. Returns the row count."""
    rows = []
    for state_id, location in STATE_LOCATIONS.items():
        rows.extend(to_rows(state_id, fetch(location)))

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as con:
        con.begin()
        try:
            con.execute("CREATE SCHEMA IF NOT EXISTS raw")
            con.execute(
                """
                CREATE OR REPLACE TABLE raw.weather (
                    state_id VARCHAR,
                    date DATE,
                    temperature_2m_max DOUBLE,
                    temperature_2m_min DOUBLE,
                    precipitation_sum DOUBLE
                )
                """
            )
            con.executemany("INSERT INTO raw.weather VALUES (?, ?, ?, ?, ?)", rows)
            con.commit()
        except Exception:
            con.rollback()
            raise

    return len(rows)


if __name__ == "__main__":
    print(f"raw.weather: {load_weather():,} rows")
