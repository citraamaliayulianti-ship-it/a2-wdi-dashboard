"""The three principal views. Each answers one part of the dashboard question.

Every view keeps its heading, unit, sources, latest-observation date, controls
and outputs inside ``st.container(key=<view id>)`` so they can be checked
against ``dashboard.yml``.
"""

from __future__ import annotations

import math

import altair as alt
import pandas as pd
import streamlit as st

from src.analysis import describe_strength, fit_line, income_fit


DOWNLOAD_LABEL = "Download filtered data (CSV)"
DATE_LABEL = "Latest observation"
EMPTY_MESSAGE = "No countries match the selected filters."

PUBLISHER = "World Bank"
SOURCES = [
    "World Development Indicators: GDP per capita, PPP (constant 2021 international $) (NY.GDP.PCAP.PP.KD)",
    "World Development Indicators: Life expectancy at birth, total (years) (SP.DYN.LE00.IN)",
    "World Development Indicators: Domestic general government health expenditure (% of GDP) (SH.XPD.GHED.GD.ZS)",
    "World Development Indicators: PM2.5 air pollution, mean annual exposure (micrograms per cubic meter) (EN.ATM.PM25.MC.M3)",
    "World Bank Indicators API: economies with region and income group (FY2027 classification)",
]

# Diverging pair (validated for colour-vision deficiency): blue = longer than
# predicted, red = shorter. Neutral ink for lines and labels.
LONGER = "#2a78d6"
SHORTER = "#e34948"
POINT = "#2a78d6"
INK = "#52514e"
GRID = "#e6e5e0"

FACTORS = {
    "Government health spending (% of GDP)": {
        "column": "gov_health_exp_pct_gdp",
        "axis": "Domestic general government health expenditure (% of GDP)",
        "short": "government health spending",
        "step": 1.0,
        "step_text": "per extra 1% of GDP spent by government on health",
    },
    "PM2.5 air pollution (µg/m³)": {
        "column": "pm25_ug_m3",
        "axis": "PM2.5 mean annual exposure (micrograms per cubic metre)",
        "short": "air pollution (PM2.5)",
        "step": 10.0,
        "step_text": "per extra 10 µg/m³ of PM2.5",
    },
}


def _style(chart: alt.Chart) -> alt.Chart:
    return (
        chart.configure_axis(gridColor=GRID, domainColor=GRID, tickColor=GRID, labelColor=INK,
                             titleColor=INK, titleFontWeight="normal", labelFontSize=12, titleFontSize=12)
        .configure_view(strokeWidth=0)
        .configure_legend(labelColor=INK, titleColor=INK, orient="top")
    )


def _sources() -> None:
    lines = "  \n".join(f"{PUBLISHER}, {title}" for title in SOURCES)
    st.caption(f"**Sources:**  \n{lines}")


def _latest(data: pd.DataFrame) -> None:
    st.caption(f"{DATE_LABEL}: {data['date'].max().date().isoformat()}")


def _download(frame: pd.DataFrame, key: str, name: str) -> None:
    st.download_button(
        DOWNLOAD_LABEL,
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name=name,
        mime="text/csv",
        key=key,
    )


def _spaced_labels(frame: pd.DataFrame, per_side: int = 3) -> pd.DataFrame:
    """The largest gaps above and below the line, skipping labels that would overlap."""
    kept: list[pd.Series] = []
    for side in (frame.nlargest(10, "residual_years"), frame.nsmallest(10, "residual_years")):
        count = 0
        for _, row in side.iterrows():
            if count == per_side:
                break
            clash = any(abs(math.log10(row["gdp_pc_ppp"]) - math.log10(k["gdp_pc_ppp"])) < 0.35
                        and abs(row["life_expectancy"] - k["life_expectancy"]) < 2.5 for k in kept)
            if not clash:
                kept.append(row)
                count += 1
    return pd.DataFrame(kept)


def _year_picker(data: pd.DataFrame, key: str) -> int:
    years = sorted((int(y) for y in data["year"].unique()), reverse=True)
    return st.selectbox("Year", years, index=0, key=key)


