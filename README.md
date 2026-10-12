# Does getting richer mean living longer?

A Streamlit dashboard on the World Bank's World Development Indicators (subject: `world_development_indicators`).

**Question.** As countries get richer, do their people live longer, and is the gap between a country's actual and expected life expectancy linked more to government health spending or to air pollution?

**Audience.** Policy analysts in government health, finance and environment ministries (primary); academic researchers in development economics and public health (secondary).

**Views.**

1. *How closely does life expectancy track income?* Scatter of life expectancy against GDP per capita (log scale) with one fitted line per year, R² and years gained per doubling of income.
2. *Which countries live longer or shorter than their income predicts?* Ranking of each country's gap (actual minus predicted life expectancy), with a full table.
3. *Is the gap linked to government health spending or to air pollution?* The gap against either domestic general government health expenditure (% of GDP) or PM2.5 exposure, with Pearson's r.

## Data

Four WDI indicators and the World Bank country list, retrieved from the Indicators API on 2026-10-12 (WDI last updated 2026-10-08), licensed CC BY 4.0:

| Code | Indicator | Original source |
|---|---|---|
| NY.GDP.PCAP.PP.KD | GDP per capita, PPP (constant 2021 international $) | ICP, Eurostat-OECD PPP Programme, national accounts, IMF WEO |
| SP.DYN.LE00.IN | Life expectancy at birth, total (years) | UN World Population Prospects, national statistical offices, Eurostat |
| SH.XPD.GHED.GD.ZS | Domestic general government health expenditure (% of GDP) | WHO Global Health Expenditure Database |
| EN.ATM.PM25.MC.M3 | PM2.5 air pollution, mean annual exposure (µg/m³) | IHME Global Burden of Disease Study 2023 |

The raw responses are kept in `data/raw/` as a snapshot. The exact URLs are listed in `dashboard.yml`.

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

`src/data.py` holds acquisition, transformation and validation. `src/analysis.py` holds the line fit used by both the pipeline and the views. `src/views.py` holds the presentation.

## Method and limitations

For each year, ordinary least squares fits life expectancy on ln(GDP per capita, PPP) across countries, unweighted. The residual (gap) is actual minus predicted life expectancy. These are cross-country associations, not causal effects. Many values are modelled, notably life expectancy (UN WPP) and PM2.5 (GBD). Income groups use the FY2027 classification for every year. The dashboard's "Methods and limitations" section has the full notes.
