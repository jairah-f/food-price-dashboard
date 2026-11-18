"""Price Trends - explore historical retail prices."""
import streamlit as st

from utils import analysis, filters, formatting as fmt, ui_analytics as ui, visualizations as viz
from utils.data_loader import load_about, load_chain_index, load_series_stats

fmt.page_header("Price Trends", "Explore historical retail prices by commodity and location")
df = fmt.get_data()
if df.empty:
    fmt.empty_state("No data loaded", "Run scripts/build_data.py to build the data folder.")
    st.stop()

with fmt.card():
    cols = st.columns(5)
    sel = filters.location_filters(df, slots=cols)
    c1, c2 = st.columns([3, 1])
    start, end = filters.date_range_filter(df, container=c1)
    ma_choice = c2.selectbox("Moving average", ["Off", "3-month", "6-month", "12-month"])

filtered = filters.apply_filters(df, **sel, start=start, end=end)
series = analysis.monthly_series(filtered)
if len(series) < 2:
    fmt.empty_state("No observations for this selection", "Try another market or a wider date range.")
    st.stop()

summary = analysis.historical_summary(series)
unit = filtered["unit"].mode().iat[0]
market_label = sel["market"] or "All markets (average)"
st.write("")
fmt.kpi_cards([
    ("Average price", fmt.peso(summary["avg"]), f"per {unit.lower()}", "", "peso"),
    ("Minimum", fmt.peso(summary["min"]), fmt.month_label(summary["min_date"]), "", "down"),
    ("Maximum", fmt.peso(summary["max"]), fmt.month_label(summary["max_date"]), "", "trend"),
    ("Change over range", fmt.pct(summary["pct_change"]),
     f'{fmt.month_label(series["date"].min())} – {fmt.month_label(series["date"].max())}',
     fmt.trend_tone(summary["pct_change"]), "activity"),
])
st.write("")

ma, ma_label = None, ""
if ma_choice != "Off":
    window = int(ma_choice.split("-")[0])
    ma, ma_label = ui.moving_average(series, window), f"{ma_choice} moving average"

with fmt.card(sel["commodity"], f"{market_label} · {summary['n']:,} monthly observations"):
    fmt.show_chart(viz.price_trend_fig(series, sel["commodity"], market_label, unit, ma, ma_label),
                   key="hist_main")

with fmt.card("Trends by food category", "Uses the region, province, market and date filters above"):
    c1, c2 = st.columns([3, 1])
    all_cats = sorted(df["category"].unique())
    cats = c1.multiselect("Categories", all_cats, default=all_cats)
    mode = c2.radio("Measure", ["Index", "Average price"], horizontal=True)
    cat_df = filters.apply_filters(df, region=sel["region"], province=sel["province"],
                                   market=sel["market"], start=start, end=end)
    cat_df = cat_df[cat_df["category"].isin(cats)]
    fmt.show_chart(viz.category_trend_fig(analysis.category_series(cat_df, mode), mode), key="hist_cat")


# --------------------------------------------------------------------------- #
# Chain-linked price index (study Step 9): same series month to month, so changing market coverage
# does not distort the index.
# --------------------------------------------------------------------------- #
with fmt.card("Price index", "Chain-linked index: average month-to-month change of the same series, cumulated"):
    ci_all = load_chain_index()
    c1, c2 = st.columns([2, 3])
    level = c1.radio("Group by", ["Food category", "Region"], horizontal=True, key="hist_ci_level")
    if level == "Food category":
        seg_label = c2.radio("Period", ["May 2020 – Jun 2026 (May 2020 = 100)", "Jan 2016 – May 2019 (Jan 2016 = 100)"],
                             horizontal=True, key="hist_ci_seg")
        segment = "B" if seg_label.startswith("May") else "A"
    else:
        segment = "B"
        c2.caption("Regional indexes start in May 2020, when about 80 markets began reporting.")
    ci = ci_all[(ci_all["level"] == level.split()[-1].lower()) & (ci_all["segment"] == segment)]
    base = "May 2020 = 100" if segment == "B" else "Jan 2016 = 100"
    fmt.show_chart(viz.chain_index_fig(ci, base), key="hist_chain")
    last = ci[ci["month"] == ci["month"].max()].sort_values("index_value", ascending=False)
    if not last.empty:
        top, low = last.iloc[0], last.iloc[-1]
        st.caption(f"At {fmt.month_label(ci['month'].max())}: highest **{top['group']}** ({top['index_value']:.1f}), "
                   f"lowest **{low['group']}** ({low['index_value']:.1f}). The 2016–2019 and post-May 2020 "
                   "indexes use different markets and cannot be joined.")

# --------------------------------------------------------------------------- #
# Trend and volatility per market (study Step 9): series with at least 24 months
# --------------------------------------------------------------------------- #
stats = load_series_stats()
stats = stats[stats["commodity"] == sel["commodity"]]
if sel["region"]:
    stats = stats[stats["region"] == sel["region"]]
if sel["market"]:
    stats = stats[stats["market"] == sel["market"]]
with fmt.card("Trend and volatility", f"{sel['commodity']} · each point is one market with at least 24 months of prices"):
    if stats.empty:
        st.caption("No market with 24 or more months of prices for this selection.")
    else:
        fmt.kpi_cards([
            ("Median trend", fmt.pct(stats["trend_pct_yr"].median()), "per year", fmt.trend_tone(stats["trend_pct_yr"].median()), "trend"),
            ("Median volatility", fmt.pct(stats["vol_pct"].median(), 1, signed=False), "typical monthly swing", "", "activity"),
            ("Markets", f"{len(stats):,}", "with a trend estimate", "", "pin"),
        ])
        st.write("")
        fmt.show_chart(viz.trend_vol_fig(stats, sel["commodity"]), key="hist_trendvol")
        with st.expander("Show table"):
            show = stats[["market", "region", "n_obs", "trend_pct_yr", "vol_pct"]].sort_values("trend_pct_yr", ascending=False)
            show.columns = ["Market", "Region", "Months", "Trend (% per year)", "Volatility (%)"]
            st.dataframe(show.style.format({"Trend (% per year)": "{:+.1f}", "Volatility (%)": "{:.1f}"}),
                         hide_index=True, **fmt.STRETCH)
