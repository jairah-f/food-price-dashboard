"""Market Watch - latest-month price alerts, last year's forecasts vs. outcome, and market coverage.

All values come from the study's monitoring and market-profile tables (Step 16 data pack):
alert rules are the study's, and nothing is recalculated here except simple counts.
"""
import pandas as pd
import streamlit as st

from utils import analysis, filters, formatting as fmt, visualizations as viz
from utils.data_loader import load_about, load_markets, load_monitoring
from utils.theme import ALERT_COLORS

mon_all = load_monitoring()
latest = mon_all["latest_month"].max()
fmt.page_header("Market Watch", "Latest-month price moves, alerts and how last year's forecasts held up",
                pills=[f"Latest month: {fmt.month_label(latest)}"])
fmt.note(f"<b>How alerts work.</b> {load_about().get('monitoring_rules', '')}.")

with fmt.card():
    c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
    category = c1.selectbox("Food category", [filters.ALL] + sorted(mon_all["category"].unique()), key="mw_cat")
    region = c2.selectbox("Region", [filters.ALL] + sorted(mon_all["region"].unique()), key="mw_region")
    commodity = c3.selectbox("Commodity", [filters.ALL] + sorted(mon_all["commodity"].unique()), key="mw_comm")
    levels = c4.multiselect("Show alert levels", analysis.ALERT_ORDER, default=["alert", "watch"], key="mw_levels")

scope = analysis.monitoring_table(None if category == filters.ALL else category,
                                  None if region == filters.ALL else region,
                                  None if commodity == filters.ALL else commodity)
if scope.empty:
    fmt.empty_state("No monitored series for this selection", "Try another category, region or commodity.")
    st.stop()
n = analysis.monitoring_counts(scope)

st.write("")
fmt.kpi_cards([
    ("Series monitored", f"{n['series']:,}", f"commodity-market series · {fmt.month_label(latest)}", "", "records"),
    ("Alerts", f"{n['alert']:,}", "move beyond the study's alert limit", "up" if n["alert"] else "", "trend"),
    ("Watch", f"{n['watch']:,}", "move beyond 2 typical swings", "", "activity"),
    ("Outside last year's forecast range", f"{n['outside_interval']:,}",
     f"of {n['with_forecast']:,} series with a SARIMA forecast", "", "target"),
])
st.write("")

left, right = st.columns([2, 3])
with left, fmt.card("Alerts by food category", f"{fmt.month_label(latest)} · all alert levels"):
    fmt.legend_row([(ALERT_COLORS[k], k.capitalize()) for k in analysis.ALERT_ORDER])
    fmt.show_chart(viz.alert_by_category_fig(scope), key="mw_cat_chart")
with right, fmt.card("Series to look at", "Largest moves first · latest month vs. the month before and a year earlier"):
    shown = scope[scope["alert_level"].isin(levels)].copy()
    if shown.empty:
        st.caption("No series at the selected alert levels.")
    else:
        shown["_o"] = shown["alert_level"].map({k: i for i, k in enumerate(analysis.ALERT_ORDER)})
        shown = shown.assign(_z=shown["z_score"].abs()).sort_values(["_o", "_z"], ascending=[True, False])
        table = shown[["alert_level", "commodity", "market", "region", "latest_price", "change_vs_prev_month_pct",
                       "change_vs_12m_pct", "z_score", "alert_reason"]]
        table.columns = ["Level", "Commodity", "Market", "Region", "Latest price", "vs. last month %",
                         "vs. 12 months ago %", "Swings (z)", "Reason"]
        table = table.reset_index(drop=True)

        def level_colour(data):
            css = pd.DataFrame("", index=data.index, columns=data.columns)
            css["Level"] = data["Level"].map({"alert": "background-color:#FFE3DC;font-weight:600",
                                              "watch": "background-color:#FBF0D3;font-weight:600"}).fillna("")
            return css

        st.dataframe(table.style.apply(level_colour, axis=None).format(
            {"Latest price": "₱{:,.2f}", "vs. last month %": "{:+.1f}", "vs. 12 months ago %": "{:+.1f}",
             "Swings (z)": "{:+.1f}"}, na_rep="—"), hide_index=True, height=330, **fmt.STRETCH)
        st.caption(f"{len(table):,} series shown. A swing is the series' own typical month-to-month change.")

with fmt.card("Last year's forecasts vs. what happened",
              f"{fmt.month_label(latest)} price against the forecast made 12 months earlier (study's 95% interval)"):
    fc = scope[scope["model_alert_sarima"] != "no forecast"]
    if fc.empty:
        st.caption("No series in this selection had a forecast made 12 months earlier.")
    else:
        rows = []
        for model, tag in (("SARIMA", "sarima"), ("Naive", "naive")):
            c = fc[f"model_alert_{tag}"].value_counts()
            tot = len(fc)
            rows.append({"Model": model, "Series": tot,
                         "Typical miss (median absolute %)": fc[f"prev_error_pct_{tag}"].abs().median(),
                         "Within interval %": c.get("within interval", 0) / tot * 100,
                         "Below interval %": c.get("below 95% interval", 0) / tot * 100,
                         "Above interval %": c.get("above 95% interval", 0) / tot * 100})
        st.dataframe(pd.DataFrame(rows).style.format(
            {"Series": "{:,.0f}", "Typical miss (median absolute %)": "{:.1f}", "Within interval %": "{:.1f}",
             "Below interval %": "{:.1f}", "Above interval %": "{:.1f}"}), hide_index=True, **fmt.STRETCH)
        st.caption("Below the interval = prices came in lower than forecast; above = higher. Seasonal Naive is not "
                   "monitored because the study gives it no interval.")

mk = load_markets()
if region != filters.ALL:
    mk = mk[mk["region"] == region]
with fmt.card("Market coverage", f"{len(mk):,} markets · size shows number of price observations"):
    fmt.show_chart(viz.market_map_fig(mk), key="mw_map")
    st.caption(load_about().get("market_coverage_changes", "") + ". Markets that stopped reporting before 2020 "
               "appear as 'pre-pandemic only'.")
    with st.expander("Show market table"):
        show = mk[["market", "region", "province", "era", "first_month", "last_month", "observations", "commodities",
                   "eligible_series", "median_trend_pct_yr", "median_vol_pct"]].copy()
        show["first_month"] = show["first_month"].dt.strftime("%b %Y")
        show["last_month"] = show["last_month"].dt.strftime("%b %Y")
        show.columns = ["Market", "Region", "Province", "Reporting era", "First month", "Last month", "Observations",
                        "Commodities", "Forecastable series", "Median trend (% per year)", "Median volatility (%)"]
        st.dataframe(show.sort_values("Observations", ascending=False).style.format(
            {"Observations": "{:,.0f}", "Median trend (% per year)": "{:+.1f}", "Median volatility (%)": "{:.1f}"},
            na_rep="—"), hide_index=True, **fmt.STRETCH)