def render_income_health(data: pd.DataFrame) -> None:
    """View 1: how closely life expectancy tracks income."""
    st.header("1. How closely does life expectancy track income?")
    st.caption("Unit: years of life expectancy at birth. Income is GDP per capita, PPP (constant 2021 international $), shown on a log scale.")
    _latest(data)

    left, right = st.columns([1, 3])
    with left:
        year = _year_picker(data, "income_health_year")
    with right:
        groups = list(dict.fromkeys(g for g in ["Low income", "Lower middle income", "Upper middle income", "High income"]
                                    if g in set(data["income_group"])))
        chosen = st.multiselect("Income groups", groups, default=groups, key="income_health_income")

    year_data = data.loc[data["year"] == year]
    filtered = year_data.loc[year_data["income_group"].isin(chosen)]

    if filtered.empty:
        st.info(EMPTY_MESSAGE)
    else:
        fit = income_fit(year_data)
        per_doubling = fit.slope * math.log(2)
        a, b, c = st.columns(3)
        a.metric("Differences in life expectancy explained by income (R²)", f"{fit.r_squared:.0%}")
        b.metric("Extra years per doubling of income", f"{per_doubling:.1f} years")
        c.metric("Countries shown", f"{len(filtered)} of {len(year_data)}")

        line = year_data.sort_values("gdp_pc_ppp")
        x = alt.X("gdp_pc_ppp:Q", scale=alt.Scale(type="log", domain=[500, 200000], nice=False),
                  title="GDP per capita, PPP (constant 2021 international $, log scale)", axis=alt.Axis(format="$,.0f"))
        trend = alt.Chart(line).mark_line(color=INK, strokeWidth=2).encode(
            x=x, y=alt.Y("predicted_life_expectancy:Q"))
        points = alt.Chart(filtered).mark_circle(size=70, color=POINT, opacity=0.75, stroke="white", strokeWidth=1).encode(
            x=x,
            y=alt.Y("life_expectancy:Q", title="Life expectancy at birth (years)", scale=alt.Scale(zero=False)),
            tooltip=[
                alt.Tooltip("country:N", title="Country"),
                alt.Tooltip("income_group:N", title="Income group"),
                alt.Tooltip("gdp_pc_ppp:Q", title="GDP per capita (PPP $)", format="$,.0f"),
                alt.Tooltip("life_expectancy:Q", title="Life expectancy (years)", format=".1f"),
                alt.Tooltip("predicted_life_expectancy:Q", title="Predicted from income", format=".1f"),
                alt.Tooltip("residual_years:Q", title="Gap (years)", format="+.1f"),
            ],
        )
        extremes = _spaced_labels(filtered)
        labels = alt.Chart(extremes).mark_text(align="left", dx=7, fontSize=11, color=INK).encode(
            x=x, y="life_expectancy:Q", text="country:N")
        st.altair_chart(_style((trend + points + labels).properties(height=430)), width="stretch")
        st.markdown(
            f"**Reading the chart:** each dot is a country in {year}; the grey line is the life expectancy "
            f"typical for each income level. Income alone accounts for **{fit.r_squared:.0%}** of the differences "
            f"in life expectancy between the {fit.n} countries, and each doubling of income goes with about "
            f"**{per_doubling:.1f} more years** of life. The dots furthest above or below the line are labelled; "
            "view 2 ranks them."
        )

    _sources()
    _download(filtered, "income_health_download", f"income_life_expectancy_{year}.csv")


def render_residual_ranking(data: pd.DataFrame) -> None:
    """View 2: which countries live longer or shorter than their income predicts."""
    st.header("2. Which countries live longer or shorter than their income predicts?")
    st.caption("Unit: years. The gap is actual life expectancy minus the life expectancy predicted from income for the same year.")
    _latest(data)

    left, right = st.columns([1, 3])
    with left:
        year = _year_picker(data, "ranking_year")
    with right:
        regions = sorted(data["region"].unique())
        chosen = st.multiselect("Regions", regions, default=regions, key="ranking_region")

    filtered = data.loc[(data["year"] == year) & data["region"].isin(chosen)]

    if filtered.empty:
        st.info(EMPTY_MESSAGE)
    else:
        a, b, c = st.columns(3)
        a.metric("Living 5+ years longer than predicted", f"{int((filtered['residual_years'] >= 5).sum())} countries")
        b.metric("Living 5+ years shorter than predicted", f"{int((filtered['residual_years'] <= -5).sum())} countries")
        c.metric("Countries shown", f"{len(filtered)}")

        ranked = filtered.sort_values("residual_years", ascending=False)
        shown = ranked if len(ranked) <= 20 else pd.concat([ranked.head(10), ranked.tail(10)])
        shown = shown.assign(direction=lambda f: f["residual_years"].ge(0).map(
            {True: "Longer than predicted", False: "Shorter than predicted"}))
        order = shown["country"].tolist()
        bars = alt.Chart(shown).mark_bar(cornerRadiusEnd=4, height=16).encode(
            x=alt.X("residual_years:Q", title="Gap between actual and predicted life expectancy (years)"),
            y=alt.Y("country:N", sort=order, title=None, axis=alt.Axis(labelOverlap=False, labelLimit=220)),
            color=alt.Color("direction:N", title=None,
                            scale=alt.Scale(domain=["Longer than predicted", "Shorter than predicted"], range=[LONGER, SHORTER])),
            tooltip=[
                alt.Tooltip("country:N", title="Country"),
                alt.Tooltip("region:N", title="Region"),
                alt.Tooltip("income_group:N", title="Income group"),
                alt.Tooltip("life_expectancy:Q", title="Life expectancy (years)", format=".1f"),
                alt.Tooltip("predicted_life_expectancy:Q", title="Predicted from income", format=".1f"),
                alt.Tooltip("residual_years:Q", title="Gap (years)", format="+.1f"),
            ],
        )
        def value_labels(rows: pd.DataFrame, align: str, dx: int) -> alt.Chart:
            return alt.Chart(rows).mark_text(fontSize=11, color=INK, align=align, dx=dx).encode(
                x="residual_years:Q", y=alt.Y("country:N", sort=order),
                text=alt.Text("residual_years:Q", format="+.1f"))

        above = value_labels(shown.loc[shown["residual_years"] >= 0], "left", 6)
        below = value_labels(shown.loc[shown["residual_years"] < 0], "right", -6)
        zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=INK, strokeWidth=1).encode(x="x:Q")
        note = "all countries" if len(ranked) <= 20 else "the 10 largest gaps in each direction"
        st.altair_chart(_style((bars + above + below + zero).properties(height=alt.Step(26))), width="stretch")
        st.caption(f"Chart shows {note}; the table below lists every selected country.")

        table = ranked[["country", "region", "income_group", "gdp_pc_ppp", "life_expectancy",
                        "predicted_life_expectancy", "residual_years"]]
        st.dataframe(
            table,
            hide_index=True,
            height=280,
            column_config={
                "country": "Country",
                "region": "Region",
                "income_group": "Income group",
                "gdp_pc_ppp": st.column_config.NumberColumn("GDP per capita (PPP $)", format="%,.0f"),
                "life_expectancy": st.column_config.NumberColumn("Life expectancy (years)", format="%.1f"),
                "predicted_life_expectancy": st.column_config.NumberColumn("Predicted (years)", format="%.1f"),
                "residual_years": st.column_config.NumberColumn("Gap (years)", format="%+.1f"),
            },
        )

    _sources()
    _download(filtered, "ranking_download", f"life_expectancy_gap_{year}.csv")


