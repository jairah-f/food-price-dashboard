"""About - research information. Study text comes from the study's dash_about table; coverage is computed from the data."""
import html

import pandas as pd
import streamlit as st

from utils import formatting as fmt
from utils.config import (DATA_DIR, EXCLUDED_LABEL, PERIOD_RANGE_LABELS, RAW_RECORDS, WHOLESALE_EXCLUDED)
from utils.data_loader import load_about, load_commodities, load_food_price_data, load_markets

about = load_about()
df = load_food_price_data()
fmt.page_header("About the Research", "Study information and dataset rules", demo=False,
                pills=[f"Data through {pd.Timestamp(about.get('data_through', df['date'].max())):%b %Y}"])


def table(rows):
    return ('<table class="meta-table">' + "".join(
        f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>" for k, v in rows) + "</table>")


with fmt.card("Research title", demo=False):
    st.markdown(f'<div class="about"><p>{html.escape(about.get("study_title", ""))}</p></div>', unsafe_allow_html=True)

left, right = st.columns(2)
with left, fmt.card("Objectives", demo=False):
    st.markdown("""<div class="about"><ol>
<li>Analyze historical food-price trends across commodities, food categories, markets, and regions.</li>
<li>Compare retail price levels and percentage changes across the three periods.</li>
<li>Apply Seasonal Naive and SARIMA models (with a Naive benchmark) and evaluate them with MAE, RMSE, and MAPE.</li>
<li>Provide an interactive dashboard for price monitoring.</li></ol></div>""", unsafe_allow_html=True)
with right, fmt.card("Study periods", demo=False):
    rows = list(PERIOD_RANGE_LABELS.items()) + [("Excluded", EXCLUDED_LABEL)]
    st.markdown(table(rows), unsafe_allow_html=True)
    st.caption(about.get("excluded_months", ""))

left, right = st.columns(2)
with left, fmt.card("Dataset", "World Food Programme (WFP) Food Prices – Philippines", demo=False):
    com, mk = load_commodities(), load_markets()
    in_excluded = int(com["observations"].sum()) - len(df)
    rows = [
        ("Raw records", f"{RAW_RECORDS:,}"),
        ("Wholesale records (not analysed)", f"{WHOLESALE_EXCLUDED:,}"),
        ("Retail records in months studied", f"{len(df):,}"),
        ("Retail records in excluded months", f"{in_excluded:,}"),
        ("Commodities with retail prices", f"{df['commodity'].nunique()}"),
        ("Food categories", f"{df['category'].nunique()}"),
        ("Markets", f"{df['market'].nunique()}"),
        ("Provinces", f"{df['province'].nunique()}"),
        ("Regions", f"{df['region'].nunique()}"),
        ("Coverage", f"{fmt.month_label(df['date'].min())} – {fmt.month_label(df['date'].max())}"),
        ("Price type", "Retail only"),
        ("Currency and unit", about.get("price_unit", "")),
    ]
    st.markdown(table(rows), unsafe_allow_html=True)
    st.caption(f"Source: {about.get('data_source', '')}. Retail counts are computed from the loaded data; raw and "
               f"wholesale counts are from the study's validation step. Data pack generated {about.get('generated_on', '')}.")
with right, fmt.card("Metrics", demo=False):
    st.markdown("""<div class="about"><ul>
<li><b>MAE</b> – average size of the forecast error, in pesos.</li>
<li><b>RMSE</b> – like MAE, but large misses count more.</li>
<li><b>MAPE</b> – average error as a percentage of the actual price.</li></ul>
<p>Lower values mean better accuracy.</p></div>""", unsafe_allow_html=True)
    fmt.note(f"<b>Study finding.</b> {html.escape(about.get('forecast_finding', ''))}.")

left, right = st.columns(2)
with left, fmt.card("Forecasting", "Models, test windows and forward forecasts", demo=False):
    st.markdown(table([
        ("Models", about.get("forecast_models", "")),
        ("Test windows", about.get("forecast_windows", "")),
        ("Forward forecasts", about.get("forward_forecasts", "")),
        ("Intervals", about.get("interval_method", ""))]), unsafe_allow_html=True)
with right, fmt.card("Comparisons and monitoring", "How periods are compared and alerts are raised", demo=False):
    st.markdown(table([
        ("Series", about.get("series_definition", "")),
        ("Matched series", about.get("matched_series_rule", "")),
        ("Reliable result", about.get("reliable_rule", "")),
        ("Price index", about.get("chain_index", "")),
        ("Large changes", about.get("flag_rule", "")),
        ("Alerts", about.get("monitoring_rules", "")),
        ("Reading the differences", about.get("causal_caveat", ""))]), unsafe_allow_html=True)

with fmt.card("Market coverage", "How the set of reporting markets changed", demo=False):
    st.markdown(table([("Before 2020", about.get("pre_pandemic_coverage", "")),
                       ("From May 2020", about.get("market_coverage_changes", ""))]), unsafe_allow_html=True)

manifest = DATA_DIR / "data_manifest.csv"
if manifest.exists():
    with st.expander("Data files used by this dashboard"):
        m = pd.read_csv(manifest)
        m.columns = ["File", "Study table", "Rows", "Study source", "Built on"]
        st.dataframe(m.style.format({"Rows": "{:,.0f}"}), hide_index=True, **fmt.STRETCH)
        st.caption("Rebuild with `python scripts/build_data.py <path to ph_food_forecasting-main>`.")
