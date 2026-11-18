# Data folder

All dashboard data comes from the study repository (`ph_food_forecasting-main`), specifically the Step 16
data pack (`outputs/tables/dash_*.csv`, described by `15_dashboard_data_contract.csv`). The files below are
built by `scripts/build_data.py`. Values are copied unchanged; only names are standardised (period, model and
comparison labels, first-of-month dates, `admin1`/`admin2` renamed `region`/`province`). The build stops if a
table's row count differs from the study's `16_datapack_manifest.csv`.

| File | Study table | Rows | Used by |
|---|---|---|---|
| `prices.csv.gz` | `dash_prices` (from `retail_clean_flagged.csv`) | 207,601 | Overview, Price Trends, Period Analysis, filters |
| `holdout.csv.gz` | `dash_forecast_holdout` | 49,864 | Forecasting (hold-out view), Model Evaluation |
| `forecast_future.csv.gz` | `dash_forecast_future` (Jul 2026 – Jun 2027) | 24,060 | Forecasting (next 12 months), Overview |
| `model_metrics.csv.gz` | `dash_forecast_metrics` | 12,486 | Model Evaluation (per series) |
| `forecast_summary.csv` | `dash_forecast_summary` | 1,413 | Model Evaluation (all series, verdicts) |
| `interval_coverage.csv` | `16_interval_calibration_check` | 16 | Model Evaluation (interval coverage) |
| `matched_changes.csv.gz` | `dash_period_series` | 2,689 | Period Analysis |
| `period_summary.csv` | `dash_period_summary` | 306 | Period Analysis, Overview |
| `monitoring.csv.gz` | `dash_monitoring` | 2,623 | Market Watch, Overview |
| `markets.csv` | `dash_markets` | 97 | Market Watch |
| `commodities.csv` | `dash_commodities` | 64 | About |
| `chain_index.csv` | `dash_chain_index` | 1,718 | Price Trends |
| `series_stats.csv` | `dash_series_stats` | 2,725 | Price Trends |
| `about.csv` | `dash_about` | 23 | About, notes on several pages |
| `data_manifest.csv` | written by the build script | 14 | About (data files list) |

Rebuild after the research outputs change:

    python scripts/build_data.py /path/to/ph_food_forecasting-main
