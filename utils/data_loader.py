"""Centralised data loading.

Every table the dashboard shows is read here from data/ (built by scripts/build_data.py from the
study's Step 16 data pack). There is no demonstration data and nothing is generated at run time.

Standard schema returned by `load_food_price_data()`:
    date | commodity | category | region | province | market | unit | price_php | period | market_id | commodity_id
"""
import pandas as pd

from . import config as C

try:  # Streamlit caching is optional so this module also works in plain scripts/tests
    import streamlit as st
    _cache = st.cache_data(show_spinner=False)
except Exception:  # pragma: no cover
    def _cache(fn):
        return fn

STANDARD_COLUMNS = ["date", "commodity", "category", "region", "province",
                    "market", "unit", "price_php", "period", "market_id", "commodity_id"]
_DATE_COLUMNS = ["date", "forecast_origin", "latest_month", "first_month", "last_month", "month"]


def using_demo_data() -> bool:
    return False


def forecasts_are_demo() -> bool:
    return False


def metrics_are_demo() -> bool:
    return False


@_cache
def _read(path_str: str, mtime: float) -> pd.DataFrame:
    head = pd.read_csv(path_str, nrows=0).columns
    return pd.read_csv(path_str, parse_dates=[c for c in _DATE_COLUMNS if c in head])


def _load(path) -> pd.DataFrame:
    return _read(str(path), path.stat().st_mtime)


def load_food_price_data() -> pd.DataFrame:
    """Retail prices (nominal PHP), one row per market x commodity x month."""
    return _load(C.PRICES_PATH)[STANDARD_COLUMNS].copy()


def load_prices_full() -> pd.DataFrame:
    """Retail prices including the study's jump flag and index segment."""
    return _load(C.PRICES_PATH)


def load_holdout() -> pd.DataFrame:
    """Hold-out forecasts: actual price and Seasonal Naive / Naive / SARIMA forecasts (PHP)."""
    return _load(C.HOLDOUT_PATH)


def load_model_metrics() -> pd.DataFrame:
    """Per-series MAE / RMSE / MAPE by period (window) and model."""
    return _load(C.METRICS_PATH)


def load_matched_changes() -> pd.DataFrame:
    """Matched-series % changes between periods (Step 10), plus calendar-balanced % changes (Step 13)."""
    return _load(C.MATCHED_PATH)


def load_period_summary() -> pd.DataFrame:
    """Period comparison medians with 95% CIs and reliability flags, by dimension (overall, category, ...)."""
    return _load(C.PERIOD_SUMMARY_PATH)


def load_forecast_summary() -> pd.DataFrame:
    """Pooled accuracy (record_type 'accuracy') and model-vs-model verdicts ('decision')."""
    return _load(C.FORECAST_SUMMARY_PATH)


def load_future() -> pd.DataFrame:
    """Forward forecasts Jul 2026 - Jun 2027 with prediction intervals (indicative)."""
    return _load(C.FUTURE_PATH)


def load_monitoring() -> pd.DataFrame:
    """Latest month per series: changes, volatility, alert level, last forecast vs. outcome."""
    return _load(C.MONITORING_PATH)


def load_markets() -> pd.DataFrame:
    return _load(C.MARKETS_PATH)


def load_commodities() -> pd.DataFrame:
    return _load(C.COMMODITIES_PATH)


def load_chain_index() -> pd.DataFrame:
    return _load(C.CHAIN_INDEX_PATH)


def load_series_stats() -> pd.DataFrame:
    return _load(C.SERIES_STATS_PATH)


def load_interval_coverage() -> pd.DataFrame:
    return _load(C.INTERVAL_PATH)


def load_about() -> dict:
    """Study key/value text (dash_about) as a dict."""
    a = pd.read_csv(C.ABOUT_PATH)
    return dict(zip(a["key"], a["value"]))
