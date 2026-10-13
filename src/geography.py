"""Where the gaps are (map) and how they are spread within groups (distribution).

Both follow the year chosen on page 2. The text describes only what the data
show for that year.
"""

from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src.views import GRID, INK, LONGER, SHORTER

ROOT = Path(__file__).resolve().parents[1]
MAP_FILE = ROOT / "data" / "geo" / "countries-110m-iso3.json"
NEUTRAL = "#f3f2ee"
# Lighter steps of the same two hues, so that small gaps still read as clearly blue or red.
LONGER_LIGHT = "#94bdf0"
SHORTER_LIGHT = "#f2a09f"
NO_DATA = "#cfcec8"
CAP = 10


@st.cache_data
def load_outlines(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def gap_map(data: pd.DataFrame, year: int) -> None:
    outlines = load_outlines(str(MAP_FILE))
    drawn = {g["id"] for g in outlines["objects"]["countries"]["geometries"]}
    year_data = data.loc[data["year"] == year, ["country_code", "country", "region", "life_expectancy",
                                                "predicted_life_expectancy", "residual_years"]]
    shown = year_data.loc[year_data["country_code"].isin(drawn)]
    hidden = year_data.loc[~year_data["country_code"].isin(drawn)]
    below = shown.loc[shown["residual_years"] <= -5]
    region_counts = below["region"].value_counts()

    st.subheader(f"Where are the gaps? ({year})")
    # Streamlit turns any data at the top of a chart spec into a table, which would strip the shapes.
    # So the outlines are named (Altair then leaves them where they are) and kept inside their own
    # layer, next to a globe-outline layer with different data (Altair only lifts data that all layers share).
    geo = alt.InlineData(values=outlines, format=alt.DataFormat(type="topojson", feature="countries"),
                         name="country_outlines")
    has_data = "isValid(datum.residual_years)"
    shapes = alt.Chart(geo).mark_geoshape(stroke="white", strokeWidth=0.4).transform_lookup(
        lookup="id",
        from_=alt.LookupData(shown, "country_code", ["country", "residual_years", "life_expectancy",
                                                     "predicted_life_expectancy"]),
    ).transform_calculate(
        name=f"{has_data} ? datum.country : datum.properties.name",
        actual=f"{has_data} ? format(datum.life_expectancy, '.1f') : 'no data'",
        predicted=f"{has_data} ? format(datum.predicted_life_expectancy, '.1f') : 'no data'",
        gap=f"{has_data} ? format(datum.residual_years, '+.1f') : 'no data'",
    ).encode(
        color=alt.when(has_data).then(alt.Color(
            "residual_years:Q",
            title="Gap (years)",
            scale=alt.Scale(domain=[-CAP, -CAP / 2, 0, CAP / 2, CAP],
                            range=[SHORTER, SHORTER_LIGHT, NEUTRAL, LONGER_LIGHT, LONGER], clamp=True,
                            interpolate="lab"),
            legend=alt.Legend(orient="bottom", direction="horizontal", gradientLength=320, titleOrient="left"),
        )).otherwise(alt.value(NO_DATA)),
        tooltip=[
            alt.Tooltip("name:N", title="Country"),
            alt.Tooltip("actual:N", title="Life expectancy (years)"),
            alt.Tooltip("predicted:N", title="Predicted from income"),
            alt.Tooltip("gap:N", title="Gap (years)"),
        ],
    )
    globe = alt.Chart(alt.sphere()).mark_geoshape(fill="#fbfbfa", stroke=GRID, strokeWidth=0.8)
    chart = alt.layer(globe, shapes).project("equalEarth").properties(height=500)
    st.altair_chart(chart.configure_view(strokeWidth=0).configure_legend(labelColor=INK, titleColor=INK),
                    width="stretch")
    top_region = region_counts.index[0] if len(region_counts) else None
    st.markdown(
        f"Blue countries live longer than their income predicts and red countries live shorter; grey means no data. "
        f"Of the {len(below)} mapped countries at least 5 years below the line in {year}, "
        + (f"{int(region_counts.iloc[0])} are in {top_region}." if top_region else "none are shown.")
    )
    st.caption(
        f"Colours are capped at ±{CAP} years so that one extreme value does not wash out the rest. "
        f"{len(hidden)} small countries and territories (mostly islands, such as "
        f"{', '.join(hidden.sort_values('country')['country'].head(3))}) are too small to draw at this scale; they "
        "appear in the chart and table above. Map outlines: Natural Earth 1:110m (public domain), via world-atlas."
    )


def gap_distribution(data: pd.DataFrame, year: int) -> None:
    st.subheader(f"How spread out are the gaps within each group? ({year})")
    group_label = st.radio("Group countries by", ["Region", "Income group"], horizontal=True, key="distribution_group")
    group = "region" if group_label == "Region" else "income_group"
    year_data = data.loc[data["year"] == year, ["country", group, "residual_years"]]
    summary = (year_data.groupby(group)["residual_years"]
               .agg(median="median", p10=lambda s: s.quantile(0.1), p90=lambda s: s.quantile(0.9), n="count")
               .sort_values("median", ascending=False))
    order = summary.index.tolist()
    # Leave room beyond the most extreme countries so the smoothed curves can taper off instead of being cut.
    low = float(np.floor(year_data["residual_years"].min() - 3))
    high = float(np.ceil(year_data["residual_years"].max() + 3))

    density = alt.Chart().transform_density(
        "residual_years", groupby=[group], as_=["gap", "density"], extent=[low, high], steps=160,
    ).mark_area(color=LONGER, opacity=0.35, line={"color": LONGER, "strokeWidth": 1.5}).encode(
        x=alt.X("gap:Q", title="Gap between actual and predicted life expectancy (years)",
                scale=alt.Scale(domain=[low, high], nice=False)),
        y=alt.Y("density:Q", axis=None, title=None),
    )
    zero = alt.Chart().transform_aggregate(n="count()", groupby=[group]).mark_rule(
        color=INK, strokeDash=[4, 4]).encode(x=alt.datum(0))
    median = alt.Chart().transform_aggregate(median="median(residual_years)", groupby=[group]).mark_rule(
        color=INK, strokeWidth=2.5).encode(x="median:Q", tooltip=[alt.Tooltip("median:Q", title="Median gap", format="+.1f")])
    ticks = alt.Chart().mark_tick(color=INK, opacity=0.5, thickness=1, size=10).encode(
        x="residual_years:Q", tooltip=[alt.Tooltip("country:N", title="Country"),
                                       alt.Tooltip("residual_years:Q", title="Gap (years)", format="+.1f")])
    chart = alt.layer(density, zero, median, ticks, data=year_data).properties(width=640, height=54).facet(
        row=alt.Row(f"{group}:N", sort=order, title=None,
                    header=alt.Header(labelAngle=0, labelAlign="left", labelColor=INK, labelFontSize=12, labelLimit=260)),
    ).resolve_scale(y="independent").configure_facet(spacing=6).configure_view(strokeWidth=0).configure_axis(
        gridColor=GRID, domainColor=GRID, tickColor=GRID, labelColor=INK, titleColor=INK, titleFontWeight="normal")
    st.altair_chart(chart, width="content")

    widest = (summary["p90"] - summary["p10"]).idxmax()
    narrowest = (summary["p90"] - summary["p10"]).idxmin()
    st.markdown(
        f"Each curve shows how the gaps of one {group_label.lower()}'s countries are spread; the solid line is the "
        f"median, the dashed line is zero and each small tick is a country. In {year}, the median gap is highest in "
        f"**{order[0]}** ({summary.loc[order[0], 'median']:+.1f} years) and lowest in **{order[-1]}** "
        f"({summary.loc[order[-1], 'median']:+.1f} years). The middle 80% of countries spans "
        f"{summary.loc[widest, 'p90'] - summary.loc[widest, 'p10']:.1f} years in {widest} but only "
        f"{summary.loc[narrowest, 'p90'] - summary.loc[narrowest, 'p10']:.1f} years in {narrowest}."
    )
    st.caption("Curves are smoothed (kernel density) and drawn on their own vertical scale, so compare their shape "
               "and position rather than their height. Groups with few countries, such as North America (3), give "
               "rough curves.")
