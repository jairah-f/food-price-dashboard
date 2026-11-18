"""Period Analysis - Pre-Pandemic vs. Pandemic vs. Post-Pandemic."""
import pandas as pd
import streamlit as st

from utils import analysis, filters, formatting as fmt, ui_analytics as ui, visualizations as viz
from utils.config import PERIOD_ORDER, PERIOD_RANGE_LABELS
from utils.data_loader import load_about

fmt.page_header("Period Analysis", "How retail prices changed across the three study periods")
df = fmt.get_data()
if df.empty:
    fmt.empty_state("No data loaded", "Run scripts/build_data.py to build the data folder.")
    st.stop()

_about = load_about()
fmt.note(f"<b>Read with care.</b> {_about.get('pre_pandemic_coverage', '')}. "
         f"{_about.get('causal_caveat', '')}.", warn=True)

with fmt.card():
    cols = st.columns([2, 2, 2, 3])
    sel = filters.location_filters(df, show_province=False, show_market=False, slots=cols[:3])
    periods = cols[3].multiselect("Periods", PERIOD_ORDER, default=PERIOD_ORDER)
if not periods:
    fmt.empty_state("Select at least one period")
    st.stop()

data = filters.apply_filters(df, category=sel["category"], commodity=sel["commodity"], region=sel["region"])
if data.empty:
    fmt.empty_state("No observations for this selection", "Try another commodity or region.")
    st.stop()

# Availability check (placeholder: counts rows per period, not per commodity-market series).
avail = analysis.period_availability(data)
missing = [p for p in periods if avail[p] == 0]
if missing:
    st.info("No observations in: " + ", ".join(missing))

summary = analysis.period_summary(data, periods)
changes = analysis.period_changes(sel["category"], sel["commodity"], sel["region"])
st.write("")
fmt.kpi_cards([(r.period, fmt.peso(r.avg_price), f"{PERIOD_RANGE_LABELS[r.period]} · {r.n_obs:,} obs",
                "", "calendar") for r in summary.itertuples()])
st.write("")

c1, c2 = st.columns(2)
with c1, fmt.card("Average retail price", "Mean price in each period"):
    fmt.show_chart(viz.period_avg_bar(summary), key="pc_avg")
with c2, fmt.card("Change between periods", "Median % change across matched market series (study method)"):
    fmt.show_chart(viz.period_change_bar(changes), key="pc_chg")

with fmt.card("Price trend by period", f'{sel["commodity"]} · {sel["region"] or "All regions"}'):
    fmt.show_chart(viz.trend_shading_fig(analysis.monthly_series(data), periods), key="pc_trend")

with fmt.card("Commodity comparison", "Median % change across matched market series for every commodity (all regions)"):
    table = ui.commodity_period_table(filters.apply_filters(df, category=sel["category"]))
    fmt.show_chart(viz.commodity_change_fig(table), key="pc_commodity")
    with st.expander("Show table"):
        if table.empty:
            st.caption("No data.")
        else:
            show = table.rename(columns={"commodity": "Commodity", "pre_to_pandemic": "Pre → Pandemic",
                                         "pandemic_to_post": "Pandemic → Post"})
            st.dataframe(show.style.format({**{p: "₱{:,.2f}" for p in PERIOD_ORDER},
                                            "Pre → Pandemic": "{:+.1f}%", "Pandemic → Post": "{:+.1f}%"},
                                           na_rep="—"), hide_index=True, **fmt.STRETCH)

with fmt.card("Regional comparison", f'{sel["commodity"]} · average price by region and period'):
    regional = filters.apply_filters(df, category=sel["category"], commodity=sel["commodity"])
    fmt.show_chart(viz.regional_comparison_fig(analysis.regional_period_summary(regional, periods)),
                   key="pc_region")


# --------------------------------------------------------------------------- #
# Study results with confidence intervals (Step 10 / 10B / 13) - all series, independent of the filters above
# --------------------------------------------------------------------------- #
st.markdown('<div class="section-break">Study results with confidence intervals</div>', unsafe_allow_html=True)
with fmt.card("Median % change between periods",
              "Matched commodity-market series · 95% intervals resample whole markets · all regions and commodities"):
    c1, c2 = st.columns([2, 3])
    comparison = c1.selectbox("Comparison", analysis.COMPARISONS, index=1, key="pc_cmp")
    dims = {"Food category": "category", "Region": "region", "Commodity": "commodity"}
    dim_label = c2.radio("Group by", list(dims), horizontal=True, key="pc_dim")
    overall = analysis.period_summary_rows(comparison, "overall")
    if not overall.empty:
        o = overall.iloc[0]
        fmt.kpi_cards([
            ("Median change", fmt.pct(o["median_pct"]), "across all matched series", fmt.trend_tone(o["median_pct"]),
             "trend"),
            ("95% interval", f"{o['ci_low']:.1f}% to {o['ci_high']:.1f}%" if pd.notna(o["ci_low"]) else "Not estimated",
             "bootstrap over markets" if pd.notna(o["ci_low"]) else "only 3 markets", "", "activity"),
            ("Series rising", f"{o['share_rising_pct']:.0f}%", f"{int(o['series']):,} series", "", "layers"),
            ("Calendar-balanced", fmt.pct(o["median_pct_cal_balanced"]), f"{int(o['markets'])} markets", "", "calendar"),
        ])
        st.write("")
    rows = analysis.period_summary_rows(comparison, dims[dim_label])
    if dims[dim_label] == "commodity":
        rows = rows[rows["reliable"].astype(bool)]
        st.caption("Commodities with too few markets or series for a reliable estimate are not shown.")
    fmt.show_chart(viz.period_ci_fig(rows), key="pc_ci")
    if dims[dim_label] != "commodity":
        st.caption("Solid bars are reliable results (at least 3 markets and 5 series). Faded bars have fewer "
                   "and should be read as indicative.")
    with st.expander("Show table"):
        if rows.empty:
            st.caption("No data.")
        else:
            show = rows[["group", "series", "markets", "median_pct", "ci_low", "ci_high", "share_rising_pct",
                         "median_pct_cal_balanced", "reliable"]]
            show.columns = ["Group", "Series", "Markets", "Median %", "CI low", "CI high", "Share rising %",
                            "Calendar-balanced %", "Reliable"]
            st.dataframe(show.style.format({"Median %": "{:+.1f}", "CI low": "{:+.1f}", "CI high": "{:+.1f}",
                                            "Share rising %": "{:.0f}", "Calendar-balanced %": "{:+.1f}"},
                                           na_rep="—"), hide_index=True, **fmt.STRETCH)

with fmt.card("Where prices rose most",
              "Pandemic → Post-Pandemic median % change by food category and region · blank = too few markets or series"):
    fmt.show_chart(viz.category_region_heatmap(analysis.period_summary_rows(
        "Pandemic → Post-Pandemic", "category_region")), key="pc_heat")
