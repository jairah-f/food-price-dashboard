"""Plotly figure builders. Pure functions: DataFrame in, Figure out."""
import pandas as pd
import plotly.graph_objects as go

from .config import EXCLUDED_LABEL, EXCLUDED_RANGE, PERIOD_ORDER, PERIOD_RANGE_LABELS, PERIODS
from .theme import (ALERT_COLORS, CATEGORY_COLORS, CORAL, ERA_COLORS, GRID, INK, MODEL_COLORS, MUTED,
                    NAVY, PERIOD_COLORS, SAGE, SAND, SLATE, TEAL)

FONT = "Inter, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
TEAL_BAND = "rgba(111,175,165,0.22)"


def _style(fig, height=360, legend=True):
    fig.update_layout(
        template="plotly_white", height=height, margin=dict(l=8, r=8, t=30, b=8),
        font=dict(family=FONT, size=13, color=INK), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", showlegend=legend,
        legend=dict(orientation="h", y=1.12, x=0, title_text="", font=dict(size=12)),
        hoverlabel=dict(bgcolor="white", font_size=13, bordercolor=GRID), hovermode="closest",
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, title_text=None, tickfont=dict(size=12))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, title_text=None, tickfont=dict(size=12))
    return fig


def _empty(message="No data for this selection", height=300):
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, xref="paper", yref="paper",
                       showarrow=False, font=dict(color=MUTED, size=14))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _style(fig, height=height, legend=False)


def _with_gaps(df, value_cols):
    """Insert an empty row for every missing month so lines break where data is missing
    instead of joining across the gap."""
    if len(df) < 2:
        return df
    full = pd.date_range(df["date"].min(), df["date"].max(), freq="MS")
    return df.set_index("date").reindex(full).rename_axis("date").reset_index()


def _excluded_band(fig, lo, hi):
    """Light band + label over the study's excluded months when the plotted range covers them."""
    a, b = EXCLUDED_RANGE
    if lo < a and hi > b:
        fig.add_vrect(x0=_iso(a), x1=_iso(b), fillcolor=MUTED, opacity=0.10, line_width=0, layer="below")
        fig.add_annotation(x=_iso(a + (b - a) / 2), y=0, yref="paper", yanchor="bottom", showarrow=False,
                           text=f"No data<br>{EXCLUDED_LABEL}", font=dict(size=11, color=MUTED))


def _iso(ts) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%d")


# ---------------------------- Overview ------------------------------------ #
def category_trend_fig(cs, mode="Index", height=360):
    if cs.empty:
        return _empty(height=height)
    fig = go.Figure()
    for i, (cat, g) in enumerate(cs.groupby("category")):
        g = _with_gaps(g.sort_values("date"), ["value"])
        fig.add_trace(go.Scatter(
            x=g["date"], y=g["value"], mode="lines", name=cat,
            line=dict(width=2.2, color=CATEGORY_COLORS[i % len(CATEGORY_COLORS)]),
            hovertemplate=("%{x|%b %Y}<br>" + cat + "<br>" +
                           ("Index %{y:.1f}" if mode == "Index" else "₱%{y:,.2f}") + "<extra></extra>")))
    fig.update_xaxes(title_text="Date")
    if mode == "Index":
        fig.update_yaxes(title_text="Index (start of range = 100)")
    else:
        fig.update_yaxes(tickprefix="₱", title_text="Average price (₱)")
    fig.update_layout(hovermode="x unified")
    return _style(fig, height=height)


def price_distribution_fig(d, height=340):
    """Box plot of prices by period. `d` needs columns [period, price_php]."""
    if d.empty:
        return _empty(height=height)
    fig = go.Figure()
    for p in PERIOD_ORDER:
        g = d[d["period"] == p]
        if g.empty:
            continue
        fig.add_trace(go.Box(
            y=g["price_php"], name=p, marker_color=PERIOD_COLORS[p], line=dict(color=PERIOD_COLORS[p]),
            fillcolor=PERIOD_COLORS[p], opacity=0.85, boxpoints="outliers", marker_size=3,
            hovertemplate="%{y:,.2f}<extra>" + p + "</extra>"))
    fig.update_yaxes(tickprefix="₱", title_text="Price (₱)")
    return _style(fig, height=height, legend=False)


