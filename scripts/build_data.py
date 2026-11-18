"""Build the data files the dashboard reads (data/*.csv.gz and data/*.csv).

Source: the study repository (ph_food_forecasting-main), Step 16 data pack
(outputs/tables/dash_*.csv, described by 15_dashboard_data_contract.csv and verified by
16_datapack_manifest.csv). Nothing is re-estimated here. Values are copied from the study;
only names are standardised: period / model / comparison labels are mapped to the dashboard's
labels, 'YYYY-MM' months become first-of-month dates, and admin1/admin2 become region/province.

Usage:  python scripts/build_data.py /path/to/ph_food_forecasting-main
The script stops with an error if a table's row count differs from the study's manifest.
"""
import sys
from datetime import date
from pathlib import Path

import pandas as pd

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "ph_food_forecasting-main")
OUT = Path(__file__).resolve().parents[1] / "data"
TAB = SRC / "outputs" / "tables"

PERIOD = {"Pre-pandemic": "Pre-Pandemic", "Pandemic": "Pandemic", "Post-pandemic": "Post-Pandemic"}
MODEL = {"snaive": "Seasonal Naive", "naive": "Naive", "sarima": "SARIMA"}
COMPARISON = {"pre_pan": "Pre-Pandemic → Pandemic", "pan_post": "Pandemic → Post-Pandemic",
              "pre_post": "Pre-Pandemic → Post-Pandemic"}


def read(name):
    for ext in (".csv.gz", ".csv"):
        if (TAB / f"{name}{ext}").exists():
            return pd.read_csv(TAB / f"{name}{ext}")
    sys.exit(f"Missing study table: {TAB / name}.csv[.gz]")


def month(s):  # 'YYYY-MM' or 'YYYY-MM-DD' -> first day of the month
    return pd.to_datetime(s).dt.to_period("M").dt.to_timestamp().dt.strftime("%Y-%m-%d")


manifest = pd.read_csv(TAB / "16_datapack_manifest.csv").set_index("table")
written = []


def save(df, fname, table, source):
    expected = int(manifest.loc[table, "rows"])
    if len(df) != expected:
        sys.exit(f"{table}: {len(df)} rows built but the study manifest lists {expected}")
    df.to_csv(OUT / fname, index=False)
    written.append({"file": fname, "study_table": table, "rows": len(df), "source": source})


# 1) Prices (Q1, Q4): 207,601 retail rows, Jan 2016 - Jun 2026, excluded months absent
p = read("dash_prices")
prices = pd.DataFrame({
    "date": month(p["date"]), "commodity": p["commodity"], "category": p["category"],
    "region": p["admin1"], "province": p["admin2"], "market": p["market"],
    "market_id": p["market_id"], "commodity_id": p["commodity_id"], "unit": p["unit"],
    "price_php": p["price"], "period": p["period"].map(PERIOD), "segment": p["segment"],
    "flag_jump": p["flag_jump"]})
assert prices["period"].notna().all()
save(prices, "prices.csv.gz", "dash_prices", "retail_clean_flagged.csv")

# 2) Hold-out forecasts (Q3): actual + Seasonal Naive / Naive / SARIMA for the three test windows (PHP)
h = read("dash_forecast_holdout")
hold = pd.DataFrame({
    "period": h["window"].map(PERIOD), "market_id": h["market_id"], "commodity_id": h["commodity_id"],
    "commodity": h["commodity"], "category": h["category"], "market": h["market"], "region": h["admin1"],
    "date": month(h["ym"]), "h": h["h"], "actual": h["price"],
    "snaive": h["snaive_php"], "naive": h["naive_php"], "sarima": h["sarima_php"]})
save(hold, "holdout.csv.gz", "dash_forecast_holdout", "forecast_results_paired.csv")

# 3) Per-series accuracy (Q3): MAE / RMSE / MAPE(%) per test window and model
m = read("dash_forecast_metrics")
mk = read("dash_markets")[["market_id", "market"]]
met = pd.DataFrame({
    "period": m["window"].map(PERIOD), "market_id": m["market_id"], "commodity_id": m["commodity_id"],
    "commodity": m["commodity"], "category": m["category"], "region": m["admin1"],
    "model": m["model"].map(MODEL), "mae": m["MAE"], "rmse": m["RMSE"], "mape": m["MAPE"],
    "n_obs": m["n_test"]}).merge(mk, on="market_id", how="left")
