"""Building blocks of the overview page: introduction, data themes, question cards and data access.

The theme icons are simple line drawings made for this dashboard, and the
card pictures are miniature charts drawn from the dashboard's own data.
"""

from __future__ import annotations

import html
import math

import numpy as np
import pandas as pd
import streamlit as st

from src.analysis import fit_line, income_fit
from src.stories import PAGE_CONCLUSION, PAGE_FACTORS, PAGE_GAPS, PAGE_INCOME, PAGE_SPOTLIGHT
from src.views import LONGER, SHORTER, INK, GRID

API_URLS = {
    "GDP per capita, PPP (NY.GDP.PCAP.PP.KD)": "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.PP.KD?format=json&per_page=20000&date=1990:2024",
    "Life expectancy at birth (SP.DYN.LE00.IN)": "https://api.worldbank.org/v2/country/all/indicator/SP.DYN.LE00.IN?format=json&per_page=20000&date=1990:2024",
    "Government health expenditure (SH.XPD.GHED.GD.ZS)": "https://api.worldbank.org/v2/country/all/indicator/SH.XPD.GHED.GD.ZS?format=json&per_page=20000&date=1990:2024",
    "PM2.5 exposure (EN.ATM.PM25.MC.M3)": "https://api.worldbank.org/v2/country/all/indicator/EN.ATM.PM25.MC.M3?format=json&per_page=20000&date=1990:2024",
    "Country list with regions and income groups": "https://api.worldbank.org/v2/country?format=json&per_page=400",
}

# ---------------------------------------------------------------- hero banner

def _hero_pattern(now: pd.DataFrame) -> str:
    """Decorative backdrop: every country in the latest year, life expectancy against income."""
    width, height = 560, 320
    lo, hi = math.log10(500), math.log10(200000)
    xs = _scale(np.log10(now["gdp_pc_ppp"]), lo, hi, 20, width - 20)
    ys = _scale(now["life_expectancy"], 45, 90, height - 20, 20)
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#86b6ef" fill-opacity="0.45"/>' for x, y in zip(xs, ys))
    fit = income_fit(now)
    ends = _scale(fit.intercept + fit.slope * np.log(np.array([500.0, 200000.0])), 45, 90, height - 20, 20)
    line = (f'<line x1="20" y1="{ends[0]:.1f}" x2="{width - 20}" y2="{ends[1]:.1f}" stroke="#ffffff" '
            f'stroke-opacity="0.55" stroke-width="2.5"/>')
    return (f'<svg viewBox="0 0 {width} {height}" aria-hidden="true" style="position:absolute;right:-10px;bottom:-10px;'
            f'width:min(56%,560px);height:auto;opacity:0.9">{dots}{line}</svg>')