def commodity_insights_fig(ins, top=8, height=340):
    """Largest price movements: latest 12 months vs. the 12 months before."""
    if ins.empty:
        return _empty("Not enough history to compare", height)
    t = ins.head(top).sort_values("change_pct")
    fig = go.Figure(go.Bar(
        x=t["change_pct"], y=t["commodity"], orientation="h",
        marker_color=[CORAL if v >= 0 else TEAL for v in t["change_pct"]],
        text=[f"{v:+.1f}%" for v in t["change_pct"]], textposition="outside", cliponaxis=False,
        customdata=t[["latest_avg", "prior_avg"]].to_numpy(),
        hovertemplate=("<b>%{y}</b><br>%{x:+.2f}%<br>Latest 12 mo: ₱%{customdata[0]:,.2f}"
                       "<br>Previous 12 mo: ₱%{customdata[1]:,.2f}<extra></extra>")))
    lim = max(abs(t["change_pct"]).max(), 1) * 1.35
    fig.update_xaxes(ticksuffix="%", range=[-lim, lim], showgrid=True, gridcolor=GRID, zeroline=True,
                     zerolinecolor=MUTED)
    return _style(fig, height=height, legend=False)


# ----------------------- Historical trends -------------------------------- #
def price_trend_fig(series, commodity, market_label, unit="KG", ma=None, ma_label="", height=400):
    if series.empty:
        return _empty(height=height)
    s = series.sort_values("date")
    avg = s["price"].mean()
    fig = go.Figure()
    _excluded_band(fig, s["date"].min(), s["date"].max())
    g = _with_gaps(s, ["price"])  # missing months break the line
    fig.add_trace(go.Scatter(
        x=g["date"], y=g["price"], mode="lines+markers", name="Retail price",
        line=dict(color=NAVY, width=2.2), marker=dict(size=4),
        customdata=[[commodity, market_label, unit]] * len(g),
        hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[1]}<br>%{x|%b %Y}<br>"
                       "₱%{y:,.2f} / %{customdata[2]}<extra></extra>")))
    if ma is not None and len(ma):
        fig.add_trace(go.Scatter(
            x=ma["date"], y=ma["price"], mode="lines", name=ma_label,
            line=dict(color=CORAL, width=2.4),
            hovertemplate="%{x|%b %Y}<br>" + ma_label + " ₱%{y:,.2f}<extra></extra>"))
    lo, hi = s.loc[s["price"].idxmin()], s.loc[s["price"].idxmax()]
    fig.add_trace(go.Scatter(
        x=[lo["date"], hi["date"]], y=[lo["price"], hi["price"]], mode="markers", name="Min / Max",
        marker=dict(size=10, color=TEAL, line=dict(color="white", width=1.5)),
        hovertemplate="%{x|%b %Y}<br>₱%{y:,.2f}<extra></extra>"))
    fig.add_hline(y=avg, line_dash="dot", line_color=MUTED, annotation_text=f"Avg ₱{avg:,.2f}",
                  annotation_position="top left", annotation_font=dict(size=12, color=MUTED))
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(tickprefix="₱", title_text=f"Price (₱ per {unit.lower()})")
    return _style(fig, height=height)


# ------------------------ Period comparison -------------------------------- #
def period_avg_bar(summary, height=340):
    s = summary.dropna(subset=["avg_price"])
    if s.empty:
        return _empty(height=height)
    fig = go.Figure(go.Bar(
        x=s["period"], y=s["avg_price"], marker_color=[PERIOD_COLORS[p] for p in s["period"]],
        text=[f"₱{v:,.2f}" for v in s["avg_price"]], textposition="outside", cliponaxis=False,
        customdata=s["n_obs"],
        hovertemplate="%{x}<br>₱%{y:,.2f}<br>%{customdata:,} observations<extra></extra>"))
    fig.update_yaxes(tickprefix="₱", title_text="Average price (₱)", range=[0, s["avg_price"].max() * 1.2])
    return _style(fig, height=height, legend=False)


def period_change_bar(changes, height=340):
    if changes.empty:
        return _empty("Not enough periods with data", height)
    fig = go.Figure(go.Bar(
        x=changes["comparison"], y=changes["pct_change"],
        marker_color=[CORAL if v >= 0 else TEAL for v in changes["pct_change"]],
        text=[f"{v:+.1f}%" for v in changes["pct_change"]], textposition="outside", cliponaxis=False,
        hovertemplate="%{x}<br>%{y:+.2f}%<extra></extra>"))
    fig.update_yaxes(ticksuffix="%", title_text="Median change (matched series)")
    fig.add_hline(y=0, line_color=MUTED, line_width=1)
    return _style(fig, height=height, legend=False)


