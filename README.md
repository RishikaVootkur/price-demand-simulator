# Retail Price-Demand Simulator

An end-to-end ML pipeline that learns how price affects demand for each Walmart item and store, and a Streamlit app where a pricing analyst can test "what if I change the price by X%?" before changing it.

## Data

- [M5 Forecasting](https://www.kaggle.com/competitions/m5-forecasting-accuracy/data): 5 years of daily Walmart unit sales, weekly prices, and a calendar of holidays and events for 10 stores in 3 states.
- [Open-Meteo](https://open-meteo.com/): daily historical temperature and rain per state.

Raw data is not committed. It is downloaded into `data/raw/`.

## Stack

DuckDB, dbt-duckdb, Dagster, MLflow, LightGBM, statsmodels, Streamlit, pytest, SQLFluff, GitHub Actions.

## Setup

```bash
uv sync                      # create .venv and install locked dependencies
# Kaggle token must be saved at ~/.kaggle/access_token, and the M5 competition rules accepted
uv run kaggle competitions download -c m5-forecasting-accuracy -p data/raw
unzip -o data/raw/m5-forecasting-accuracy.zip calendar.csv sell_prices.csv sales_train_evaluation.csv -d data/raw \
  && rm data/raw/m5-forecasting-accuracy.zip
```

## Repo layout

```
ingest/          Python loaders: CSV and API to DuckDB raw tables
dbt_project/     staging, intermediate, marts
ml/              training, evaluation, elasticity
app/             Streamlit simulator
orchestration/   Dagster assets, schedules, checks
tests/           pytest
data/            raw files and DuckDB file (gitignored)
```
