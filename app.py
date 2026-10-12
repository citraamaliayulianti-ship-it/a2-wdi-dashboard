from __future__ import annotations

import math
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from src.analysis import describe_strength, fit_line, income_fit
from src.views import render_gap_factors, render_income_health, render_residual_ranking


ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT / "data" / "sample.csv"
PROCESSED = ROOT / "data" / "processed.csv"
TITLE = "Does getting richer mean living longer?"
QUESTION = (
    "As countries get richer, do their people live longer, and is the gap between a country's actual and "
    "expected life expectancy linked more to government health spending or to air pollution?"
)


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    frame = pd.read_csv(
        path,
        dtype={"country_code": str, "country": str, "region": str, "income_group": str},
        keep_default_na=False,
        na_values=[""],
        parse_dates=["date"],
    )
    return frame.sort_values(["year", "country"]).reset_index(drop=True)


def data_path() -> Path:
    sample_mode = os.getenv("DASHBOARD_SAMPLE_MODE", "0") == "1"
    if sample_mode or not PROCESSED.exists():
        return SAMPLE
    return PROCESSED


def introduction(data: pd.DataFrame) -> None:
    st.subheader("Why this question matters")
    st.markdown(
        "If a country gets richer, should its people expect to live longer? There are two competing ideas about "
        "how economic growth reaches people's health, and they point policy in different directions."
    )
    left, right = st.columns(2)
    with left.container(border=True):
        st.markdown(
            "**Idea 1: growth pays for health.** Richer countries can afford better health services, so people "
            "live longer.  \n*Tested with:* domestic general government health expenditure (% of GDP)."
        )
    with right.container(border=True):
        st.markdown(
            "**Idea 2: growth costs health.** Growth can bring industry, traffic and dirtier air, which can "
            "shorten lives.  \n*Tested with:* PM2.5 air pollution exposure (µg/m³)."
        )
    st.markdown(
        "Both ideas could be partly true at the same time. This dashboard cannot prove either one; it checks whether "
        "the pattern across countries is **consistent** with them."
    )
    st.subheader("How the dashboard answers it")
    st.markdown(
        "1. **View 1 sets the baseline:** how much longer people live, on average, in richer countries.\n"
        "2. **View 2 finds the exceptions:** countries whose people live longer or shorter than their income "
        "predicts. This difference is called the *gap*: a gap of +5 means five years longer than in countries "
        "with similar incomes.\n"
        "3. **View 3 tests the two ideas:** does the gap go with government health spending (idea 1) or with air "
        "pollution (idea 2)?"
    )
    years = sorted(int(y) for y in data["year"].unique())
    st.caption(
        f"What the data cover: {data['country_code'].nunique()} economies from the World Bank's World Development "
        f"Indicators, {years[0]}–{years[-1]} ({len(years)} years in this file), one row per country and year with "
        "income, life expectancy, government health spending and PM2.5 air pollution."
    )


def conclusion(data: pd.DataFrame) -> None:
    first, latest = int(data["year"].min()), int(data["year"].max())
    now = data.loc[data["year"] == latest]
    fit_now, fit_first = income_fit(now), income_fit(data.loc[data["year"] == first])
    health = fit_line(now["gov_health_exp_pct_gdp"], now["residual_years"])
    air = fit_line(now["pm25_ug_m3"], now["residual_years"])
    ranked = now.sort_values("residual_years", ascending=False)
    best = ", ".join(ranked["country"].head(3))
    worst = ", ".join(ranked["country"].tail(3).iloc[::-1])
    sign = lambda r: "positive" if r > 0 else "negative"

    st.header("Conclusion: what the evidence shows, and what it does not")
    st.markdown(f"**What the data show for {latest}**")
    st.markdown(
        f"1. **Richer countries do live longer.** Income accounts for {fit_now.r_squared:.0%} of the differences in "
        f"life expectancy between {fit_now.n} countries. Each doubling of income goes with about "
        f"{fit_now.slope * math.log(2):.1f} more years of life, a flatter slope than in {first} "
        f"({fit_first.slope * math.log(2):.1f} years per doubling).\n"
        f"2. **But income is not the whole story.** Countries with similar incomes range from "
        f"{ranked['residual_years'].iloc[0]:+.1f} to {ranked['residual_years'].iloc[-1]:+.1f} years around the life "
        f"expectancy their income predicts. {int((now['residual_years'] >= 5).sum())} countries live at least 5 years "
        f"longer than predicted and {int((now['residual_years'] <= -5).sum())} at least 5 years shorter.\n"
        f"3. **Both ideas get only weak support.** Government health spending has a {describe_strength(health.correlation)} "
        f"{sign(health.correlation)} link with the gap (r = {health.correlation:+.2f}) and PM2.5 air pollution a "
        f"{describe_strength(air.correlation)} {sign(air.correlation)} link (r = {air.correlation:+.2f}). The directions "
        f"match ideas 1 and 2, but each explains only about {health.r_squared:.1%} and {air.r_squared:.1%} of the gap."
    )
    st.markdown("**What the data cannot tell us**")
    st.markdown(
        "- **Cause and effect.** These are associations between national averages. Healthier populations may also "
        "earn more, so the arrow can run both ways.\n"
        "- **Why the exceptions differ.** Factors such as conflict, disease outbreaks or how health money is spent are "
        "not in this dataset.\n"
        "- **Exact values for every country.** Many figures, including most life expectancy and all PM2.5 values, are "
        "modelled estimates (see Methods and limitations)."
    )
    st.markdown("**What this means for policy analysts**")
    st.markdown(
        "- Income growth goes with longer lives, but it does not guarantee them: countries at similar incomes differ "
        "by many years.\n"
        f"- Countries well above the line in {latest}, such as {best}, are peers worth studying. Countries well below "
        f"it, such as {worst}, are places where income is not turning into longer lives.\n"
        "- This evidence does not show that more health spending or cleaner air alone would close the gap. Decisions "
        "on either should rest on further, country-level evidence."
    )
    st.markdown("**Next steps for researchers**")
    st.markdown(
        "Follow the same countries over time rather than comparing countries in one year; add other WDI factors such "
        "as sanitation, disease burden or conflict; weight countries by population; and use the uncertainty ranges "
        "published with modelled estimates."
    )