def trend_shading_fig(series, periods=None, height=340):
    if series.empty:
        return _empty(height=height)
    periods = periods or PERIOD_ORDER
    s = series.sort_values("date")
    g = _with_gaps(s, ["price"])
    fig = go.Figure(go.Scatter(
        x=g["date"], y=g["price"], mode="lines", name="Retail price", line=dict(color=NAVY, width=2.2),
        hovertemplate="%{x|%b %Y}<br>₱%{y:,.2f}<extra></extra>"))
    lo, hi = s["date"].min(), s["date"].max()
    for p in periods:
        start, end = PERIODS[p]
        start, end = max(start, lo), min(end, hi)
        if start >= end:
            continue
        fig.add_shape(type="rect", xref="x", yref="paper", x0=_iso(start), x1=_iso(end), y0=0, y1=1,
                      fillcolor=PERIOD_COLORS[p], opacity=0.28, line_width=0, layer="below")
        fig.add_annotation(x=_iso(start + (end - start) / 2), y=1.0, yref="paper", yanchor="bottom",
                           text=p, showarrow=False, font=dict(size=12, color=INK))
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(tickprefix="₱", title_text="Price (₱)")
    return _style(fig, height=height, legend=False)


def regional_comparison_fig(rp):
    if rp.empty:
        return _empty()
    regions = sorted(rp["region"].unique(), reverse=True)
    fig = go.Figure()
    for p in PERIOD_ORDER:
        g = rp[rp["period"] == p]
        if g.empty:
            continue
        fig.add_trace(go.Bar(
            y=g["region"], x=g["avg_price"], name=p, orientation="h", marker_color=PERIOD_COLORS[p],
            hovertemplate="%{y}<br>" + p + "<br>₱%{x:,.2f}<extra></extra>"))
    fig.update_layout(barmode="group")
    fig.update_yaxes(categoryorder="array", categoryarray=regions)
    fig.update_xaxes(tickprefix="₱", showgrid=True, gridcolor=GRID, title_text="Average price (₱)")
    return _style(fig, height=max(420, 20 * len(regions) * 3))


def commodity_change_fig(table, height=420):
    """% change into the Pandemic and Post-Pandemic periods, per commodity."""
    if table.empty:
        return _empty(height=height)
    t = table.sort_values("pre_to_pandemic", na_position="first")
    fig = go.Figure()
    for col, name, color in (("pre_to_pandemic", "Pre-Pandemic → Pandemic", PERIOD_COLORS["Pandemic"]),
                             ("pandemic_to_post", "Pandemic → Post-Pandemic", PERIOD_COLORS["Post-Pandemic"])):
        fig.add_trace(go.Bar(y=t["commodity"], x=t[col], name=name, orientation="h", marker_color=color,
                             hovertemplate="%{y}<br>" + name + ": %{x:+.2f}%<extra></extra>"))
    fig.update_layout(barmode="group")
    fig.update_xaxes(ticksuffix="%", showgrid=True, gridcolor=GRID, zeroline=True, zerolinecolor=MUTED,
                     title_text="Median change (matched series)")
    return _style(fig, height=height)


