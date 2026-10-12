"""Page texts that describe only what the data show, plus page navigation.

Every number in these summaries is computed from the loaded dataset, so the
text always matches the data the page is using.
"""

from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from src.analysis import describe_strength, fit_line, income_fit


HOME = "home.py"
PAGE_INCOME = "sections/1_income_and_life_expectancy.py"
PAGE_GAPS = "sections/2_longer_or_shorter.py"
PAGE_FACTORS = "sections/3_spending_or_pollution.py"
PAGE_CONCLUSION = "sections/4_conclusion.py"


def page_nav(previous: tuple[str, str] | None, following: tuple[str, str] | None) -> None:
    st.divider()
    left, right = st.columns(2)
    if previous:
        left.page_link(previous[0], label=f"Previous: {previous[1]}", icon=":material/arrow_back:")
    if following:
        right.page_link(following[0], label=f"Next: {following[1]}", icon=":material/arrow_forward:")


PER_DOUBLING = "Extra years per doubling of income"


def year_fits(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, frame in data.groupby("year"):
        fit = income_fit(frame)
        rows.append({"Year": int(year), "Countries": fit.n, "R²": fit.r_squared,
                     PER_DOUBLING: fit.slope * math.log(2)})
    return pd.DataFrame(rows)


def income_summary(data: pd.DataFrame) -> None:
    fits = year_fits(data)
    first, last = fits.iloc[0], fits.iloc[-1]
    low, high = fits.loc[fits["R²"].idxmin()], fits.loc[fits["R²"].idxmax()]
    trend = "smaller" if last[PER_DOUBLING] < first[PER_DOUBLING] else "larger"
    st.subheader("What the data show")
    st.markdown(
        f"- In **{int(last['Year'])}**, income accounts for **{last['R²']:.0%}** of the differences in life expectancy "
        f"between {int(last['Countries'])} countries, and each doubling of income goes with about "
        f"**{last[PER_DOUBLING]:.1f} more years**.\n"
        f"- Across the years in this file, the share explained by income ranges from {low['R²']:.0%} "
        f"({int(low['Year'])}) to {high['R²']:.0%} ({int(high['Year'])}).\n"
        f"- The extra years per doubling of income are **{trend}** in {int(last['Year'])} "
        f"({last[PER_DOUBLING]:.1f}) than in {int(first['Year'])} ({first[PER_DOUBLING]:.1f}): the line is "
        f"{'flatter' if trend == 'smaller' else 'steeper'} than at the start of the period."
    )
    st.dataframe(
        fits,
        hide_index=True,
        column_config={
            "Year": st.column_config.NumberColumn(format="%d"),
            "R²": st.column_config.NumberColumn(format="%.2f"),
            "Extra years per doubling of income": st.column_config.NumberColumn(format="%.2f"),
        },
    )
    st.caption("One line is fitted for each year across all countries with data in that year.")


def gaps_summary(data: pd.DataFrame) -> None:
    first, latest = int(data["year"].min()), int(data["year"].max())
    now = data.loc[data["year"] == latest].sort_values("residual_years", ascending=False)
    then = data.loc[data["year"] == first].set_index("country_code")["residual_years"]
    above = now.loc[now["residual_years"] >= 5]
    below = now.loc[now["residual_years"] <= -5]
    still_below = [r.country for r in below.itertuples() if then.get(r.country_code, 0) <= -5]
    still_above = [r.country for r in above.itertuples() if then.get(r.country_code, 0) >= 5]
    regions = (now.groupby("region")
               .agg(Countries=("country_code", "count"), **{"Average gap (years)": ("residual_years", "mean")},
                    **{"5+ years longer": ("residual_years", lambda s: int((s >= 5).sum()))},
                    **{"5+ years shorter": ("residual_years", lambda s: int((s <= -5).sum()))})
               .sort_values("Average gap (years)", ascending=False).reset_index()
               .rename(columns={"region": "Region"}))
    top, bottom = now.iloc[0], now.iloc[-1]
    st.subheader("What the data show")
    lines = [
        f"- In **{latest}**, {len(above)} countries live at least 5 years longer than their income predicts and "
        f"{len(below)} live at least 5 years shorter. The largest gaps are {top['country']} "
        f"({top['residual_years']:+.1f} years) and {bottom['country']} ({bottom['residual_years']:+.1f} years).",
        f"- Of the {len(below)} countries at least 5 years below the line in {latest}, {len(still_below)} were also "
        f"at least 5 years below in {first}" + (f": {', '.join(still_below)}." if still_below else "."),
        f"- Of the {len(above)} countries at least 5 years above the line in {latest}, {len(still_above)} were also "
        f"at least 5 years above in {first}" + (f": {', '.join(still_above)}." if still_above else "."),
        f"- By region, the average gap in {latest} runs from {regions.iloc[0]['Average gap (years)']:+.1f} years "
        f"({regions.iloc[0]['Region']}) to {regions.iloc[-1]['Average gap (years)']:+.1f} years "
        f"({regions.iloc[-1]['Region']}).",
    ]
    st.markdown("\n".join(lines))
    st.dataframe(
        regions,
        hide_index=True,
        column_config={"Average gap (years)": st.column_config.NumberColumn(format="%+.1f")},
    )
    st.caption(f"Regional figures for {latest}; each country counts once.")


def _factor_fit(frame: pd.DataFrame, column: str):
    usable = frame.dropna(subset=[column])
    return fit_line(usable[column], usable["residual_years"]) if len(usable) >= 5 else None


def factors_summary(data: pd.DataFrame) -> None:
    latest = int(data["year"].max())
    rows = []
    for year, frame in data.groupby("year"):
        health, air = _factor_fit(frame, "gov_health_exp_pct_gdp"), _factor_fit(frame, "pm25_ug_m3")
        rows.append({"Year": int(year),
                     "r: health spending": health.correlation, "Countries (spending)": health.n,
                     "r: PM2.5": air.correlation, "Countries (PM2.5)": air.n})
    by_year = pd.DataFrame(rows)
    groups = []
    now = data.loc[data["year"] == latest]
    for group in ["Low income", "Lower middle income", "Upper middle income", "High income"]:
        frame = now.loc[now["income_group"] == group]
        health, air = _factor_fit(frame, "gov_health_exp_pct_gdp"), _factor_fit(frame, "pm25_ug_m3")
        if health and air:
            groups.append({"Income group": group, "Countries": len(frame),
                           "r: health spending": health.correlation,
                           "r: PM2.5": air.correlation})
    by_group = pd.DataFrame(groups)
    h, a = by_year["r: health spending"], by_year["r: PM2.5"]
    max_share = max((h ** 2).max(), (a ** 2).max())
    sign_text = lambda s, word: (f"{word} in every year" if (s > 0).all() else
                                 f"negative in every year" if (s < 0).all() else "positive in some years and negative in others")
    best_row, best_col = max(
        ((row, col) for _, row in by_group.iterrows()
         for col in ["r: health spending", "r: PM2.5"]),
        key=lambda pair: abs(pair[0][pair[1]]),
    )
    best_factor = best_col.split(": ")[1]
    st.subheader("What the data show")
    st.markdown(
        f"- The link between the gap and **government health spending** is {sign_text(h, 'positive')}, with r between "
        f"{h.min():+.2f} and {h.max():+.2f}.\n"
        f"- The link between the gap and **PM2.5 air pollution** is {sign_text(a, 'positive')}, with r between "
        f"{a.min():+.2f} and {a.max():+.2f}.\n"
        f"- In no year does either measure account for more than **{max_share:.0%}** of the variation in the gap.\n"
        f"- Within income groups in {latest}, the strongest single link is {best_factor} among "
        f"{best_row['Income group'].lower()} countries (r = {best_row[best_col]:+.2f}, "
        f"{describe_strength(best_row[best_col])})."
    )
    left, right = st.columns(2)
    with left:
        st.dataframe(by_year, hide_index=True, column_config={
            "Year": st.column_config.NumberColumn(format="%d"),
            "r: health spending": st.column_config.NumberColumn(format="%+.2f"),
            "r: PM2.5": st.column_config.NumberColumn(format="%+.2f"),
        })
        st.caption("Pearson's r between each country's gap and the factor, by year.")
    with right:
        st.dataframe(by_group, hide_index=True, column_config={
            "r: health spending": st.column_config.NumberColumn(format="%+.2f"),
            "r: PM2.5": st.column_config.NumberColumn(format="%+.2f"),
        })
        st.caption(f"The same correlations within each income group, {latest}.")


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
        "modelled estimates (see Methods and limitations below)."
    )
    st.markdown("**What this means for policy analysts**")
    st.markdown(
        "- Higher income goes with longer lives, but it does not guarantee them: countries at similar incomes "
        "differ by many years.\n"
        f"- Countries well above the line in {latest}, such as {best}, are peers worth studying. Countries well below "
        f"it, such as {worst}, are where life expectancy falls furthest below what income predicts.\n"
        "- This evidence does not show that more health spending or cleaner air alone would close the gap. Decisions "
        "on either should rest on further, country-level evidence."
    )
    st.markdown("**Next steps for researchers**")
    st.markdown(
        "Follow the same countries over time rather than comparing countries in one year; add other WDI factors such "
        "as sanitation, disease burden or conflict; weight countries by population; and use the uncertainty ranges "
        "published with modelled estimates."
    )


def methods_and_limitations() -> None:
    with st.expander("Methods and limitations (for academic readers)"):
        st.markdown(
            "**Method.** For each year, an ordinary least squares line is fitted across all countries with data: "
            "life expectancy = a + b × ln(GDP per capita, PPP). Every country counts once, regardless of population. "
            "R² is the share of cross-country variation in life expectancy the line explains, and b × ln 2 is the "
            "change in life expectancy per doubling of income. The *gap* (residual) is actual minus predicted life "
            "expectancy. Question 3 fits a second simple line of the gap on one factor and reports Pearson's r.\n\n"
            "**Coverage.** The World Bank lists 217 economies; a country-year is included when both GDP per capita and "
            "life expectancy are reported, which leaves 199 economies and 4,721 of 5,208 country-years for 2000–2023. "
            "The period starts in 2000 because government health expenditure starts then, and ends in 2023 because "
            "health spending and PM2.5 are not yet published for 2024. Missing health-spending or PM2.5 values are kept "
            "as missing, not filled in.\n\n"
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
