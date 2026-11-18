"""Model Evaluation - MAE / RMSE / MAPE by model and period (uses analysis.get_model_metrics)."""
import pandas as pd
import streamlit as st

from utils import analysis, filters, formatting as fmt, ui_analytics as ui, visualizations as viz
from utils.config import EVAL_WINDOWS, MODELS, PERIOD_ORDER
from utils.data_loader import (forecasts_are_demo, load_about, load_interval_coverage, metrics_are_demo,
                               using_demo_data)
from utils.theme import MODEL_COLORS, PERIOD_COLORS

demo = using_demo_data() or metrics_are_demo()
fmt.page_header("Model Evaluation", "Seasonal Naive vs. Naive vs. SARIMA · lower MAE, RMSE and MAPE mean better accuracy",
                demo=demo)
df = fmt.get_data()
if df.empty:
    fmt.empty_state("No data loaded", "Run scripts/build_data.py to build the data folder.")
    st.stop()

# --------------------------------------------------------------------------- #
# Study-wide results: every evaluated series, from the study's Step 12 summaries
# --------------------------------------------------------------------------- #
acc = analysis.accuracy_table("pooled_MAPE")
dec_all = analysis.decision_table("overall")
latest_w = PERIOD_ORDER[-1]
post = acc[acc["window"] == latest_w].set_index("model")
if not post.empty:
    n_series, n_obs = int(post["n_series"].iloc[0]), int(post["n_obs"].iloc[0])
    st.write("")
    fmt.kpi_cards([
        (f"{m} · pooled MAPE", fmt.pct(post.loc[m, "value"], 2, signed=False), f"{latest_w} test window", "", icon)
        for m, icon in (("Naive", "target"), ("SARIMA", "target"), ("Seasonal Naive", "target"))
        if m in post.index
    ] + [("Series evaluated", f"{n_series:,}", f"{n_obs:,} forecast months · {latest_w}", "", "records")])
    finding = load_about().get("forecast_finding")
    if finding:
        st.caption(f"**Study finding:** {finding}.")
    st.write("")

left, right = st.columns([1, 1])
with left, fmt.card("Accuracy of all evaluated series", "Pooled MAPE by test period (lower is better)", demo=demo):
    fmt.legend_row([(MODEL_COLORS[m], m) for m in ("Seasonal Naive", "Naive", "SARIMA")])
    fmt.show_chart(viz.pooled_accuracy_fig(acc), key="me_pooled")
with right, fmt.card("Which model is more accurate overall?",
                     "Error ratio across series with 95% interval · below 1 favours the first model", demo=demo):
    metric_dec = st.radio("Error measure", ["MAPE", "MAE", "RMSE"], horizontal=True, key="me_dec_metric")
    dec_m = dec_all[dec_all["metric"] == metric_dec]
    fmt.show_chart(viz.decision_fig(dec_m), key="me_decision")
    st.caption("Each point compares two models on the same series (geometric-mean error ratio). "
               "Grey = no clear winner. SARIMA beats Seasonal Naive; against plain Naive it is no better.")

left, right = st.columns([1, 1])
with left, fmt.card("Accuracy by forecast distance", "Pooled MAPE by months ahead", demo=demo):
    win_h = st.radio("Test period", PERIOD_ORDER, index=len(PERIOD_ORDER) - 1, horizontal=True, key="me_win_h")
    hb = analysis.accuracy_table("pooled_MAPE", "horizon_band", window=win_h)
    fmt.show_chart(viz.horizon_band_fig(hb), key="me_horizon")
with right, fmt.card("How well do the prediction intervals cover?",
                     "Share of actual prices inside the interval · Post-Pandemic hold-out", demo=demo):
    fmt.show_chart(viz.interval_coverage_fig(load_interval_coverage()), key="me_cover")
    st.caption("Empirical intervals for the forward forecasts are calibrated on this hold-out. "
               "Coverage close to the nominal level means the bands are about the right width.")

with fmt.card("Accuracy by food category", "Pooled MAPE · model verdicts by category are in the table below", demo=demo):
    win_c = st.radio("Test period", PERIOD_ORDER, index=len(PERIOD_ORDER) - 1, horizontal=True, key="me_win_c")
    cat_acc = analysis.accuracy_table("pooled_MAPE", "category", window=win_c)
    if cat_acc.empty:
        st.caption("No category results for this period.")
    else:
        wide = cat_acc.pivot(index="group", columns="model", values="value").reindex(columns=MODELS)
        wide.insert(0, "Series", cat_acc.groupby("group")["n_series"].first())
        wide.index.name = "Category"
        best = wide[MODELS].idxmin(axis=1).rename("Lowest error")
        show = wide.join(best).reset_index()
        st.dataframe(show.style.format({m: "{:.2f}%" for m in MODELS} | {"Series": "{:,.0f}"}),
                     hide_index=True, **fmt.STRETCH)

st.markdown('<div class="section-break">Single series</div>', unsafe_allow_html=True)

with fmt.card():
    cols = st.columns(4)
    # only series the study evaluated (eligible series with hold-out forecasts)
    sel = filters.location_filters(analysis.restrict_to_forecast_series(df), require_market=True,
                                   show_category=False, slots=cols)
    c1, c2, c3 = st.columns(3)
    model = filters.sticky_select("Model", MODELS, "sel_model", MODELS[0], kind="radio",
                                  container=c1, horizontal=True)
    period = filters.sticky_select("Period", PERIOD_ORDER, "sel_period", PERIOD_ORDER[-1], kind="radio",
                                   container=c2, horizontal=True)
    metric_label = c3.radio("Compare by", ["MAPE", "MAE", "RMSE"], horizontal=True,
                            help="Metric used for the comparison panels below.")
