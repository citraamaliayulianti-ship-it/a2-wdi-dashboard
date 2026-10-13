"""Country spotlight: one country compared with the ten countries closest to it in income.

Everything shown is computed from the dashboard dataset; the text describes
where the country stands, not why.
"""

from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src.views import INK, LONGER, SHORTER, _style

PEERS = 10
DEFAULT_COUNTRY = "Indonesia"


def income_peers(year_data: pd.DataFrame, code: str, k: int = PEERS) -> pd.DataFrame:
    """The k countries with the closest ln(GDP per capita) to `code` in the same year."""
    target = float(np.log(year_data.loc[year_data["country_code"] == code, "gdp_pc_ppp"].iloc[0]))
    others = year_data.loc[year_data["country_code"] != code].copy()
    others["distance"] = (np.log(others["gdp_pc_ppp"]) - target).abs()
    return others.nsmallest(k, "distance").drop(columns="distance")


def _compare(value: float, reference: float) -> str:
    if pd.isna(value) or pd.isna(reference):
        return "not available"
    return "above" if value > reference else "below" if value < reference else "equal to"


def render_spotlight(data: pd.DataFrame) -> None:
    years = sorted((int(y) for y in data["year"].unique()), reverse=True)
    left, right = st.columns([3, 1])
    with left:
        countries = sorted(data["country"].unique())
        default = countries.index(DEFAULT_COUNTRY) if DEFAULT_COUNTRY in countries else 0
        country = st.selectbox("Country", countries, index=default, key="spotlight_country")
    with right:
        year = st.selectbox("Year", years, index=0, key="spotlight_year")

    year_data = data.loc[data["year"] == year]
    row = year_data.loc[year_data["country"] == country]
    if row.empty:
        st.info(f"{country} has no income and life expectancy data for {year}. Choose another year.")
        return
    row = row.iloc[0]
    peers = income_peers(year_data, row["country_code"])
    group = pd.concat([row.to_frame().T, peers]).reset_index(drop=True)
    for column in ["gdp_pc_ppp", "life_expectancy", "predicted_life_expectancy", "residual_years",
                   "gov_health_exp_pct_gdp", "pm25_ug_m3"]:
        group[column] = pd.to_numeric(group[column])
    rank = int((year_data["residual_years"] > row["residual_years"]).sum()) + 1
    peer_gap = peers["residual_years"].median()
    health, health_peers = row["gov_health_exp_pct_gdp"], peers["gov_health_exp_pct_gdp"].median()
    air, air_peers = row["pm25_ug_m3"], peers["pm25_ug_m3"].median()

    a, b, c, d = st.columns(4)
    a.metric("Life expectancy", f"{row['life_expectancy']:.1f} years")
    b.metric("Predicted from income", f"{row['predicted_life_expectancy']:.1f} years")
    c.metric("Gap", f"{row['residual_years']:+.1f} years")
    d.metric("Gap rank (largest first)", f"{rank} of {len(year_data)}")

    direction = "longer" if row["residual_years"] >= 0 else "shorter"
    more_peers = int((peers["residual_years"] > row["residual_years"]).sum())
    st.markdown(
        f"**What the data show.** In {year}, people in **{country}** are expected to live "
        f"{row['life_expectancy']:.1f} years, {abs(row['residual_years']):.1f} years {direction} than the line predicts "
        f"for its income (GDP per capita {row['gdp_pc_ppp']:,.0f} international dollars, PPP). Among its "
        f"{PEERS} closest income peers, {more_peers} have a larger gap and the median peer gap is "
        f"{peer_gap:+.1f} years. Its government health spending "
        + (f"({health:.1f}% of GDP) is {_compare(health, health_peers)} the peer median ({health_peers:.1f}%)"
           if pd.notna(health) else "is not reported for this year")
        + ", and its PM2.5 exposure "
        + (f"({air:.1f} µg/m³) is {_compare(air, air_peers)} the peer median ({air_peers:.1f} µg/m³)."
           if pd.notna(air) else "is not reported for this year.")
    )

    chart_data = group.assign(
        role=lambda f: np.where(f["country"] == country, "Selected country", "Income peer"),
        direction=lambda f: np.where(f["residual_years"] >= 0, "Longer than predicted", "Shorter than predicted"),
    ).sort_values("residual_years", ascending=False)
    order = chart_data["country"].tolist()
    bars = alt.Chart(chart_data).mark_bar(cornerRadiusEnd=4, height=16).encode(
        x=alt.X("residual_years:Q", title="Gap between actual and predicted life expectancy (years)"),
        y=alt.Y("country:N", sort=order, title=None, axis=alt.Axis(labelOverlap=False, labelLimit=220)),
        color=alt.Color("direction:N", title=None,
                        scale=alt.Scale(domain=["Longer than predicted", "Shorter than predicted"], range=[LONGER, SHORTER])),
        opacity=alt.condition(alt.datum.role == "Selected country", alt.value(1.0), alt.value(0.45)),
        stroke=alt.condition(alt.datum.role == "Selected country", alt.value(INK), alt.value(None)),
        tooltip=[
            alt.Tooltip("country:N", title="Country"),
            alt.Tooltip("gdp_pc_ppp:Q", title="GDP per capita (PPP $)", format=",.0f"),
            alt.Tooltip("life_expectancy:Q", title="Life expectancy (years)", format=".1f"),
            alt.Tooltip("residual_years:Q", title="Gap (years)", format="+.1f"),
        ],
    )
    zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=INK).encode(x="x:Q")
    st.markdown(f"**{country} and its {PEERS} closest income peers, {year}**")
    st.altair_chart(_style((bars + zero).properties(height=alt.Step(26))), width="stretch")
    st.caption("The selected country is shown in full colour; peers are faded.")

    history = data.loc[data["country"] == country, ["year", "life_expectancy", "predicted_life_expectancy"]]
    long = history.melt("year", var_name="series", value_name="years").replace(
        {"life_expectancy": "Actual life expectancy", "predicted_life_expectancy": "Predicted from income"})
    lines = alt.Chart(long).mark_line(point=alt.OverlayMarkDef(size=40), strokeWidth=2).encode(
        x=alt.X("year:O", title="Year"),
        y=alt.Y("years:Q", title="Years", scale=alt.Scale(zero=False)),
        color=alt.Color("series:N", title=None,
                        scale=alt.Scale(domain=["Actual life expectancy", "Predicted from income"], range=[LONGER, INK])),
        strokeDash=alt.StrokeDash("series:N", legend=None,
                                  scale=alt.Scale(domain=["Actual life expectancy", "Predicted from income"],
                                                  range=[[1, 0], [5, 4]])),
        tooltip=[alt.Tooltip("year:O", title="Year"), alt.Tooltip("series:N", title="Series"),
                 alt.Tooltip("years:Q", title="Years", format=".1f")],
    )
    st.markdown(f"**{country} over time: actual and predicted life expectancy**")
    st.altair_chart(_style(lines.properties(height=300)), width="stretch")
    st.caption("The predicted line uses each year's fit across all countries, so the space between the two lines is "
               "the country's gap in that year.")

    table = group[["country", "region", "income_group", "gdp_pc_ppp", "life_expectancy", "residual_years",
                   "gov_health_exp_pct_gdp", "pm25_ug_m3"]].copy()
    for column in ["gov_health_exp_pct_gdp", "pm25_ug_m3"]:
        table[column] = table[column].map(lambda v: "not reported" if pd.isna(v) else f"{v:.1f}")
    st.dataframe(table, hide_index=True, column_config={
        "country": "Country", "region": "Region", "income_group": "Income group",
        "gdp_pc_ppp": st.column_config.NumberColumn("GDP per capita (PPP $)", format="%,.0f"),
        "life_expectancy": st.column_config.NumberColumn("Life expectancy (years)", format="%.1f"),
        "residual_years": st.column_config.NumberColumn("Gap (years)", format="%+.1f"),
        "gov_health_exp_pct_gdp": st.column_config.TextColumn("Gov. health spending (% of GDP)"),
        "pm25_ug_m3": st.column_config.TextColumn("PM2.5 (µg/m³)"),
    })
    st.caption(f"Peers are the {PEERS} countries with the closest GDP per capita (on a log scale) in {year}. "
               "Comparing with peers shows where a country stands, not why.")
    st.download_button(
        "Download this comparison (CSV)",
        data=group.to_csv(index=False).encode("utf-8"),
        file_name=f"spotlight_{row['country_code']}_{year}.csv",
        mime="text/csv",
        key="spotlight_download",
    )
