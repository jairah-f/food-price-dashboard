"""Analysis layer: summaries, period comparison, forecasts, evaluation metrics, monitoring.

No Streamlit code here. Forecasts, metrics, period summaries and alerts are read from the
study's Step 16 data pack (data/*.csv[.gz], built by scripts/build_data.py).
"""
import numpy as np
import pandas as pd

from .config import FORECAST_PERIOD, PERIOD_ORDER, PERIODS
from .data_loader import (load_forecast_summary, load_future, load_holdout, load_matched_changes,
                          load_model_metrics, load_monitoring, load_period_summary)


# --------------------------------------------------------------------------- #
# Historical helpers
# --------------------------------------------------------------------------- #
def monthly_series(df: pd.DataFrame) -> pd.DataFrame:
    """Mean price per date across whatever rows are passed in -> [date, price]."""
    if df.empty:
        return pd.DataFrame(columns=["date", "price"])
    out = df.groupby("date", as_index=False)["price_php"].mean()
    return out.rename(columns={"price_php": "price"}).sort_values("date").reset_index(drop=True)


def historical_summary(series: pd.DataFrame) -> dict:
    """Average / min / max / % change for a [date, price] series."""
    if series.empty:
        return {}
    s = series.sort_values("date")
    first, last = float(s["price"].iloc[0]), float(s["price"].iloc[-1])
    i_min, i_max = s["price"].idxmin(), s["price"].idxmax()
    return {
        "avg": float(s["price"].mean()),
        "min": float(s.loc[i_min, "price"]), "min_date": s.loc[i_min, "date"],
        "max": float(s.loc[i_max, "price"]), "max_date": s.loc[i_max, "date"],
        "first": first, "last": last,
        "pct_change": (last / first - 1) * 100 if first else np.nan,
        "n": len(s),
    }


def category_series(df: pd.DataFrame, mode: str = "Index") -> pd.DataFrame:
    """Category trend lines -> [date, category, value].

    mode 'Index': each commodity is rescaled to 100 at its first observation in the
    range, then averaged within the category (avoids mixing PHP/kg and PHP/unit).
    mode 'Average price': plain mean PHP price per category.
    """
    if df.empty:
        return pd.DataFrame(columns=["date", "category", "value"])
    if mode == "Average price":
        out = df.groupby(["date", "category"], as_index=False)["price_php"].mean()
        return out.rename(columns={"price_php": "value"})
    m = df.groupby(["date", "category", "commodity"], as_index=False)["price_php"].mean()
    m = m.sort_values("date")
    m["value"] = m["price_php"] / m.groupby("commodity")["price_php"].transform("first") * 100
    return m.groupby(["date", "category"], as_index=False)["value"].mean()


# --------------------------------------------------------------------------- #
# Pandemic-period comparison
# --------------------------------------------------------------------------- #
def assign_period(dates) -> pd.Series:
    d = pd.to_datetime(pd.Series(dates))
    conds = [(d >= s) & (d <= e) for s, e in PERIODS.values()]
    return pd.Series(np.select(conds, PERIOD_ORDER, default=""), index=d.index).replace("", np.nan)


def period_availability(df: pd.DataFrame) -> dict:
    """Observation count per period."""
    p = assign_period(df["date"]) if len(df) else pd.Series(dtype=object)
    counts = p.value_counts()
    return {k: int(counts.get(k, 0)) for k in PERIOD_ORDER}


def period_summary(df: pd.DataFrame, periods=None) -> pd.DataFrame:
    """Average price and observation count per period -> [period, avg_price, n_obs]."""
    periods = periods or PERIOD_ORDER
    d = df.assign(period=assign_period(df["date"])) if len(df) else df.assign(period=[])
    g = d.dropna(subset=["period"]).groupby("period")["price_php"].agg(avg_price="mean", n_obs="size")
    out = g.reindex(periods).rename_axis("period").reset_index()
    out["n_obs"] = out["n_obs"].fillna(0).astype(int)
    return out


COMPARISONS = ["Pre-Pandemic → Pandemic", "Pandemic → Post-Pandemic", "Pre-Pandemic → Post-Pandemic"]


def period_changes(category=None, commodity=None, region=None) -> pd.DataFrame:
    """Study's matched-series % change between periods -> [comparison, pct_change, series].

    Median % change across commodity-market series observed in both periods (Step 10),
    optionally limited to a category, commodity or region. Comparisons with no matched series
    are skipped (the Pre-Pandemic comparisons rest on only 3 markets).
    """
    m = load_matched_changes()
    for col, val in (("category", category), ("commodity", commodity), ("region", region)):
        if val is not None:
            m = m[m[col] == val]
    g = m.groupby("comparison")["pct_chg"].agg(pct_change="median", series="size")
    g = g.reindex(COMPARISONS).dropna().reset_index()
    return g[["comparison", "pct_change", "series"]]