# ----------------------------- Forecasting --------------------------------- #
def forecast_fig(hist, fc, model, unit="KG", height=440, band_label="Prediction interval",
                 start_label="Forecast start", forecast_name=None):
    """History + forecast. `fc` columns: date, forecast, lower, upper, actual, segment.

    Hold-out view: `actual` holds the price later observed for each forecast month and is drawn as a
    second line so forecast and outcome can be compared. Forward view: `actual` is empty."""
    if hist.empty:
        return _empty(height=height)
    hist = hist.sort_values("date")
    last_date = hist["date"].iloc[-1]
    last_val = float(hist["price"].iloc[-1])
    back = fc[fc["segment"] == "Backtest"] if len(fc) else fc
    fut = fc[fc["segment"] == "Forecast"] if len(fc) else fc

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist["date"], y=hist["price"], mode="lines", name="Historical (actual)",
        line=dict(color=NAVY, width=2.4),
        hovertemplate=f"%{{x|%b %Y}}<br>Actual ₱%{{y:,.2f}} / {unit.lower()}<extra></extra>"))
    if len(back):
        fig.add_trace(go.Scatter(
            x=back["date"], y=back["forecast"], mode="lines+markers", name="Predicted (backtest)",
            line=dict(color=MUTED, width=1.6, dash="dot"), marker=dict(size=6),
            hovertemplate="%{x|%b %Y}<br>Predicted ₱%{y:,.2f}<extra></extra>"))
    if len(fut):
        xs = [last_date] + fut["date"].tolist()
        ys = [last_val] + fut["forecast"].tolist()
        if fut["lower"].notna().all() and fut["upper"].notna().all():
            up = [last_val] + fut["upper"].tolist()
            lw = [last_val] + fut["lower"].tolist()
            fig.add_trace(go.Scatter(
                x=xs + xs[::-1], y=up + lw[::-1], fill="toself", mode="lines",
                fillcolor=TEAL_BAND, line=dict(width=0), name=band_label, hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers", name=forecast_name or f"Forecast ({model})",
            line=dict(color=TEAL, width=3, dash="dash"), marker=dict(size=7),
            hovertemplate="%{x|%b %Y}<br>Forecast ₱%{y:,.2f}<extra></extra>"))
        obs = fut[fut["actual"].notna()]
        if len(obs):
            fig.add_trace(go.Scatter(
                x=obs["date"], y=obs["actual"], mode="lines+markers", name="Observed later",
                line=dict(color=NAVY, width=2.0, dash="dot"), marker=dict(size=6, symbol="diamond"),
                hovertemplate="%{x|%b %Y}<br>Observed ₱%{y:,.2f}<extra></extra>"))
        fig.add_shape(type="rect", xref="x", yref="paper", x0=_iso(last_date),
                      x1=_iso(fut["date"].iloc[-1]), y0=0, y1=1,
                      fillcolor=TEAL, opacity=0.07, line_width=0, layer="below")
    fig.add_shape(type="line", xref="x", yref="paper", x0=_iso(last_date), x1=_iso(last_date),
                  y0=0, y1=1, line=dict(color=MUTED, width=1, dash="dot"))
    fig.add_annotation(x=_iso(last_date), y=1.0, yref="paper", yanchor="bottom", text=start_label,
                       showarrow=False, font=dict(size=12, color=MUTED))
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(tickprefix="₱", title_text=f"Price (₱ per {unit.lower()})")
    return _style(fig, height=height)


def future_outlook_fig(outlook, top=8, height=420):
    """Median forecast % change vs. the last observed price: the biggest expected rises and falls."""
    if outlook.empty:
        return _empty("No forward forecasts for this selection", height)
    t = pd.concat([outlook.head(top), outlook.tail(top)]).drop_duplicates("commodity").sort_values("change_pct")
    fig = go.Figure(go.Bar(
        x=t["change_pct"], y=t["commodity"], orientation="h",
        marker_color=[CORAL if v >= 0 else TEAL for v in t["change_pct"]],
        text=[f"{v:+.1f}%" for v in t["change_pct"]], textposition="outside", cliponaxis=False,
        customdata=t["series"], hovertemplate="<b>%{y}</b><br>%{x:+.2f}% (median)<br>%{customdata} series<extra></extra>"))
    lim = max(abs(t["change_pct"]).max(), 1) * 1.35
    fig.update_xaxes(ticksuffix="%", range=[-lim, lim], showgrid=True, gridcolor=GRID, zeroline=True,
                     zerolinecolor=MUTED, title_text="Median forecast change vs. latest price")
    return _style(fig, height=height, legend=False)


# ------------------------- Model evaluation -------------------------------- #
_METRIC_FMT = {"mae": ("MAE", "₱{:,.2f}", "₱"), "rmse": ("RMSE", "₱{:,.2f}", "₱"),
               "mape": ("MAPE", "{:.2f}%", "")}


def actual_vs_predicted_fig(actual, preds, height=340):
    """actual: [date, price]; preds: {model: [date, forecast]} for the evaluation window."""
    if actual.empty or not preds:
        return _empty("No actual-vs-predicted values available", height)
    fig = go.Figure(go.Scatter(
        x=actual["date"], y=actual["price"], mode="lines+markers", name="Actual",
        line=dict(color=NAVY, width=2.4), marker=dict(size=6),
        hovertemplate="%{x|%b %Y}<br>Actual ₱%{y:,.2f}<extra></extra>"))
    for model, p in preds.items():
        fig.add_trace(go.Scatter(
            x=p["date"], y=p["forecast"], mode="lines+markers", name=f"{model} (predicted)",
            line=dict(color=MODEL_COLORS.get(model, TEAL), width=2.2, dash="dash"), marker=dict(size=7),
            hovertemplate="%{x|%b %Y}<br>" + model + " ₱%{y:,.2f}<extra></extra>"))
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(tickprefix="₱", title_text="Price (₱)")
    return _style(fig, height=height)


