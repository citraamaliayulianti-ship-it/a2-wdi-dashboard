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


def key_findings(data: pd.DataFrame) -> None:
    first, latest = int(data["year"].min()), int(data["year"].max())
    now = data.loc[data["year"] == latest]
    fit_now, fit_first = income_fit(now), income_fit(data.loc[data["year"] == first])
    health = now.dropna(subset=["gov_health_exp_pct_gdp"])
    air = now.dropna(subset=["pm25_ug_m3"])
    r_health = fit_line(health["gov_health_exp_pct_gdp"], health["residual_years"]).correlation
    r_air = fit_line(air["pm25_ug_m3"], air["residual_years"]).correlation
    sign = lambda r: "positive" if r > 0 else "negative"
    st.subheader(f"Key findings for {latest}")
    st.markdown(
        f"1. **Income is the strongest single guide.** It accounts for {fit_now.r_squared:.0%} of the differences "
        f"in life expectancy between {fit_now.n} countries. Each doubling of income goes with about "
        f"{fit_now.slope * math.log(2):.1f} more years of life, a flatter line than in {first} "
        f"({fit_first.slope * math.log(2):.1f} years per doubling).\n"
        f"2. **Countries with similar incomes still differ a lot.** {int((now['residual_years'] >= 5).sum())} countries "
        f"live at least 5 years longer than their income predicts and {int((now['residual_years'] <= -5).sum())} live "
        "at least 5 years shorter (view 2).\n"
        f"3. **Neither proposed explanation accounts for much of that gap.** Government health spending has a "
        f"{describe_strength(r_health)} {sign(r_health)} link with the gap (r = {r_health:+.2f}) and PM2.5 air "
        f"pollution a {describe_strength(r_air)} {sign(r_air)} link (r = {r_air:+.2f}). Both point the way the question "
        "anticipated, but most of the gap is not explained by either measure; other causes would need separate evidence."
    )
    st.caption(
        "For policy analysts: the over-performers in view 2 are peers that achieve longer lives at similar incomes and "
        "are worth closer study. Spending and air-quality figures alone do not explain their advantage."
    )


st.set_page_config(page_title="Income and life expectancy", layout="wide")
st.title(TITLE)
st.write(f"**Question:** {QUESTION}")
st.caption(
    "Audience: policy analysts in government health, finance and environment ministries (primary), and academic "
    "researchers in development economics and public health (see Methods and limitations)."
)
data = load_data(str(data_path()))
years = sorted(int(y) for y in data["year"].unique())
st.write(
    f"**What the data cover:** {data['country_code'].nunique()} economies from the World Bank's World Development "
    f"Indicators, {years[0]}–{years[-1]} ({len(years)} years in this file), one row per country and year with "
    "income, life expectancy, government health spending and PM2.5 air pollution."
)
with st.expander("How to read this dashboard", expanded=False):
    st.markdown(
        "- **View 1** draws one line through all countries: the life expectancy that is typical for each income level.\n"
        "- **View 2** ranks countries by their *gap*: actual life expectancy minus the value the line predicts. "
        "A gap of +5 means people live five years longer than in countries with similar incomes.\n"
        "- **View 3** checks whether the gap goes with government health spending or with air pollution, the two "
        "explanations in the question."
    )

key_findings(data)

with st.container(key="income_health"):
    render_income_health(data)

st.divider()
with st.container(key="residual_ranking"):
    render_residual_ranking(data)

st.divider()
with st.container(key="gap_factors"):
    render_gap_factors(data)

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