def regional_period_summary(df: pd.DataFrame, periods=None) -> pd.DataFrame:
    """Average price by region and period -> [region, period, avg_price]."""
    periods = periods or PERIOD_ORDER
    if df.empty:
        return pd.DataFrame(columns=["region", "period", "avg_price"])
    d = df.assign(period=assign_period(df["date"])).dropna(subset=["period"])
    d = d[d["period"].isin(periods)]
    out = d.groupby(["region", "period"], as_index=False)["price_php"].mean()
    return out.rename(columns={"price_php": "avg_price"})


# --------------------------------------------------------------------------- #
# Forecasting - the study's hold-out forecasts (Step 12)
# --------------------------------------------------------------------------- #
_MODEL_COL = {"Seasonal Naive": "snaive", "Naive": "naive", "SARIMA": "sarima"}


def restrict_to_forecast_series(df: pd.DataFrame, period=None) -> pd.DataFrame:
    """Keep only commodity-market series the study evaluated (eligible series with forecasts).

    period: one period label, or None for any of the three windows."""
    h = load_holdout()
    if period is not None:
        h = h[h["period"] == period]
    keys = h[["market_id", "commodity_id"]].drop_duplicates()
    return df.merge(keys, on=["market_id", "commodity_id"], how="inner")


def _holdout(commodity, market, period) -> pd.DataFrame:
    h = load_holdout()
    h = h[(h["commodity"] == commodity) & (h["market"] == market) & (h["period"] == period)]
    return h.sort_values("date")


def forecast_origin(commodity, market, period=FORECAST_PERIOD):
    """Last month of data the models were fitted on (month before the first forecast), or None."""
    h = _holdout(commodity, market, period)
    return None if h.empty else h["date"].iloc[0] - pd.DateOffset(months=1)


def get_forecast(series, commodity, market, model, horizon) -> pd.DataFrame:
    """Study forecast (Seasonal Naive, Naive or SARIMA) for the first `horizon` months of the latest hold-out window.

    Columns: date, forecast, lower, upper, actual, segment. The study produced point forecasts
    only, so lower/upper are NaN. `actual` is the price later observed for that month."""
    h = _holdout(commodity, market, FORECAST_PERIOD)
    h = h[h["h"] <= horizon]
    out = pd.DataFrame({"date": h["date"], "forecast": h[_MODEL_COL[model]], "lower": np.nan,
                        "upper": np.nan, "actual": h["actual"], "segment": "Forecast"})
    return out.reset_index(drop=True)


def get_backtest(commodity, market, period) -> pd.DataFrame:
    """Hold-out months of one evaluation window -> [date, actual, <model>...] (PHP)."""
    h = _holdout(commodity, market, period)
    out = pd.DataFrame({"date": h["date"], "actual": h["actual"]})
    for name, col in _MODEL_COL.items():
        out[name] = h[col]
    return out.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Forecast evaluation - the study's per-series metrics (Step 12)
# --------------------------------------------------------------------------- #
def get_model_metrics(df: pd.DataFrame, commodity: str, market: str) -> pd.DataFrame:
    """MAE/RMSE/MAPE per period and model -> [period, model, mae, rmse, mape, n_obs].

    Values are the study's per-series results (12_series_metrics.csv); MAPE is in %."""
    m = load_model_metrics()
    m = m[(m["commodity"] == commodity) & (m["market"] == market) & m["model"].isin(_MODEL_COL)]
    m = m.assign(_o=m["model"].map({k: i for i, k in enumerate(_MODEL_COL)})).sort_values(["period", "_o"])
    return m[["period", "model", "mae", "rmse", "mape", "n_obs"]].reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Forward forecasts - Jul 2026 to Jun 2027 (Step 16, indicative)
# --------------------------------------------------------------------------- #
_FUTURE_BAND = {"Naive": "naive", "SARIMA": "sarima"}   # Seasonal Naive has no interval in the study


