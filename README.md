# Does getting richer mean living longer?

A Streamlit dashboard on the World Bank's World Development Indicators (subject: `world_development_indicators`).

**Question.** As countries get richer, do their people live longer, and is the gap between a country's actual and expected life expectancy linked more to government health spending or to air pollution?

**Audience.** Government policy analysts in health, finance and environment ministries, and academic researchers in development economics and public health.

**Pages.** `app.py` sets up navigation across six pages:

| Page | File | Content |
|---|---|---|
| Overview | `home.py` | The question and the two ideas it tests, where the dashboard sits among the WDI data themes, the indicators used, cards linking to each question, and data access |
| 1. Income and life expectancy | `sections/1_income_and_life_expectancy.py` | View `income_health`: life expectancy against GDP per capita (log scale) with one fitted line per year, R² and years gained per doubling of income (with 95% CI); then change within each country 2000–2023 (income growth vs life-expectancy gain) |
| 2. Longer or shorter than predicted | `sections/2_longer_or_shorter.py` | View `residual_ranking`: each country's gap (actual minus predicted life expectancy), largest gaps chart and full table, regional summary; then a world map of the gap and the distribution of gaps by region or income group |
| 3. Health spending or air pollution? | `sections/3_spending_or_pollution.py` | View `gap_factors`: the gap against government health expenditure (% of GDP) or PM2.5 exposure, with Pearson's r by year and by income group |
| Conclusion | `sections/4_conclusion.py` | What the data show and do not show, implications for the audience, methods and limitations |
| Country spotlight | `sections/5_country_spotlight.py` | Tool: one country against its ten closest income peers (gap, rank, health spending, PM2.5, gap over time) |

The explanations on pages 1–3 only describe what the data show; every number in them is computed from the loaded data. The theme icons and the card pictures were made for this dashboard (the card pictures are miniature charts drawn from the data).

## Data

Four WDI indicators and the World Bank country list, retrieved from the Indicators API on 2026-10-12 (WDI last updated 2026-10-08), licensed CC BY 4.0:

| Code | Indicator | Original source |
|---|---|---|
| NY.GDP.PCAP.PP.KD | GDP per capita, PPP (constant 2021 international $) | ICP, Eurostat-OECD PPP Programme, national accounts, IMF WEO |
| SP.DYN.LE00.IN | Life expectancy at birth, total (years) | UN World Population Prospects, national statistical offices, Eurostat |
| SH.XPD.GHED.GD.ZS | Domestic general government health expenditure (% of GDP) | WHO Global Health Expenditure Database |
| EN.ATM.PM25.MC.M3 | PM2.5 air pollution, mean annual exposure (µg/m³) | IHME Global Burden of Disease Study 2023 |

The raw responses are kept in `data/raw/` as a snapshot. The exact URLs are listed in `dashboard.yml`.

The map on page 2 uses Natural Earth 1:110m country outlines (public domain), packaged by world-atlas 2.0.2 (ISC licence), with ISO numeric ids recoded to the World Bank's ISO alpha-3 codes using world-countries 5.1.0 (ODbL). The result is bundled as `data/geo/countries-110m-iso3.json` so the map works offline; `src/build_map.py` documents how it was made.

- `data/processed.csv`: every year 2000–2023 (4,721 country-years, 199 economies).
- `data/sample.csv`: the offline sample, every economy for 2000, 2005, 2010, 2015, 2020 and 2023 (1,178 rows). Because each year keeps all economies, each year's fitted line matches the full data.

## Run

Python 3.11 is required. The direct dependencies are pinned in `pyproject.toml` and `requirements.txt`.

```bash
pip install -r requirements.txt
streamlit run app.py                      # uses data/processed.csv
DASHBOARD_SAMPLE_MODE=1 streamlit run app.py   # offline sample
```

## Pipeline

```bash
python -m src.data --acquire              # download the five raw JSON files to data/raw/
python -m src.data                        # transform + validate -> data/processed.csv
python -m src.data --refresh-sample       # same, and rewrite data/sample.csv
DASHBOARD_SAMPLE_MODE=1 python -m src.data   # offline: rebuild processed.csv from the sample
python -m src.data --validate             # validate data/processed.csv
```

Without `--acquire`, existing raw files are reused. If the API cannot be reached, open each URL in a browser and save it under `data/raw/` with the indicator code as the file name (for example `data/raw/SP.DYN.LE00.IN.json`) and `countries.json`.

`src/data.py` holds acquisition, transformation and validation. `src/analysis.py` holds the line fit used by both the pipeline and the views. Presentation lives in `src/views.py` (the three assessed views), `src/stories.py` (data-only page summaries, change over time and the conclusion), `src/overview.py` (overview page parts), `src/spotlight.py` (country spotlight), `src/geography.py` (map and distribution), `src/theme.py` (page banners) and `src/loading.py` (cached data loading).

## Method and limitations

For each year, ordinary least squares fits life expectancy on ln(GDP per capita, PPP) across countries, unweighted. The residual (gap) is actual minus predicted life expectancy. Change over time regresses each country's change in life expectancy on its change in ln(GDP per capita) between the first and last year. Confidence intervals are approximate 95% intervals (slope ± 1.96 SE; Fisher z for r) and do not include the error in modelled estimates. These are cross-country associations, not causal effects. Many values are modelled, notably life expectancy (UN WPP) and PM2.5 (GBD). Income groups use the FY2027 classification for every year. The dashboard's "Methods and limitations" section has the full notes.