metric = metric_label.lower()

if not sel["market"]:
    fmt.empty_state("No market available", "Choose another commodity or region.")
    st.stop()

perf = analysis.get_model_metrics(df, sel["commodity"], sel["market"])
if perf.empty:
    fmt.empty_state("No evaluation results for this series", "Try another commodity or market.")
    st.stop()

row = perf[(perf["model"] == model) & (perf["period"] == period)]
others = perf[(perf["model"] != model) & (perf["period"] == period)]
if row.empty:
    fmt.empty_state(f"No {model} results for {period}")
    st.stop()
r = row.iloc[0]


def vs_other(m):
    """Sub-text comparing the selected model with the other model."""
    if others.empty:
        return "", ""
    best = others.sort_values(m).iloc[0]  # compared with the most accurate of the other models
    diff = (r[m] / best[m] - 1) * 100
    return f'{diff:+.1f}% vs. {best["model"]}', ("down" if diff < 0 else "up")


st.write("")
fmt.kpi_cards([
    ("MAE", fmt.peso(r["mae"]), *vs_other("mae"), "peso"),
    ("RMSE", fmt.peso(r["rmse"]), *vs_other("rmse"), "activity"),
    ("MAPE", fmt.pct(r["mape"], 2, signed=False), *vs_other("mape"), "target"),
    ("Evaluated observations", f'{int(r["n_obs"]):,}', f"{period} · {model}", "", "records"),
])
st.caption(" · ".join(f"**{k}**: {v}" for k, v in fmt.METRIC_HELP.items()))
_train, _test = EVAL_WINDOWS[period]
st.caption(f"**{period} evaluation window:** models fitted on {_train}, tested on {_test} (12 months).")
st.write("")

title = f'{sel["commodity"]} · {sel["market"]}'
left, right = st.columns([2, 1])
with left, fmt.card("Actual vs. predicted prices", f"{title} · evaluation window", demo=demo):
    back = analysis.get_backtest(sel["commodity"], sel["market"], period)
    preds, actual = {}, pd.DataFrame()
    if len(back):
        preds = {m: back[["date", m]].rename(columns={m: "forecast"}) for m in MODELS}
        actual = back[["date", "actual"]].rename(columns={"actual": "price"})
    fmt.legend_row([(MODEL_COLORS[m], m) for m in preds])
    fmt.show_chart(viz.actual_vs_predicted_fig(actual, preds), key="me_avp")
with right, fmt.card("Which model is more accurate?", f"Lower {metric_label} by period", demo=demo):
    best = ui.best_model_by_period(perf, metric)
    if best.empty:
        st.caption("Not enough results to compare.")
    for b in best.itertuples():
        st.markdown(
            f'<div class="winner"><div><div class="w-period"><span class="dot" '
            f'style="background:{PERIOD_COLORS[b.period]}"></span>{b.period}</div>'
            f'<div class="w-model">{b.model}</div></div>'
            f'<div class="w-gap">{"tied with<br>" + b.other if b.gap_pct < 0.05 else f"{b.gap_pct:.1f}% lower<br>than {b.other}"}</div></div>',
            unsafe_allow_html=True)

with fmt.card(f"MAE, RMSE and MAPE · {period}", "Seasonal Naive vs. Naive vs. SARIMA", demo=demo):
    cols = st.columns(3)
    for col, m, name in zip(cols, ["mae", "rmse", "mape"], ["MAE", "RMSE", "MAPE"]):
        with col:
            st.caption(f"**{name}** · {fmt.METRIC_HELP[name]}")
            fmt.show_chart(viz.metric_compare_bar(perf[perf["period"] == period], m), key=f"me_{m}")

left, right = st.columns([1, 1])
with left, fmt.card("Accuracy across the three periods", f"{metric_label} by model", demo=demo):
    fmt.show_chart(viz.accuracy_across_periods_fig(perf, metric), key="me_across")
with right, fmt.card("Comparison table", "Green = lowest error within each period", demo=demo):
    table = perf.rename(columns={"period": "Period", "model": "Model", "mae": "MAE", "rmse": "RMSE",
                                 "mape": "MAPE"})
    table["Period"] = pd.Categorical(table["Period"], PERIOD_ORDER, ordered=True)
    table = table.sort_values(["Period", "Model"]).reset_index(drop=True)
    table["Period"] = table["Period"].astype(str)
    cols_m = ["MAE", "RMSE", "MAPE"]

    def highlight_best(data):
        css = pd.DataFrame("", index=data.index, columns=data.columns)
        for c in cols_m:
            best_v = data.groupby("Period")[c].transform("min")
            css.loc[data[c] == best_v, c] = "background-color:#DFF1EE;font-weight:600"
        return css

    styled = (table[["Period", "Model"] + cols_m].style.apply(highlight_best, axis=None)
              .format({"MAE": "₱{:,.2f}", "RMSE": "₱{:,.2f}", "MAPE": "{:.2f}%"}))
    st.dataframe(styled, hide_index=True, **fmt.STRETCH)
