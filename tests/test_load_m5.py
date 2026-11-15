import duckdb
import pytest

from ingest.load_m5 import load_m5

SAMPLE_CSVS = {
    "sales_train_evaluation.csv": (
        "id,item_id,dept_id,cat_id,store_id,state_id,d_1,d_2\n"
        "FOODS_1_001_CA_1_evaluation,FOODS_1_001,FOODS_1,FOODS,CA_1,CA,3,0\n"
        "FOODS_1_002_CA_1_evaluation,FOODS_1_002,FOODS_1,FOODS,CA_1,CA,1,2\n"
    ),
    "sell_prices.csv": (
        "store_id,item_id,wm_yr_wk,sell_price\n"
        "CA_1,FOODS_1_001,11101,2.00\n"
        "CA_1,FOODS_1_002,11101,3.50\n"
    ),
    "calendar.csv": (
        "date,wm_yr_wk,weekday,wday,month,year,d,event_name_1,event_type_1,"
        "event_name_2,event_type_2,snap_CA,snap_TX,snap_WI\n"
        "2011-01-29,11101,Saturday,1,1,2011,d_1,,,,,0,0,0\n"
        "2011-01-30,11101,Sunday,2,1,2011,d_2,,,,,0,0,0\n"
    ),
}


@pytest.fixture
def raw_dir(tmp_path):
    folder = tmp_path / "raw"
    folder.mkdir()
    for name, content in SAMPLE_CSVS.items():
        (folder / name).write_text(content)
    return folder


def test_rerun_does_not_duplicate_rows(raw_dir, tmp_path):
    db_path = tmp_path / "test.duckdb"

    first = load_m5(db_path=db_path, raw_dir=raw_dir)
    second = load_m5(db_path=db_path, raw_dir=raw_dir)

    assert first == second == {"sales": 2, "prices": 2, "calendar": 2}


def test_sales_stay_in_wide_format(raw_dir, tmp_path):
    db_path = tmp_path / "test.duckdb"
    load_m5(db_path=db_path, raw_dir=raw_dir)

    with duckdb.connect(str(db_path)) as con:
        columns = con.execute("DESCRIBE raw.sales").fetchall()

    names = [col[0] for col in columns]
    types = {col[0]: col[1] for col in columns}
    assert names == ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id", "d_1", "d_2"]
    assert types["d_1"] == types["d_2"] == "BIGINT"


def test_missing_file_fails_before_loading(raw_dir, tmp_path):
    (raw_dir / "calendar.csv").unlink()
    db_path = tmp_path / "test.duckdb"

    with pytest.raises(FileNotFoundError, match="calendar.csv"):
        load_m5(db_path=db_path, raw_dir=raw_dir)

    assert not db_path.exists()


def test_failed_load_keeps_previous_tables(raw_dir, tmp_path):
    db_path = tmp_path / "test.duckdb"
    load_m5(db_path=db_path, raw_dir=raw_dir)

    # Sales gets a new row, but calendar is now broken, so the whole reload must roll back.
    with open(raw_dir / "sales_train_evaluation.csv", "a") as f:
        f.write("FOODS_1_003_CA_1_evaluation,FOODS_1_003,FOODS_1,FOODS,CA_1,CA,5,5\n")
    (raw_dir / "calendar.csv").write_bytes(b"date,d\n2011-01-29,\xff\xfe\n")  # invalid UTF-8

    with pytest.raises(duckdb.Error):
        load_m5(db_path=db_path, raw_dir=raw_dir)

    with duckdb.connect(str(db_path)) as con:
        assert con.execute("SELECT count(*) FROM raw.sales").fetchone()[0] == 2