def metric_compare_bar(perf_period, metric, height=270):
    """Seasonal Naive vs Naive vs SARIMA for one metric and one period."""
    if perf_period.empty:
        return _empty(height=height)
    name, fmt, prefix = _METRIC_FMT[metric]
    fig = go.Figure(go.Bar(
        x=perf_period["model"], y=perf_period[metric],
        marker_color=[MODEL_COLORS.get(m, NAVY) for m in perf_period["model"]],
        text=[fmt.format(v) for v in perf_period[metric]], textposition="outside", cliponaxis=False,
        hovertemplate="%{x}<br>" + name + " " + fmt.replace("{:", "%{y:") + "<extra></extra>"))
    fig.update_yaxes(tickprefix=prefix, ticksuffix="%" if metric == "mape" else "",
                     range=[0, perf_period[metric].max() * 1.28])
    return _style(fig, height=height, legend=False)


def accuracy_across_periods_fig(perf, metric, height=340):
    if perf.empty:
        return _empty(height=height)
    name, fmt, prefix = _METRIC_FMT[metric]
    fig = go.Figure()
    for model, g in perf.groupby("model", sort=False):
        g = g.set_index("period").reindex([p for p in PERIOD_ORDER if p in set(g["period"])]).reset_index()
        fig.add_trace(go.Bar(
            x=g["period"], y=g[metric], name=model, marker_color=MODEL_COLORS.get(model, NAVY),
            text=[fmt.format(v) for v in g[metric]], textposition="outside", cliponaxis=False,
            hovertemplate="%{x}<br>" + model + "<br>" + name + ": %{y:,.2f}<extra></extra>"))
    fig.update_layout(barmode="group")
    fig.update_yaxes(tickprefix=prefix, ticksuffix="%" if metric == "mape" else "", title_text=name)
    return _style(fig, height=height)


# ------------------------ Trends: index, trend and volatility ---------------- #
def chain_index_fig(ci, title_base, height=340):
    """Chain-linked index lines for one segment. ci: [group, month, index_value]."""
    if ci.empty:
        return _empty(height=height)
    fig = go.Figure()
    for i, (grp, g) in enumerate(ci.groupby("group")):
        g = g.sort_values("month")
        fig.add_trace(go.Scatter(
            x=g["month"], y=g["index_value"], mode="lines", name=grp,
            line=dict(width=2.2, color=CATEGORY_COLORS[i % len(CATEGORY_COLORS)]),
            hovertemplate="%{x|%b %Y}<br>" + grp + "<br>Index %{y:.1f}<extra></extra>"))
    fig.add_hline(y=100, line_dash="dot", line_color=MUTED, line_width=1,
                  annotation_text=title_base, annotation_position="bottom left",
                  annotation_font=dict(size=11, color=MUTED))
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(title_text="Index")
    return _style(fig, height=height)


def trend_vol_fig(stats, commodity, height=340):
    """One point per market: annualised trend vs. monthly volatility for a commodity."""
    if stats.empty:
        return _empty("No trend estimates for this selection", height)
    fig = go.Figure(go.Scatter(
        x=stats["vol_pct"], y=stats["trend_pct_yr"], mode="markers",
        marker=dict(size=9, color=TEAL, line=dict(color="white", width=1), opacity=0.9),
        customdata=stats[["market", "region", "n_obs"]].to_numpy(),
        hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[1]}<br>Trend %{y:+.1f}% per year"
                       "<br>Volatility %{x:.1f}%<br>%{customdata[2]} months<extra></extra>")))
    fig.add_hline(y=0, line_color=MUTED, line_width=1)
    fig.update_xaxes(ticksuffix="%", title_text="Typical monthly swing (volatility)")
    fig.update_yaxes(ticksuffix="%", title_text="Trend (% per year)")
    return _style(fig, height=height, legend=False)