assert met["market"].notna().all() and met["model"].notna().all()
save(met, "model_metrics.csv.gz", "dash_forecast_metrics", "12_series_metrics.csv")

# 4) Matched-series period changes (Q2)
s = read("dash_period_series")
mat = pd.DataFrame({
    "comparison": s["comparison"].map(COMPARISON), "market_id": s["market_id"],
    "commodity_id": s["commodity_id"], "commodity": s["commodity"], "category": s["category"],
    "market": s["market"], "region": s["admin1"], "p1": s["p1"], "p2": s["p2"],
    "pct_chg": s["pct_chg"], "pct_chg_calendar_balanced": s["pct_chg_calendar_balanced"]})
save(mat, "matched_changes.csv.gz", "dash_period_series", "10_matched_series_*.csv, 13_calendar_balanced_*.csv")

# 5) Period summary with confidence intervals and reliability flags (Q2)
ps = read("dash_period_summary")
ps["comparison"] = ps["comparison"].map(COMPARISON)
save(ps, "period_summary.csv", "dash_period_summary", "10_pan_post_by_*.csv, 10B_category_region_cells.csv")

# 6) Forecast accuracy summary + model decisions (Q3)
fs = read("dash_forecast_summary")
fs["window"] = fs["window"].map(PERIOD)
fs["model"] = fs["model"].map(MODEL)
fs["vs"] = fs["vs"].map(MODEL)
save(fs, "forecast_summary.csv", "dash_forecast_summary", "12_accuracy_*.csv, 12_sarima_vs_*.csv, 12B_*.csv")

# 7) Forward forecasts, Jul 2026 - Jun 2027 (Q3, Q4); flagged indicative by the study
f = read("dash_forecast_future")
f["forecast_origin"] = month(f["forecast_origin"])
f["ym"] = month(f["ym"])
f = f.rename(columns={"ym": "date", "admin1": "region", "naive_php": "naive", "snaive_php": "snaive",
                      "sarima_php": "sarima"})
save(f, "forecast_future.csv.gz", "dash_forecast_future", "16_datapack_preparation.py (SARIMA refit through Jun 2026)")

# 8) Monitoring: latest month per series, alerts, last forecast vs outcome (Q4)
mo = read("dash_monitoring")
mo["latest_month"] = month(mo["latest_month"])
mo = mo.rename(columns={"admin1": "region"})
save(mo, "monitoring.csv.gz", "dash_monitoring", "retail_clean_flagged.csv")

# 9) Reference tables
mkt = read("dash_markets")
for c in ("first_month", "last_month"):
    mkt[c] = month(mkt[c])
mkt = mkt.rename(columns={"admin1": "region", "admin2": "province"})
save(mkt, "markets.csv", "dash_markets", "09B_market_profile.csv")

com = read("dash_commodities")
for c in ("first_month", "last_month"):
    com[c] = month(com[c])
save(com, "commodities.csv", "dash_commodities", "09B_commodity_coverage.csv")

ci = read("dash_chain_index")
ci["month"] = month(ci["month"])
save(ci, "chain_index.csv", "dash_chain_index", "09_chain_index_category_A.csv, 09_chain_index_B.csv")

ss = read("dash_series_stats").rename(columns={"admin1": "region"})
save(ss, "series_stats.csv", "dash_series_stats", "09_series_stats.csv")

about = read("dash_about")
save(about, "about.csv", "dash_about", "study_config.py, Steps 2, 3, 5, 10, 12")

# 10) Interval calibration (Step 16 checks; not part of the manifest)
cal = read("16_interval_calibration_check")
cal["model"] = cal["model"].map(MODEL)
cal["source"] = "Post-pandemic hold-out, empirical intervals scaled by series volatility"
cal.to_csv(OUT / "interval_coverage.csv", index=False)
written.append({"file": "interval_coverage.csv", "study_table": "16_interval_calibration_check",
                "rows": len(cal), "source": "16_interval_calibration_check.csv"})

pd.DataFrame(written).assign(built_on=date.today().isoformat()).to_csv(OUT / "data_manifest.csv", index=False)
for w in written:
    f_ = OUT / w["file"]
    print(f"{w['file']:<26}{w['rows']:>9,} rows  {f_.stat().st_size / 1e6:6.2f} MB   <- {w['study_table']}")
