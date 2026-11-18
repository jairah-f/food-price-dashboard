# Update: synchronised with ph_food_forecasting-main

Data source switched to the study's Step 16 data pack (`outputs/tables/dash_*.csv`), the study's own data contract for the dashboard.

## Data
- `scripts/build_data.py` rewritten: builds `data/` from the data pack and checks every table's row count against `16_datapack_manifest.csv`.
- `data/*.parquet` replaced by gzip CSV (no `pyarrow` needed). New tables: forward forecasts, forecast summary, period summary with CIs, monitoring, markets, commodities, chain index, series stats, interval coverage, about text, manifest.
- Hold-out forecasts now use the study's PHP columns directly instead of exp() of log forecasts.

## New
- Forecasting: *Next 12 months* view (Jul 2026 – Jun 2027) with 80% / 95% empirical intervals, outlook across commodities, series details; hold-out view now also draws observed prices.
- Model Evaluation: study-wide pooled MAPE, model-vs-model verdicts, accuracy by forecast distance and category, interval coverage.
- Period Analysis: median % change with 95% CIs by category / region / commodity, calendar-balanced medians, category-by-region heatmap, caveat note.
- Price Trends: chain-linked price index, trend and volatility by market.
- Market Watch (new page): latest-month alerts, last year's forecasts vs. outcome, market coverage map.
- Overview: change since the pandemic with CIs, latest-month alerts, 12-month outlook.
- About: study text from `dash_about`, dataset facts computed from the data, methods, data-file list.

## Fixed
- Forecasting page said the study produced no forecasts beyond Jun 2026; it now has them.
- About/metric text said no model is assumed better; now reports the study's finding (SARIMA beats Seasonal Naive, no better than Naive; forecasts indicative).
- About page figures were hard-coded; they are now computed from the loaded data.
- Stale "Add the WFP CSV" empty-state messages.