# ------------------------ Period analysis with intervals --------------------- #
def period_ci_fig(rows, label_col="group", height=340):
    """Median % change with 95% CI per group (study Step 10). Hollow bars = too few markets/series."""
    if rows.empty:
        return _empty("No study results for this comparison", height)
    t = rows.sort_values("median_pct")
    ok = t["reliable"].astype(bool)
    err_hi = (t["ci_high"] - t["median_pct"]).fillna(0)
    err_lo = (t["median_pct"] - t["ci_low"]).fillna(0)
    fig = go.Figure(go.Bar(
        y=t[label_col], x=t["median_pct"], orientation="h",
        marker=dict(color=[CORAL if r else "rgba(255,135,111,0.30)" for r in ok]),
        error_x=dict(type="data", symmetric=False, array=err_hi, arrayminus=err_lo, color=INK, thickness=1.4),
        customdata=t[["series", "markets", "ci_low", "ci_high", "share_rising_pct"]].to_numpy(),
        hovertemplate=("<b>%{y}</b><br>Median %{x:+.1f}%<br>95% CI %{customdata[2]:.1f} to %{customdata[3]:.1f}"
                       "<br>%{customdata[0]} series · %{customdata[1]} markets"
                       "<br>%{customdata[4]:.0f}% of series rising<extra></extra>")))
    fig.update_xaxes(ticksuffix="%", showgrid=True, gridcolor=GRID, zeroline=True, zerolinecolor=MUTED,
                     title_text="Median % change (matched series), 95% CI")
    return _style(fig, height=max(height, 34 * len(t) + 90), legend=False)


def category_region_heatmap(rows, height=380):
    """Median % change by category x region; cells the study marks unreliable are left blank."""
    if rows.empty:
        return _empty("No category-by-region cells", height)
    r = rows[rows["reliable"].astype(bool)]
    if r.empty:
        return _empty("No reliable category-by-region cells", height)
    z = r.pivot_table(index="category", columns="region", values="median_pct")
    fig = go.Figure(go.Heatmap(
        z=z.values, x=z.columns, y=z.index, colorscale=[[0, "#F3F8F6"], [1, CORAL]], zmin=0,
        text=[[("" if pd.isna(v) else f"{v:.1f}") for v in row] for row in z.values],
        texttemplate="%{text}", hovertemplate="%{y}<br>%{x}<br>Median %{z:+.1f}%<extra></extra>",
        colorbar=dict(title="%", thickness=12)))
    fig.update_xaxes(tickangle=-40, side="bottom")
    return _style(fig, height=height, legend=False)


# ------------------------ Model evaluation: study-wide accuracy -------------- #
def pooled_accuracy_fig(acc, metric_label="Pooled MAPE", height=320):
    """acc: [window, model, value]. Grouped bars: window on x, one bar per model."""
    if acc.empty:
        return _empty(height=height)
    fig = go.Figure()
    for model in ("Seasonal Naive", "Naive", "SARIMA"):
        g = acc[acc["model"] == model].set_index("window").reindex(PERIOD_ORDER).reset_index()
        g = g.dropna(subset=["value"])
        if g.empty:
            continue
        fig.add_trace(go.Bar(
            x=g["window"], y=g["value"], name=model, marker_color=MODEL_COLORS[model],
            text=[f"{v:.2f}" for v in g["value"]], textposition="outside", cliponaxis=False,
            hovertemplate="%{x}<br>" + model + "<br>" + metric_label + " %{y:.2f}<extra></extra>"))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title_text=metric_label, range=[0, acc["value"].max() * 1.22])
    return _style(fig, height=height)


def decision_fig(dec, height=340):
    """Forest plot of the geometric-mean error ratio (model / comparison) with 95% CI. Left of 1 favours the model."""
    if dec.empty:
        return _empty(height=height)
    d = dec.copy()
    d["label"] = d["window"] + " · " + d["model"] + " vs. " + d["vs"]
    d = d.iloc[::-1]
    fig = go.Figure(go.Scatter(
        x=d["ratio"], y=d["label"], mode="markers",
        marker=dict(size=10, color=[TEAL if v == "sarima better" or v == "naive better" else MUTED
                                    for v in d["verdict"]]),
        error_x=dict(type="data", symmetric=False, array=d["ci_high"] - d["ratio"],
                     arrayminus=d["ratio"] - d["ci_low"], color=INK, thickness=1.4),
        customdata=d[["verdict", "ties_pct", "n_series"]].to_numpy(),
        hovertemplate=("<b>%{y}</b><br>Error ratio %{x:.3f}<br>Verdict: %{customdata[0]}"
                       "<br>%{customdata[2]:.0f} series · %{customdata[1]}% ties<extra></extra>")))
    fig.add_vline(x=1, line_dash="dot", line_color=MUTED)
    fig.update_xaxes(showgrid=True, gridcolor=GRID, title_text="Error ratio (below 1 = first model is more accurate)")
    return _style(fig, height=max(height, 38 * len(d) + 90), legend=False)