st.set_page_config(page_title="Income and life expectancy", layout="wide")
st.title(TITLE)
st.write(f"**Question:** {QUESTION}")
st.caption(
    "Audience: policy analysts in government health, finance and environment ministries (primary), and academic "
    "researchers in development economics and public health (see Methods and limitations)."
)
data = load_data(str(data_path()))
introduction(data)

st.divider()
with st.container(key="income_health"):
    render_income_health(data)

st.divider()
with st.container(key="residual_ranking"):
    render_residual_ranking(data)

st.divider()
with st.container(key="gap_factors"):
    render_gap_factors(data)

st.divider()
conclusion(data)

st.divider()
with st.expander("Methods and limitations (for academic readers)"):
    st.markdown(
        "**Method.** For each year, an ordinary least squares line is fitted across all countries with data: "
        "life expectancy = a + b × ln(GDP per capita, PPP). Every country counts once, regardless of population. "
        "R² is the share of cross-country variation in life expectancy the line explains, and b × ln 2 is the "
        "change in life expectancy per doubling of income. The *gap* (residual) is actual minus predicted life "
        "expectancy. View 3 fits a second simple line of the gap on one factor and reports Pearson's r.\n\n"
        "**Coverage.** The World Bank lists 217 economies; a country-year is included when both GDP per capita and "
        "life expectancy are reported, which leaves 199 economies and 4,721 of 5,208 country-years for 2000–2023. The period starts in 2000 because "
        "government health expenditure starts then, and ends in 2023 because health spending and PM2.5 are not yet "
        "published for 2024. Missing health-spending or PM2.5 values are kept as missing, not filled in.\n\n"
        "**Limitations.**\n"
        "- These are associations between national averages, not causal effects. Health may also raise income "
        "(reverse causality), and no other factors are held constant.\n"
        "- Many values are modelled rather than measured. Life expectancy comes largely from UN World Population "
        "Prospects estimates, especially where death registration is incomplete; extreme values (for example "
        "14.7 years for the Central African Republic in 2009) reflect modelled crisis mortality and should be read "
        "with care. PM2.5 exposure is modelled by the Global Burden of Disease study from satellite and ground data.\n"
        "- PPP-based GDP is designed for international comparison, but the subject's data catalogue notes that WDI "
        "national accounts are not built for precise level comparisons; Penn World Table or Maddison data could be "
        "used as a robustness check.\n"
        "- Regions and income groups use the World Bank FY2027 classification (released July 2026) for every year, "
        "so a country's group in earlier years may differ from its historical classification.\n"
        "- PM2.5 captures only one environmental pressure; other environmental costs of growth are not measured here.\n\n"
        "**Offline sample.** `data/sample.csv` keeps every economy for 2000, 2005, 2010, 2015, 2020 and 2023, so "
        "each year's line is identical to the full dataset; `data/processed.csv` from the live pipeline covers every year."
    )

with st.expander("Indicator definitions and original sources"):
    st.markdown(
        "All series come from the World Bank's **World Development Indicators** (Indicators API, retrieved "
        "2026-10-12; database last updated 2026-10-08), licensed CC BY 4.0. The World Bank republishes them from "
        "these original sources:\n\n"
        "- **NY.GDP.PCAP.PP.KD**, GDP per capita, PPP (constant 2021 international dollars): GDP divided by "
        "population, converted with purchasing power parities. Original sources: World Bank International "
        "Comparison Program, Eurostat-OECD PPP Programme, World Bank and OECD national accounts, IMF World Economic "
        "Outlook.\n"
        "- **SP.DYN.LE00.IN**, Life expectancy at birth (years): the number of years a newborn infant would live if "
        "prevailing patterns of mortality at the time of its birth were to stay the same throughout its life. "
        "Original sources: UN Population Division (World Population Prospects), national statistical offices, "
        "Eurostat.\n"
        "- **SH.XPD.GHED.GD.ZS**, Domestic general government health expenditure (% of GDP): public expenditure on "
        "health from domestic sources as a share of GDP. Original source: WHO Global Health Expenditure Database.\n"
        "- **EN.ATM.PM25.MC.M3**, PM2.5 air pollution, mean annual exposure (micrograms per cubic metre): "
        "population-weighted exposure to fine particulate matter. Original source: IHME Global Burden of Disease "
        "Study 2023 exposure estimates."
    )
    st.markdown(
        "[World Bank Indicators API](https://api.worldbank.org/v2/country/all/indicator/SP.DYN.LE00.IN?format=json"
        "&per_page=20000&date=1990:2024) · [Country list with regions and income groups]"
        "(https://api.worldbank.org/v2/country?format=json&per_page=400)"
    )
