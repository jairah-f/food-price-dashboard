"""Fixed research metadata and shared constants.

Nothing in this file is generated: file paths, the study's period definitions and the palette.
Dataset coverage figures are computed from the loaded data (see utils/ui_analytics.py).
"""
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
ASSETS_DIR = ROOT_DIR / "assets"

# ---- Research data files (built from the study's Step 16 data pack by scripts/build_data.py) ----
PRICES_PATH = DATA_DIR / "prices.csv.gz"                  # dash_prices: retail prices
HOLDOUT_PATH = DATA_DIR / "holdout.csv.gz"                # dash_forecast_holdout: actual + 3 models, 3 test windows
METRICS_PATH = DATA_DIR / "model_metrics.csv.gz"          # dash_forecast_metrics: MAE / RMSE / MAPE per series
MATCHED_PATH = DATA_DIR / "matched_changes.csv.gz"        # dash_period_series: matched-series % changes
PERIOD_SUMMARY_PATH = DATA_DIR / "period_summary.csv"     # dash_period_summary: medians, CIs, reliability
FORECAST_SUMMARY_PATH = DATA_DIR / "forecast_summary.csv" # dash_forecast_summary: pooled accuracy + model verdicts
FUTURE_PATH = DATA_DIR / "forecast_future.csv.gz"         # dash_forecast_future: Jul 2026 - Jun 2027
MONITORING_PATH = DATA_DIR / "monitoring.csv.gz"          # dash_monitoring: latest month, alerts
MARKETS_PATH = DATA_DIR / "markets.csv"                   # dash_markets
COMMODITIES_PATH = DATA_DIR / "commodities.csv"           # dash_commodities
CHAIN_INDEX_PATH = DATA_DIR / "chain_index.csv"           # dash_chain_index
SERIES_STATS_PATH = DATA_DIR / "series_stats.csv"         # dash_series_stats: trend and volatility
INTERVAL_PATH = DATA_DIR / "interval_coverage.csv"        # 16_interval_calibration_check
ABOUT_PATH = DATA_DIR / "about.csv"                       # dash_about

# Raw WFP file: 210,339 records, of which 2,615 are wholesale (study notebook 01). Only retail is analysed.
RAW_RECORDS = 210339
WHOLESALE_EXCLUDED = 2615

# ---- Pandemic periods -------------------------------------------------------
PERIODS = {
    # Study definitions (notebooks/study_config.py). Jun 2019 - Apr 2020 is excluded (too thin / no data).
    "Pre-Pandemic": (pd.Timestamp("2016-01-01"), pd.Timestamp("2019-05-31")),
    "Pandemic": (pd.Timestamp("2020-05-01"), pd.Timestamp("2023-05-31")),
    "Post-Pandemic": (pd.Timestamp("2023-06-01"), pd.Timestamp("2026-06-30")),
}
PERIOD_ORDER = list(PERIODS)
# Months excluded from the study (too thin / no data); no observations exist in this range.
EXCLUDED_RANGE = (pd.Timestamp("2019-06-01"), pd.Timestamp("2020-04-30"))
EXCLUDED_LABEL = "Jun 2019 – Apr 2020"

# Forecast evaluation windows (notebooks/study_config.py, 11_window_design.csv):
# model fitted on the training range, evaluated on the 12 test months.
EVAL_WINDOWS = {
    "Pre-Pandemic": ("Jan 2016 – May 2018", "Jun 2018 – May 2019"),
    "Pandemic": ("May 2020 – May 2022", "Jun 2022 – May 2023"),
    "Post-Pandemic": ("May 2020 – Jun 2025", "Jul 2025 – Jun 2026"),
}
PERIOD_RANGE_LABELS = {
    "Pre-Pandemic": "Jan 2016 – May 2019",
    "Pandemic": "May 2020 – May 2023",
    "Post-Pandemic": "Jun 2023 – Jun 2026",
}

# ---- Forecasting ------------------------------------------------------------
MODELS = ["Seasonal Naive", "Naive", "SARIMA"]
HORIZONS = [3, 6, 9, 12]
# Hold-out window shown on the Forecasting page: the study's most recent test window
# (model fitted on May 2020 - Jun 2025, tested on Jul 2025 - Jun 2026). Eligibility follows the study's
# rule (>=80% of training months observed, no gap > 3 months, >= 9 of 12 test months observed).
FORECAST_PERIOD = "Post-Pandemic"
# Forward forecasts (Step 16): refit through Jun 2026, 12 months ahead. The study flags them as indicative.
FUTURE_LABEL = "Jul 2026 – Jun 2027"
INTERVAL_LEVELS = ["80%", "95%"]

# Default selections (used only if present in the loaded data)
DEFAULT_COMMODITY = "Rice (regular, milled)"

# ---- Palette ----------------------------------------------------------------
NAVY = "#1F3A5F"
GREEN = "#5B8C6A"
SLATE = "#8FA9C7"
SAND = "#C9B27C"
INK = "#1B2430"
MUTED = "#6B7684"
GRID = "#E6EAF0"
CATEGORY_COLORS = [NAVY, GREEN, SLATE, SAND, "#7C8B9A", "#A8C3A0"]
PERIOD_COLORS = {"Pre-Pandemic": SLATE, "Pandemic": NAVY, "Post-Pandemic": GREEN}
MODEL_COLORS = {"Seasonal Naive": SLATE, "Naive": SAND, "SARIMA": GREEN}
