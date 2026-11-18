"""Forecasting - historical vs. forecasted prices.

Two views, both from the study's outputs:
  * Next 12 months: forward forecasts Jul 2026 - Jun 2027 (SARIMA refit through Jun 2026), with intervals.
  * Hold-out test: the Jul 2025 - Jun 2026 forecasts made from data to Jun 2025, shown against what happened.
"""
import pandas as pd
import streamlit as st

from utils import analysis, filters, formatting as fmt, visualizations as viz
from utils.config import FORECAST_PERIOD, FUTURE_LABEL, HORIZONS, INTERVAL_LEVELS, MODELS
from utils.data_loader import forecasts_are_demo, using_demo_data
from utils.theme import MUTED, NAVY, TEAL

VIEW_FUTURE, VIEW_HOLDOUT = "Next 12 months", "Hold-out test"
demo = using_demo_data() or forecasts_are_demo()
fmt.page_header("Forecasting", "Historical retail prices alongside model forecasts",
                demo=demo, pills=[f"Forecasts {FUTURE_LABEL}", "Indicative only"])
df = fmt.get_data()
if df.empty:
    fmt.empty_state("No data loaded", "Run scripts/build_data.py to build the data folder.")
    st.stop()

with fmt.card():
    view = filters.sticky_select("View", [VIEW_FUTURE, VIEW_HOLDOUT], "sel_fc_view", VIEW_FUTURE,
                                 kind="radio", container=st, horizontal=True)
    cols = st.columns(5)
    # only series the study forecast (eligible series: same 2,005 series in both views)
    base = (analysis.restrict_to_future_series(df) if view == VIEW_FUTURE
            else analysis.restrict_to_forecast_series(df, FORECAST_PERIOD))
    sel = filters.location_filters(base, require_market=True, slots=cols)
    c1, c2, c3 = st.columns([2, 2, 2])
    model = filters.sticky_select("Model", MODELS, "sel_model", MODELS[0], kind="radio",
                                  container=c1, horizontal=True)
    horizon = c2.select_slider("Forecast horizon (months)", HORIZONS,
                               value=st.session_state.get("sel_horizon", 6))
    st.session_state["sel_horizon"] = horizon
    if view == VIEW_FUTURE:
        level = c3.radio("Interval", INTERVAL_LEVELS, horizontal=True, key="sel_level",
                         help="Share of future prices the band is meant to cover (study's empirical intervals).")
        history = st.radio("History shown", ["Since May 2020", "Last 3 years", "All"], horizontal=True,
                           key="sel_history")

if not sel["market"]:
    fmt.empty_state("No market available", "Choose another commodity or region.")
    st.stop()

commodity, market = sel["commodity"], sel["market"]
unit = df.loc[df["commodity"] == commodity, "unit"].mode().iat[0]
all_series = analysis.monthly_series(filters.apply_filters(df, commodity=commodity, market=market))

# --------------------------------------------------------------------------- #
# Next 12 months
# --------------------------------------------------------------------------- #
if view == VIEW_FUTURE:
    origin = analysis.future_origin(commodity, market)
    if origin is None:
        fmt.empty_state("No forward forecast for this series", "Pick a market with a longer price history.")
        st.stop()
    series = all_series[all_series["date"] <= origin]
    shown = series
    if history == "Since May 2020":
        shown = series[series["date"] >= pd.Timestamp("2020-05-01")]
    elif history == "Last 3 years":
        shown = series[series["date"] > origin - pd.DateOffset(years=3)]
    fc = analysis.get_future_forecast(commodity, market, model, horizon, level)
    if fc.empty:
        fmt.empty_state("No forecast available for this selection")
        st.stop()
    info = analysis.future_details(commodity, market)
    latest = float(series["price"].iloc[-1])
    nxt = float(fc["forecast"].iloc[0])
    end_val = float(fc["forecast"].iloc[-1])
    change = (nxt / latest - 1) * 100 if latest else float("nan")
    end_change = (end_val / latest - 1) * 100 if latest else float("nan")
    direction = "Stable" if abs(end_change) < 0.5 else ("Rising" if end_change > 0 else "Falling")
    mape = info["holdout_mape"].get(model)

    st.write("")
    fmt.kpi_cards([
        ("Latest observed price", fmt.peso(latest), f'{fmt.month_label(series["date"].iloc[-1])} · per {unit.lower()}',
         "", "peso"),
        ("Forecasted price", fmt.peso(end_val), f'{fmt.month_label(fc["date"].iloc[-1])} · {model}', "", "target"),
        ("Forecast direction", direction, f"{fmt.pct(end_change)} vs. latest observed over {horizon} months",
         fmt.trend_tone(end_change), "down" if end_change < 0 else "trend"),
        ("Typical error of this model", fmt.pct(mape, 1, signed=False) if pd.notna(mape) else "—",
         "MAPE on this series, Jul 2025 – Jun 2026 hold-out", "", "activity"),
    ])
    st.write("")

    with fmt.card(f"{commodity} · {market}", f"Historical vs. forecasted prices · {fc['date'].min():%b %Y} – "
                                              f"{fc['date'].max():%b %Y}", demo=demo):
        legend = [(NAVY, "Historical (actual)"), (TEAL, f"Forecast ({model})")]
        if analysis.has_interval(model):
            legend.append(("rgba(111,175,165,0.45)", f"{level} prediction interval"))
        fmt.legend_row(legend)
        fmt.show_chart(viz.forecast_fig(shown, fc, model, unit, band_label=f"{level} prediction interval"),
                       key="fc_main")
        if analysis.has_interval(model):
            st.caption(f"Models fitted on data through {fmt.month_label(origin)}. The band uses the study's empirical "
                       "intervals, which scale this series' own volatility by the errors seen in the Jul 2025 – "
                       "Jun 2026 hold-out. **Indicative only:** SARIMA was no better than plain Naive in the study.")
        else:
            st.caption(f"Models fitted on data through {fmt.month_label(origin)}. The study gives no interval for "
                       "Seasonal Naive. **Indicative only:** Seasonal Naive was the least accurate model.")

    left, right = st.columns([3, 2])
    with left, fmt.card("Forecast outlook across commodities",
                        f"{model} · median change vs. latest price at month {horizon} · "
                        f"{sel['region'] or 'all regions'}", demo=demo):
        outlook = analysis.future_outlook(model, horizon, sel["category"], sel["region"])
        if not outlook.empty:
            up, down = outlook.iloc[-1], outlook.iloc[0]
            st.caption(f"Largest expected rise: **{up['commodity']}** ({up['change_pct']:+.1f}%) · "
                       f"Largest expected drop: **{down['commodity']}** ({down['change_pct']:+.1f}%)")
        fmt.show_chart(viz.future_outlook_fig(outlook), key="fc_outlook")
    with right, fmt.card("About this series", f"{commodity} · {market}", demo=demo):
        rows = [("Forecast origin", fmt.month_label(origin)), ("Forecast months", FUTURE_LABEL),
                ("SARIMA specification", f"(p,d,q)(P,D,Q) = {info['sarima_spec']}")]
        rows += [(f"Hold-out MAPE · {m}", fmt.pct(v, 1, signed=False) if pd.notna(v) else "—")
                 for m, v in info["holdout_mape"].items()]
        st.markdown('<table class="meta-table">' + "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows)
                    + "</table>", unsafe_allow_html=True)
        st.caption("Hold-out MAPE is each model's error on this series over Jul 2025 – Jun 2026 (lower is better).")

    with st.expander("Forecast values (all models)"):
        table = pd.DataFrame({"Month": analysis.get_future_forecast(commodity, market, MODELS[0], 12)["date"]})
        for m_ in MODELS:
            f_ = analysis.get_future_forecast(commodity, market, m_, 12, level)
            table[m_] = f_["forecast"].to_numpy()
            if analysis.has_interval(m_):
                table[f"{m_} {level} low"], table[f"{m_} {level} high"] = f_["lower"].to_numpy(), f_["upper"].to_numpy()
        table["Month"] = table["Month"].dt.strftime("%b %Y")
        st.dataframe(table.style.format({c: "₱{:,.2f}" for c in table.columns if c != "Month"}, na_rep="—"),
                     hide_index=True, **fmt.STRETCH)