def hero(data: pd.DataFrame, title: str, question: str, audience: str) -> None:
    """Opening banner: what the dashboard asks, for whom, and where to start."""
    years = sorted(int(y) for y in data["year"].unique())
    latest = data.loc[data["year"] == years[-1]]
    kicker = (f"World Development Indicators · {years[0]}–{years[-1]} · "
              f"{data['country_code'].nunique()} economies")
    button = ("display:inline-block;padding:10px 18px;border-radius:8px;font-weight:600;font-size:15px;"
              "text-decoration:none;margin:0 10px 10px 0;")
    st.markdown(
        f'<div style="position:relative;overflow:hidden;border-radius:16px;background:#0d366b;'
        f'padding:44px 40px 34px;margin-bottom:8px">'
        f'{_hero_pattern(latest)}'
        f'<div style="position:relative;max-width:720px">'
        f'<div style="font-size:13px;letter-spacing:0.08em;text-transform:uppercase;color:#b7d3f6">'
        f'{html.escape(kicker)}</div>'
        f'<h1 style="color:#ffffff;font-size:2.6rem;line-height:1.15;margin:10px 0 14px;padding:0">'
        f'{html.escape(title)}</h1>'
        f'<p style="color:#e6eefb;font-size:1.1rem;line-height:1.55;margin:0 0 16px">{html.escape(question)}</p>'
        f'<div style="margin:0 0 22px"><span style="display:inline-block;background:rgba(255,255,255,0.14);'
        f'color:#ffffff;border-radius:999px;padding:5px 14px;font-size:14px;line-height:1.45">'
        f'For: {html.escape(audience[0].lower() + audience[1:])}</span></div>'
        f'<a href="income" target="_self" style="{button}background:#ffffff;color:#0d366b">Start with question 1 →</a>'
        f'<a href="#about-the-data" target="_self" style="{button}border:1.5px solid #ffffff;color:#ffffff">About the data</a>'
        f'<a href="#access-the-data" target="_self" style="{button}border:1.5px solid #ffffff;color:#ffffff">Access the data</a>'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    st.caption("Background pattern: every country's life expectancy against its income in "
               f"{years[-1]}, drawn from this dashboard's data.")


# ---------------------------------------------------------------- introduction

def introduction() -> None:
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

# ---------------------------------------------------------------- data themes

_ICONS = {
    "Poverty and inequality": '<path d="M24 9v29M15 38h18M9 15h30"/><path d="M9 15l-5 11h10zM39 15l-5 11h10z"/>',
    "People": '<circle cx="17" cy="16" r="5"/><circle cx="31" cy="16" r="5"/>'
              '<path d="M8 37c0-6 4-10 9-10s9 4 9 10M22 37c0-6 4-10 9-10s9 4 9 10"/>',
    "Environment": '<path d="M10 38C10 21 21 10 38 10c0 17-11 28-28 28z"/><path d="M10 38L27 21"/>',
    "Economy": '<path d="M7 40h34"/><path d="M12 40V30M20 40V25M28 40V27M36 40V18"/><path d="M10 20l9-7 8 4 12-8"/>',
    "States and markets": '<path d="M6 18L24 8l18 10z"/><path d="M11 22v14M19 22v14M29 22v14M37 22v14M6 40h36"/>',
    "Global links": '<circle cx="24" cy="24" r="16"/><ellipse cx="24" cy="24" rx="7" ry="16"/><path d="M8 24h32M11 16h26M11 32h26"/>',
}
_THEMES = [
    ("Poverty and inequality", "poverty, prosperity, income distribution", None),
    ("People", "population, health, education, gender", "Life expectancy · government health spending"),
    ("Environment", "climate, energy, land, water, air quality", "PM2.5 air pollution"),
    ("Economy", "growth, economic structure, income", "GDP per capita (PPP)"),
    ("States and markets", "business, public sector, infrastructure", None),
    ("Global links", "trade, debt, aid, migration", None),
]


def data_themes() -> None:
    st.subheader("Where this dashboard sits in the WDI")
    st.markdown(
        "The World Bank groups WDI indicators into six data themes. This dashboard draws on three of them, "
        "highlighted below; the other three are outside its scope."
    )
    cards = []
    for name, topics, used in _THEMES:
        on = used is not None
        colour = LONGER if on else "#a3a29c"
        badge = (f'<div style="margin-top:8px;font-size:12px;color:{LONGER};font-weight:600">Used here</div>'
                 f'<div style="font-size:12px;color:#31333f">{html.escape(used)}</div>') if on else \
                '<div style="margin-top:8px;font-size:12px;color:#8a8984">Not used</div>'
        cards.append(
            f'<div style="border:1px solid {LONGER if on else GRID};background:{"#eef4fc" if on else "#fafaf8"};'
            f'border-radius:10px;padding:14px 12px;text-align:center;opacity:{1 if on else 0.75}">'
            f'<svg viewBox="0 0 48 48" width="44" height="44" fill="none" stroke="{colour}" stroke-width="2.2" '
            f'stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="{html.escape(name)} icon">'
            f'{_ICONS[name]}</svg>'
            f'<div style="font-weight:600;margin-top:6px;color:{"#31333f" if on else "#6b6a65"}">{html.escape(name)}</div>'
            f'<div style="font-size:12px;color:#6b6a65">{html.escape(topics)}</div>{badge}</div>'
        )
    st.markdown(
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px">'
        + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )
    st.caption("Theme names follow the World Bank's WDI website; the icons are drawn for this dashboard.")

# ---------------------------------------------------------------- about the data

def indicator_details() -> None:
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


def about_the_data(data: pd.DataFrame) -> None:
    years = sorted(int(y) for y in data["year"].unique())
    st.subheader("About the data")
    st.markdown(
        "All figures come from the World Bank's [World Development Indicators]"
        "(https://datatopics.worldbank.org/world-development-indicators/) (WDI). The World Bank describes WDI as its "
        "main collection of development statistics that can be compared across countries: about 1,400 indicators for "
        "217 economies and more than 40 country groups. The World Bank compiles most of these series from other "
        "organisations, such as UN agencies, WHO and national statistical offices, so each indicator below names its "
        "original source. This dashboard uses four of them:"
    )
    st.markdown(
        "| Indicator (WDI code) | WDI theme | What it measures | Original source |\n"
        "|---|---|---|---|\n"
        "| GDP per capita, PPP (NY.GDP.PCAP.PP.KD) | Economy | Average income per person, adjusted for price "
        "differences between countries, in constant 2021 international dollars | International Comparison Program, "
        "national accounts, IMF |\n"
        "| Life expectancy at birth (SP.DYN.LE00.IN) | People | Years a newborn would live if current death rates "
        "stayed the same | UN World Population Prospects, national statistical offices |\n"
        "| Domestic general government health expenditure, % of GDP (SH.XPD.GHED.GD.ZS) | People | How much of the "
        "economy the government spends on health from its own resources | WHO Global Health Expenditure Database |\n"
        "| PM2.5 air pollution, mean annual exposure (EN.ATM.PM25.MC.M3) | Environment | Average fine-particle air "
        "pollution people breathe, in µg/m³ | IHME Global Burden of Disease study |"
    )
    st.caption(
        f"Coverage in this file: {data['country_code'].nunique()} economies with both income and life expectancy data, "
        f"{years[0]}–{years[-1]} ({len(years)} years). Retrieved from the World Bank Indicators API on 2026-10-12. "
        "Many values, including most life expectancy and all PM2.5 figures, are modelled estimates rather than direct "
        "measurements; see Methods and limitations on the Conclusion page."
    )
    with st.expander("Full indicator definitions and original sources"):
        indicator_details()

# ---------------------------------------------------------------- question cards

_W, _H, _P = 320, 170, 14
_FRAME = (f'<svg viewBox="0 0 {_W} {_H}" width="100%" role="img" aria-label="{{label}}" '
          f'style="background:#f6f6f3;border-radius:8px;display:block">{{body}}</svg>')


def _scale(values, low, high, out_low, out_high):
    return out_low + (np.clip(values, low, high) - low) / (high - low) * (out_high - out_low)


def _thumb_income(now: pd.DataFrame) -> str:
    fit = income_fit(now)
    lo, hi = math.log10(500), math.log10(200000)
    xs = _scale(np.log10(now["gdp_pc_ppp"]), lo, hi, _P, _W - _P)
    ys = _scale(now["life_expectancy"], 45, 90, _H - _P, _P)
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.4" fill="{LONGER}" fill-opacity="0.55"/>' for x, y in zip(xs, ys))
    ends = np.array([500.0, 200000.0])
    line_y = _scale(fit.intercept + fit.slope * np.log(ends), 45, 90, _H - _P, _P)
    line = f'<line x1="{_P}" y1="{line_y[0]:.1f}" x2="{_W - _P}" y2="{line_y[1]:.1f}" stroke="{INK}" stroke-width="2"/>'
    return _FRAME.format(label="Miniature scatter of life expectancy against income", body=dots + line)


def _thumb_gaps(now: pd.DataFrame) -> str:
    ranked = now.sort_values("residual_years", ascending=False)
    rows = pd.concat([ranked.head(5), ranked.tail(5)])
    extent = rows["residual_years"].abs().max()
    zero = _W * 0.62
    span = (_W - _P - zero, zero - _P)
    parts = [f'<line x1="{zero:.1f}" y1="8" x2="{zero:.1f}" y2="{_H - 8}" stroke="{INK}" stroke-width="1"/>']
    for i, value in enumerate(rows["residual_years"]):
        y = 12 + i * 15
        width = abs(value) / extent * (span[0] if value >= 0 else span[1])
        x = zero if value >= 0 else zero - width
        parts.append(f'<rect x="{x:.1f}" y="{y}" width="{width:.1f}" height="10" rx="3" '
                     f'fill="{LONGER if value >= 0 else SHORTER}"/>')
    return _FRAME.format(label="Miniature bar chart of the largest gaps", body="".join(parts))


def _thumb_factors(now: pd.DataFrame) -> str:
    usable = now.dropna(subset=["gov_health_exp_pct_gdp"])
    fit = fit_line(usable["gov_health_exp_pct_gdp"], usable["residual_years"])
    xmax = float(usable["gov_health_exp_pct_gdp"].quantile(0.98))
    xs = _scale(usable["gov_health_exp_pct_gdp"], 0, xmax, _P, _W - _P)
    ys = _scale(usable["residual_years"], -16, 10, _H - _P, _P)
    zero_y = float(_scale(np.array([0.0]), -16, 10, _H - _P, _P)[0])
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.4" fill="{LONGER}" fill-opacity="0.55"/>' for x, y in zip(xs, ys))
    zero = f'<line x1="{_P}" y1="{zero_y:.1f}" x2="{_W - _P}" y2="{zero_y:.1f}" stroke="{INK}" stroke-dasharray="4 4" stroke-width="1"/>'
    line_y = _scale(fit.intercept + fit.slope * np.array([0.0, xmax]), -16, 10, _H - _P, _P)
    line = f'<line x1="{_P}" y1="{line_y[0]:.1f}" x2="{_W - _P}" y2="{line_y[1]:.1f}" stroke="{INK}" stroke-width="2"/>'
    return _FRAME.format(label="Miniature scatter of the gap against health spending", body=zero + dots + line)


def _thumb_conclusion(now: pd.DataFrame) -> str:
    share = income_fit(now).r_squared
    body = (f'<text x="{_W / 2}" y="86" text-anchor="middle" font-size="54" font-weight="700" fill="{LONGER}">'
            f'{share:.0%}</text>'
            f'<text x="{_W / 2}" y="118" text-anchor="middle" font-size="17" fill="{INK}">of the differences in life '
            f'expectancy</text><text x="{_W / 2}" y="140" text-anchor="middle" font-size="17" fill="{INK}">go with '
            f'income. What about the rest?</text>')
    return _FRAME.format(label="Headline share explained by income", body=body)


def question_cards(data: pd.DataFrame) -> None:
    latest = int(data["year"].max())
    now = data.loc[data["year"] == latest]
    st.subheader("Explore the questions")
    st.markdown("Each question has its own page with an interactive chart, a short reading of what the data show, "
                "and a download of the selected data. Pictures are miniature versions of each page's chart for "
                f"{latest}.")
    cards = [
        (PAGE_INCOME, "QUESTION 1", "How closely does life expectancy track income?", _thumb_income(now)),
        (PAGE_GAPS, "QUESTION 2", "Which countries live longer or shorter than their income predicts?", _thumb_gaps(now)),
        (PAGE_FACTORS, "QUESTION 3", "Is the gap linked to government health spending or to air pollution?",
         _thumb_factors(now)),
        (PAGE_CONCLUSION, "CONCLUSION", "What the evidence shows, and what it does not", _thumb_conclusion(now)),
    ]
    columns = st.columns(4)
    for column, (page, kicker, title, picture) in zip(columns, cards):
        with column.container(border=True):
            st.markdown(picture, unsafe_allow_html=True)
            st.caption(kicker)
            st.markdown(f"**{title}**")
            st.page_link(page, label="Open page", icon=":material/arrow_forward:")
    with st.container(border=True):
        left, right = st.columns([3, 1], vertical_alignment="center")
        left.markdown("**Looking at one country?** The Country spotlight compares any country's life expectancy with "
                      "what its income predicts and with its ten closest income peers.")
        right.page_link(PAGE_SPOTLIGHT, label="Open the Country spotlight", icon=":material/travel_explore:")

# ---------------------------------------------------------------- data access

def access_data(data: pd.DataFrame) -> None:
    st.subheader("Access the data")
    left, middle, right = st.columns(3)
    with left:
        st.markdown("#### :blue[Download this dashboard's data]")
        st.markdown(
            "Each question page has a download button for the countries and year you select. The complete table "
            f"behind this dashboard ({len(data):,} country-years, {data.shape[1]} columns, including the predicted "
            "life expectancy and gap for every country) is available here."
        )
        st.download_button(
            "Download the full dataset (CSV)",
            data=data.to_csv(index=False).encode("utf-8"),
            file_name="wdi_income_life_expectancy.csv",
            mime="text/csv",
            key="full_dataset_download",
        )
    with middle:
        st.markdown("#### :green[World Bank Indicators API]")
        st.markdown(
            "The four indicators and the country list were requested from the World Bank Indicators API on "
            "12 October 2026. The pipeline (`src/data.py`) repeats the same requests with `python -m src.data "
            "--acquire`."
        )
        st.markdown("\n".join(f"- [{name}]({url})" for name, url in API_URLS.items()))
    with right:
        st.markdown("#### :orange[Explore the WDI further]")
        st.markdown(
            "The World Bank's own tools cover all WDI indicators, not only the four used here. DataBank lets you "
            "build tables and charts in the browser, and the WDI website offers bulk Excel and CSV downloads."
        )
        st.markdown(
            "- [WDI on DataBank](https://databank.worldbank.org/source/world-development-indicators)\n"
            "- [WDI website and bulk downloads](https://datatopics.worldbank.org/world-development-indicators/)\n"
            "- [Indicators API documentation](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392)"
        )
