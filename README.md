# Philippine Retail Food Price Dashboard

Streamlit dashboard for *Forecasting Philippine Food Prices Before, During, and After the COVID-19 Pandemic: A Time-Series Approach* (retail prices, Jan 2016 – Jun 2026).

**Data:** all prices, forecasts, intervals, accuracy results and alerts are the study's actual outputs (see `data/README.md`). Nothing is simulated.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m streamlit run app.py
```

## Pages (sidebar navigation)

1. **Overview** – KPIs from the loaded data, price trend, period overview, price distribution, commodity insights, change since the pandemic (with 95% intervals), latest-month alerts, 12-month outlook
2. **Price Trends** – commodity/location/date filters, avg/min/max/% change, moving average, category trends, chain-linked price index, trend and volatility by market
3. **Forecasting** – *Next 12 months* (Jul 2026 – Jun 2027, Seasonal Naive / Naive / SARIMA, 80% and 95% intervals, outlook across commodities) and *Hold-out test* (Jul 2025 – Jun 2026 forecasts vs. what was observed). Forecasts are indicative.
4. **Period Analysis** – Pre-Pandemic / Pandemic / Post-Pandemic averages, matched-series % change, commodity and regional comparison, study results with confidence intervals, category-by-region heatmap
5. **Model Evaluation** – study-wide pooled accuracy, model-vs-model verdicts, accuracy by forecast distance and category, interval coverage; then per-series actual vs. predicted and MAE / RMSE / MAPE
6. **Market Watch** – latest-month alerts, last year's forecasts vs. outcome, market coverage map
7. **About** – study text, dataset facts (computed), methods and caveats, data files used

Commodity, region, market, model and horizon selections carry over between pages.

## Project layout

```
app.py                  navigation entry point
pages/                  one script per page (UI only)
utils/config.py         file paths, period definitions, palette
utils/data_loader.py    loads the study's data files (data/*.csv[.gz])
scripts/build_data.py   builds data/ from the study's Step 16 data pack
utils/analysis.py       summaries, period comparison, forecasts, accuracy, monitoring
utils/filters.py        apply_filters() and sidebar filter widgets
utils/visualizations.py Plotly figure builders
utils/formatting.py     peso formatting, cards, KPI cards, notes, headers
utils/theme.py          UI colour palette
utils/ui_analytics.py   display-only summaries for the UI (coverage, top movers)
assets/style.css        styling (dark sidebar, cards)
.streamlit/config.toml  theme colours
data/                   study data files (see data/README.md)
```

## Updating the data

Re-run `python scripts/build_data.py <path to ph_food_forecasting-main>` to rebuild `data/`. The script checks every table against the study's manifest.

## Notes

- Prices are nominal PHP, per kg except eggs (per unit). USD is not used.
- 64 commodities, 97 markets, 17 regions, 4 food categories.
- Lower MAE, RMSE and MAPE mean better accuracy. In the study SARIMA beat Seasonal Naive but was no better than plain Naive, so forecasts are indicative only.
- Period differences are descriptive, not estimates of a pandemic effect. Before 2020 only 3 markets report in both the early and later periods.