def restrict_to_future_series(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only commodity-market series that have a forward forecast."""
    keys = load_future()[["market_id", "commodity_id"]].drop_duplicates()
    return df.merge(keys, on=["market_id", "commodity_id"], how="inner")


def _future(commodity, market) -> pd.DataFrame:
    f = load_future()
    return f[(f["commodity"] == commodity) & (f["market"] == market)].sort_values("date")


def future_origin(commodity, market):
    """Last month of data the forward forecasts were fitted on, or None."""
    f = _future(commodity, market)
    return None if f.empty else f["forecast_origin"].iloc[0]


def has_interval(model: str) -> bool:
    return model in _FUTURE_BAND


def get_future_forecast(commodity, market, model, horizon, level="80%") -> pd.DataFrame:
    """Forward forecast for the first `horizon` months after Jun 2026.

    Columns: date, forecast, lower, upper, actual, segment. Intervals are the study's empirical
    ('_emp') intervals, which it recommends over the model-based ones; Seasonal Naive has none (NaN).
    `actual` is NaN: these months had not been observed when the data pack was built."""
    f = _future(commodity, market)
    f = f[f["h"] <= horizon]
    out = pd.DataFrame({"date": f["date"], "forecast": f[_MODEL_COL[model]], "lower": np.nan,
                        "upper": np.nan, "actual": np.nan, "segment": "Forecast"})
    if has_interval(model):
        pre, lv = _FUTURE_BAND[model], level.rstrip("%")
        out["lower"], out["upper"] = f[f"{pre}_lo{lv}_emp"].to_numpy(), f[f"{pre}_hi{lv}_emp"].to_numpy()
    return out.reset_index(drop=True)


def future_details(commodity, market) -> dict:
    """Series-level facts for the forward forecast: last price, SARIMA spec, hold-out MAPE per model."""
    f = _future(commodity, market)
    if f.empty:
        return {}
    r = f.iloc[0]
    return {"last_price": float(r["last_price"]), "sarima_spec": r["sarima_spec"],
            "origin": r["forecast_origin"],
            "holdout_mape": {"Seasonal Naive": r["holdout_mape_snaive"], "Naive": r["holdout_mape_naive"],
                             "SARIMA": r["holdout_mape_sarima"]}}


def future_outlook(model: str, horizon: int, category=None, region=None) -> pd.DataFrame:
    """Median forecast % change vs. the last observed price, per commodity, at month `horizon`.

    -> [commodity, category, change_pct, series]. Computed from the study's forward forecasts."""
    f = load_future()
    f = f[f["h"] == horizon]
    if category is not None:
        f = f[f["category"] == category]
    if region is not None:
        f = f[f["region"] == region]
    f = f.assign(change_pct=(f[_MODEL_COL[model]] / f["last_price"] - 1) * 100)
    g = f.groupby(["commodity", "category"], as_index=False).agg(change_pct=("change_pct", "median"),
                                                                 series=("change_pct", "size"))
    return g.sort_values("change_pct").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Study-wide forecast accuracy (Step 12) - pooled over all evaluated series
# --------------------------------------------------------------------------- #
def accuracy_table(metric="pooled_MAPE", dimension="overall", group=None, window=None) -> pd.DataFrame:
    """Study accuracy values -> [window, model, group, value, n_series, n_obs]."""
    fs = load_forecast_summary()
    a = fs[(fs["record_type"] == "accuracy") & (fs["metric"] == metric) & (fs["dimension"] == dimension)]
    if group is not None:
        a = a[a["group"] == group]
    if window is not None:
        a = a[a["window"] == window]
    return a[["window", "model", "group", "value", "n_series", "n_obs"]].reset_index(drop=True)


def decision_table(dimension="overall") -> pd.DataFrame:
    """Model-vs-model verdicts -> [window, model, vs, group, metric, ratio, ci_low, ci_high, verdict, ...].

    `ratio` is the geometric-mean error ratio of `model` to `vs` across series (< 1 favours `model`);
    the verdict uses a bootstrap CI over markets (Step 12)."""
    fs = load_forecast_summary()
    d = fs[(fs["record_type"] == "decision") & (fs["dimension"] == dimension)]
    d = d.rename(columns={"value": "ratio"})
    return d[["window", "model", "vs", "group", "metric", "ratio", "ci_low", "ci_high", "verdict",
              "n_series", "ties_pct"]].reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Period comparison with intervals (Step 10 / 10B / 13)
# --------------------------------------------------------------------------- #
def period_summary_rows(comparison: str, dimension: str) -> pd.DataFrame:
    """Study rows for one comparison and dimension (overall, category, region, commodity, market,
    category_region): median % change, share rising, calendar-balanced median, 95% CI, reliability."""
    ps = load_period_summary()
    return ps[(ps["comparison"] == comparison) & (ps["dimension"] == dimension)].reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Monitoring (latest month, alerts)
# --------------------------------------------------------------------------- #
ALERT_ORDER = ["alert", "watch", "normal"]


def monitoring_table(category=None, region=None, commodity=None, levels=None) -> pd.DataFrame:
    m = load_monitoring()
    for col, val in (("category", category), ("region", region), ("commodity", commodity)):
        if val is not None:
            m = m[m[col] == val]
    if levels is not None:
        m = m[m["alert_level"].isin(levels)]
    return m.reset_index(drop=True)


def monitoring_counts(m: pd.DataFrame) -> dict:
    c = m["alert_level"].value_counts()
    out = {k: int(c.get(k, 0)) for k in ALERT_ORDER}
    out["series"] = len(m)
    out["outside_interval"] = int(m["model_alert_sarima"].isin(["below 95% interval", "above 95% interval"]).sum())
    out["with_forecast"] = int((m["model_alert_sarima"] != "no forecast").sum())
    return out