# --------------------------------------------------------------------------- #
# Hold-out test
# --------------------------------------------------------------------------- #
else:
    origin = analysis.forecast_origin(commodity, market)
    if origin is None:
        fmt.empty_state("Not enough observations to forecast this series", "Pick a market with a longer price history.")
        st.stop()
    series = all_series[all_series["date"] <= origin]  # history the models were fitted on
    with st.spinner("Preparing forecast…"):
        fc = analysis.get_forecast(series, commodity, market, model, horizon)
    future = fc[fc["segment"] == "Forecast"]
    if future.empty:
        fmt.empty_state("No forecast available for this selection")
        st.stop()
    latest = float(series["price"].iloc[-1])
    nxt = float(future["forecast"].iloc[0])
    change = (nxt / latest - 1) * 100 if latest else float("nan")
    direction = "Stable" if abs(change) < 0.5 else ("Rising" if change > 0 else "Falling")

    st.write("")
    fmt.kpi_cards([
        ("Latest observed price", fmt.peso(latest), f'{fmt.month_label(series["date"].iloc[-1])} · per {unit.lower()}',
         "", "peso"),
        ("Forecasted price", fmt.peso(nxt), f'{fmt.month_label(future["date"].iloc[0])} · {model}', "", "target"),
        ("Forecast direction", direction, f"{fmt.pct(change)} vs. latest observed", fmt.trend_tone(change),
         "down" if change < 0 else "trend"),
        ("Forecast period", f"{horizon} months",
         f'{fmt.month_label(future["date"].iloc[0])} – {fmt.month_label(future["date"].iloc[-1])}', "", "calendar"),
    ])
    st.write("")

    with fmt.card(f"{commodity} · {market}", "Forecasts made from data to " + fmt.month_label(origin)
                  + " vs. what was observed", demo=demo):
        fmt.legend_row([(NAVY, "Historical (actual)"), (TEAL, f"Forecast ({model})"),
                        (NAVY, "Observed in the forecast months (dotted)")])
        fmt.show_chart(viz.forecast_fig(series, fc, model, unit), key="fc_main")
        st.caption(f"Hold-out test: models fitted on data to {fmt.month_label(origin)}, forecasting "
                   f"{fmt.month_label(fc['date'].min())} onward. The prices that were later observed are drawn "
                   "for comparison (see Model Evaluation for accuracy). For the months after Jun 2026, switch to "
                   "the **Next 12 months** view.")

    with st.expander("Forecast values"):
        table = future[["date", "forecast", "actual"]].copy()
        table["date"] = table["date"].dt.strftime("%b %Y")
        table.columns = ["Month", "Forecast", "Observed"]
        table["Difference"] = table["Forecast"] - table["Observed"]
        st.dataframe(table.style.format({c: "₱{:,.2f}" for c in ["Forecast", "Observed", "Difference"]}, na_rep="—"),
                     hide_index=True, **fmt.STRETCH)
