"""Load daily historical weather per M5 state from Open-Meteo into DuckDB.

M5 does not say where its stores are, so each state uses one large city.
Each run rebuilds raw.weather, so rerunning never duplicates rows.
"""

from datetime import date
from pathlib import Path

import duckdb
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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


def _session_with_retries() -> requests.Session:
    """A session that retries rate limits (429) and server errors, waiting 2s, 4s, then 8s."""
    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_daily_weather(location: dict, start_date: str, end_date: str) -> dict:
    """Call Open-Meteo for one location and return the 'daily' block of the response."""
    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "timezone": location["timezone"],
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join(DAILY_FIELDS),
    }
    with _session_with_retries() as session:
        response = session.get(API_URL, params=params, timeout=60)

    if not response.ok:
        try:
            reason = response.json().get("reason", response.text)
        except ValueError:
            reason = response.text
        raise requests.HTTPError(
            f"Open-Meteo returned {response.status_code} for {location['city']}: {reason}",
            response=response,
        )
    return response.json()["daily"]


def to_rows(state_id: str, daily: dict, start_date: str, end_date: str) -> list[tuple]:
    """Check the response covers every day in the range, then turn its columns into rows."""
    missing = [field for field in ["time", *DAILY_FIELDS] if field not in daily]
    if missing:
        raise ValueError(f"Open-Meteo response for {state_id} is missing: {', '.join(missing)}")

    columns = [daily["time"]] + [daily[field] for field in DAILY_FIELDS]
    if len({len(col) for col in columns}) != 1:
        raise ValueError(f"Open-Meteo returned lists of different lengths for {state_id}")

    expected_days = (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days + 1
    times = daily["time"]
    if len(times) != expected_days or times[0] != start_date or times[-1] != end_date:
        raise ValueError(
            f"Open-Meteo returned {len(times)} days for {state_id}, "
            f"expected {expected_days} from {start_date} to {end_date}"
        )

    return [(state_id, *values) for values in zip(*columns)]


def load_weather(
    db_path: Path = DB_PATH,
    fetch=fetch_daily_weather,
    start_date: str = START_DATE,
    end_date: str = END_DATE,
) -> int:
    """Fetch every state, then replace raw.weather in one transaction. Returns the row count."""
    rows = []
    for state_id, location in STATE_LOCATIONS.items():
        daily = fetch(location, start_date, end_date)
        rows.extend(to_rows(state_id, daily, start_date, end_date))

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
