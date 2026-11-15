"""Load the M5 CSV files into DuckDB as raw tables.

Each run rebuilds the tables from the CSVs, so rerunning never duplicates rows.
"""

from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DB_PATH = PROJECT_ROOT / "data" / "warehouse.duckdb"

# DuckDB table name -> source CSV file
M5_FILES = {
    "sales": "sales_train_evaluation.csv",
    "prices": "sell_prices.csv",
    "calendar": "calendar.csv",
}


def load_m5(db_path: Path = DB_PATH, raw_dir: Path = RAW_DIR) -> dict[str, int]:
    """Load each M5 CSV into raw.<table> and return the row count per table."""
    missing = [name for name in M5_FILES.values() if not (raw_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing in {raw_dir}: {', '.join(missing)}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    row_counts = {}

    with duckdb.connect(str(db_path)) as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        for table, filename in M5_FILES.items():
            csv_path = (raw_dir / filename).as_posix()
            con.execute(
                f"CREATE OR REPLACE TABLE raw.{table} AS "
                f"SELECT * FROM read_csv('{csv_path}', header = true)"
            )
            row_counts[table] = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]

    return row_counts


if __name__ == "__main__":
    for table, rows in load_m5().items():
        print(f"raw.{table}: {rows:,} rows")