def horizon_band_fig(acc, height=300):
    """acc: [model, group, value] with group in horizon bands. Pooled MAPE by forecast distance."""
    if acc.empty:
        return _empty(height=height)
    bands = ["1-3", "4-6", "7-12"]
    fig = go.Figure()
    for model in ("Seasonal Naive", "Naive", "SARIMA"):
        g = acc[acc["model"] == model].set_index("group").reindex(bands).reset_index().dropna(subset=["value"])
        if g.empty:
            continue
        fig.add_trace(go.Scatter(
            x=g["group"], y=g["value"], mode="lines+markers", name=model,
            line=dict(color=MODEL_COLORS[model], width=2.4), marker=dict(size=8),
            hovertemplate="Months ahead %{x}<br>" + model + " MAPE %{y:.2f}%<extra></extra>"))
    fig.update_xaxes(title_text="Months ahead", showgrid=False)
    fig.update_yaxes(ticksuffix="%", title_text="Pooled MAPE")
    return _style(fig, height=height)


def interval_coverage_fig(cov, height=300):
    """Share of actual prices that fell inside the prediction interval vs. the nominal level."""
    c = cov[cov["horizon_band"] == "all"]
    if c.empty:
        return _empty(height=height)
    fig = go.Figure()
    for model in ("Naive", "SARIMA"):
        g = c[c["model"] == model].sort_values("nominal_pct")
        fig.add_trace(go.Bar(
            x=[f"{int(n)}% interval" for n in g["nominal_pct"]], y=g["coverage_pct"], name=model,
            marker_color=MODEL_COLORS[model], text=[f"{v:.1f}%" for v in g["coverage_pct"]],
            textposition="outside", cliponaxis=False,
            hovertemplate="%{x}<br>" + model + " covered %{y:.1f}%<extra></extra>"))
    fig.update_layout(barmode="group")
    fig.update_yaxes(ticksuffix="%", range=[0, 110], title_text="Actual prices inside interval")
    return _style(fig, height=height)


# ------------------------ Market Watch --------------------------------------- #
def alert_by_category_fig(m, height=300):
    """Stacked bars: series per category by alert level (latest month)."""
    if m.empty:
        return _empty(height=height)
    g = m.groupby(["category", "alert_level"]).size().unstack(fill_value=0)
    fig = go.Figure()
    for lv in ("alert", "watch", "normal"):
        if lv in g:
            fig.add_trace(go.Bar(y=g.index, x=g[lv], name=lv.capitalize(), orientation="h",
                                 marker_color=ALERT_COLORS[lv],
                                 hovertemplate="%{y}<br>" + lv + ": %{x} series<extra></extra>"))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(showgrid=True, gridcolor=GRID, title_text="Series (commodity x market)")
    return _style(fig, height=height)


def market_map_fig(mk, height=520):
    """Map of the study's 97 markets, coloured by when they reported."""
    if mk.empty:
        return _empty(height=height)
    fig = go.Figure()
    for era, col in ERA_COLORS.items():
        g = mk[mk["era"] == era]
        if g.empty:
            continue
        fig.add_trace(go.Scattergeo(
            lon=g["longitude"], lat=g["latitude"], mode="markers", name=era.capitalize(),
            marker=dict(size=(g["observations"] ** 0.5).clip(lower=6) / 3.2 + 4, color=col,
                        line=dict(color="white", width=1), opacity=0.9),
            customdata=g[["market", "region", "observations", "commodities", "first_month", "last_month"]]
            .assign(first_month=g["first_month"].dt.strftime("%b %Y"),
                    last_month=g["last_month"].dt.strftime("%b %Y")).to_numpy(),
            hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[1]}<br>%{customdata[2]:,} observations · "
                           "%{customdata[3]} commodities<br>%{customdata[4]} – %{customdata[5]}<extra></extra>")))
    fig.update_geos(fitbounds="locations", visible=False, resolution=50, showcountries=True,
                    countrycolor=GRID, showland=True, landcolor="#EEF3F1", showocean=True, oceancolor="#F8FBFA")
    return _style(fig, height=height)