def render_gap_factors(data: pd.DataFrame) -> None:
    """View 3: is the gap linked to government health spending or to air pollution?"""
    st.header("3. Is the gap linked to government health spending or to air pollution?")
    st.caption("Unit: years of gap (actual minus predicted life expectancy), compared with a second World Bank indicator.")
    _latest(data)

    factor_name = st.radio("Compare the gap with", list(FACTORS), index=0, horizontal=True, key="factors_choice")
    factor = FACTORS[factor_name]
    left, right = st.columns([1, 3])
    with left:
        year = _year_picker(data, "factors_year")
    with right:
        groups = [g for g in ["Low income", "Lower middle income", "Upper middle income", "High income"]
                  if g in set(data["income_group"])]
        chosen = st.multiselect("Income groups", groups, default=groups, key="factors_income")

    filtered = data.loc[(data["year"] == year) & data["income_group"].isin(chosen)]
    plotted = filtered.dropna(subset=[factor["column"]])

    if filtered.empty:
        st.info(EMPTY_MESSAGE)
    elif len(plotted) < 5:
        st.warning(f"Only {len(plotted)} selected countries report {factor['short']} in {year}; too few to describe a pattern.")
    else:
        fit = fit_line(plotted[factor["column"]], plotted["residual_years"])
        a, b, c = st.columns(3)
        a.metric("Correlation with the gap (r)", f"{fit.correlation:+.2f}")
        b.metric(f"Change in gap {factor['step_text']}", f"{fit.slope * factor['step']:+.2f} years")
        c.metric("Countries with data", f"{fit.n} of {len(filtered)}")

        xs = plotted[factor["column"]]
        ends = pd.DataFrame({"x": [xs.min(), xs.max()]})
        ends["y"] = fit.intercept + fit.slope * ends["x"]
        x = alt.X(f"{factor['column']}:Q", title=factor["axis"])
        points = alt.Chart(plotted).mark_circle(size=70, color=POINT, opacity=0.75, stroke="white", strokeWidth=1).encode(
            x=x,
            y=alt.Y("residual_years:Q", title="Gap vs income prediction (years)"),
            tooltip=[
                alt.Tooltip("country:N", title="Country"),
                alt.Tooltip("income_group:N", title="Income group"),
                alt.Tooltip(f"{factor['column']}:Q", title=factor_name, format=".1f"),
                alt.Tooltip("residual_years:Q", title="Gap (years)", format="+.1f"),
            ],
        )
        zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=INK, strokeDash=[4, 4], strokeWidth=1).encode(y="y:Q")
        trend = alt.Chart(ends).mark_line(color=INK, strokeWidth=2).encode(x="x:Q", y="y:Q")
        st.altair_chart(_style((zero + points + trend).properties(height=400)), width="stretch")

        direction = "longer" if fit.slope > 0 else "shorter"
        strength = describe_strength(fit.correlation)
        degree = "slightly " if abs(fit.correlation) < 0.3 else ""
        st.markdown(
            f"**Reading the chart:** in {year}, countries with more {factor['short']} tend to live {degree}"
            f"{direction} than their income predicts. The link is **{strength}** (r = {fit.correlation:+.2f}): "
            f"{factor['short']} accounts for about **{fit.r_squared:.0%}** of the variation in the gap. "
            "Dots above the dashed line live longer than predicted. This is an association across countries, "
            "not proof that one causes the other."
        )
        missing = len(filtered) - len(plotted)
        if missing:
            st.caption(f"{missing} selected countries have no {factor['short']} value for {year} and are not plotted; they remain in the download.")

    _sources()
    _download(filtered, "factors_download", f"gap_factors_{year}.csv")
