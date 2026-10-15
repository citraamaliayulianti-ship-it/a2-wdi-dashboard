"""Acquire, transform and validate the dashboard's dataset.

One module holds the whole data pipeline so its lineage is inspectable:

* ``acquire()`` downloads five raw JSON files from the World Bank Indicators API
  into ``data/raw/`` (four WDI indicators plus the country list that separates
  real economies from regional and income aggregates).
* ``transform()`` joins them into one country-year table for 2000-2023 and adds
  the per-year income line and each country's residual (see ``src/analysis.py``).
* ``validate()`` stops the pipeline if the table breaks a documented expectation.
* ``main()`` runs the steps. With ``DASHBOARD_SAMPLE_MODE=1`` it works offline:
  it rebuilds ``data/processed.csv`` from the bundled ``data/sample.csv``.

Presentation lives in ``views.py``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pandas as pd

from src.analysis import add_predictions


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
SAMPLE = ROOT / "data" / "sample.csv"
PROCESSED = ROOT / "data" / "processed.csv"

API = "https://api.worldbank.org/v2"
INDICATORS = {
    "NY.GDP.PCAP.PP.KD": "gdp_pc_ppp",
    "SP.DYN.LE00.IN": "life_expectancy",
    "SH.XPD.GHED.GD.ZS": "gov_health_exp_pct_gdp",
    "EN.ATM.PM25.MC.M3": "pm25_ug_m3",
}
INDICATOR_URL = API + "/country/all/indicator/{code}?format=json&per_page=20000&date=1990:2024"
COUNTRIES_URL = API + "/country?format=json&per_page=400"

FIRST_YEAR, LAST_YEAR = 2000, 2023
SAMPLE_YEARS = (2000, 2005, 2010, 2015, 2020, 2023)
MIN_COUNTRIES_PER_YEAR = 150

REGIONS = (
    "East Asia & Pacific",
    "Europe & Central Asia",
    "Latin America & Caribbean",
    "Middle East, North Africa, Afghanistan & Pakistan",
    "North America",
    "South Asia",
    "Sub-Saharan Africa",
)
INCOME_GROUPS = ("Low income", "Lower middle income", "Upper middle income", "High income")

COLUMNS = [
    "date",
    "year",
    "country_code",
    "country",
    "region",
    "income_group",
    "gdp_pc_ppp",
    "life_expectancy",
    "predicted_life_expectancy",
    "residual_years",
    "gov_health_exp_pct_gdp",
    "pm25_ug_m3",
]
STRING_COLUMNS = {"country_code": str, "country": str, "region": str, "income_group": str}
REQUIRED = ["date", "year", "country_code", "country", "region", "income_group",
            "gdp_pc_ppp", "life_expectancy", "predicted_life_expectancy", "residual_years"]
RANGES = {
    "gdp_pc_ppp": (100, 300000),
    "life_expectancy": (10, 100),
    "predicted_life_expectancy": (10, 100),
    "residual_years": (-50, 50),
    "gov_health_exp_pct_gdp": (0, 30),
    "pm25_ug_m3": (0, 200),
}


def read_dataset(path: Path) -> pd.DataFrame:
    """Read a dataset CSV keeping identifiers as text; only empty fields are missing."""
    return pd.read_csv(path, dtype=STRING_COLUMNS, keep_default_na=False, na_values=[""])


def _download(url: str, destination: Path) -> None:
    try:
        with urlopen(url, timeout=60) as response:
            payload = json.load(response)
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        sys.exit(
            f"Could not fetch {url}: {error}. Check your connection, or download the URL "
            f"in a browser and save it as {destination}. To work offline, rerun with "
            "DASHBOARD_SAMPLE_MODE=1 to use the bundled sample."
        )
    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        sys.exit(f"Unexpected response from {url}: {str(payload)[:300]}")
    destination.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    print(f"Wrote {destination}")


def acquire() -> None:
    """Download the raw API responses to data/raw/."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    _download(COUNTRIES_URL, RAW_DIR / "countries.json")
    for code in INDICATORS:
        _download(INDICATOR_URL.format(code=code), RAW_DIR / f"{code}.json")


def _economies(raw_dir: Path) -> pd.DataFrame:
    """Real economies only: the API marks regional and income aggregates as 'Aggregates'."""
    records = json.loads((raw_dir / "countries.json").read_text(encoding="utf-8"))[1]
    rows = [
        {
            "country_code": item["id"],
            "country": item["name"].strip(),
            "region": item["region"]["value"].strip(),
            "income_group": item["incomeLevel"]["value"].strip(),
        }
        for item in records
        if item["region"]["value"].strip() != "Aggregates"
    ]
    return pd.DataFrame(rows)


def _indicator(raw_dir: Path, code: str, economies: set[str]) -> pd.Series:
    """One indicator as a Series indexed by (country_code, year), real economies only."""
    records = json.loads((raw_dir / f"{code}.json").read_text(encoding="utf-8"))[1]
    values = {
        (item["countryiso3code"], int(item["date"])): float(item["value"])
        for item in records
        if item["value"] is not None
        and item["countryiso3code"] in economies
        and FIRST_YEAR <= int(item["date"]) <= LAST_YEAR
    }
    series = pd.Series(values, name=INDICATORS[code], dtype=float)
    series.index = series.index.set_names(["country_code", "year"])
    return series


def transform(raw_dir: Path) -> pd.DataFrame:
    """Join the raw responses into the tidy country-year dataset used by the app."""
    economies = _economies(raw_dir)
    codes = set(economies["country_code"])
    series = {code: _indicator(raw_dir, code, codes) for code in INDICATORS}
    table = pd.concat(series.values(), axis=1).reset_index()
    complete = table["gdp_pc_ppp"].notna() & table["life_expectancy"].notna()
    print(
        f"Coverage rule: kept {int(complete.sum())} country-years with both GDP per capita and "
        f"life expectancy; excluded {int((~complete).sum())} country-years missing either."
    )
    table = table.loc[complete].merge(economies, on="country_code", how="left", validate="many_to_one")
    table["date"] = table["year"].astype(str) + "-12-31"
    table = add_predictions(table)
    return table[COLUMNS]


def finalise(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.strftime("%Y-%m-%d")
    frame["year"] = frame["year"].astype(int)
    return frame.sort_values(["year", "country_code"]).reset_index(drop=True)[COLUMNS]


def validate(frame: pd.DataFrame) -> None:
    """Stop the pipeline if the dataset breaks a documented expectation."""
    missing_columns = set(COLUMNS).difference(frame.columns)
    if missing_columns:
        raise ValueError(f"Missing columns: {sorted(missing_columns)}")
    if len(frame) < 500:
        raise ValueError("Expected at least 500 country-year rows")
    if frame.duplicated(["date", "country_code"]).any():
        raise ValueError("Duplicate date and country keys found")
    if frame[REQUIRED].isna().any().any():
        raise ValueError("Unexpected missing values in a required column")
    dates = pd.to_datetime(frame["date"], errors="raise")
    if not (dates.dt.year == frame["year"]).all() or not (dates.dt.strftime("%m-%d") == "12-31").all():
        raise ValueError("Each date must be 31 December of its year")
    if frame["year"].min() < FIRST_YEAR or frame["year"].max() > LAST_YEAR:
        raise ValueError("Year outside the documented 2000-2023 period")
    if not set(frame["region"]).issubset(REGIONS):
        raise ValueError(f"Unexpected region: {sorted(set(frame['region']) - set(REGIONS))}")
    if not set(frame["income_group"]).issubset(INCOME_GROUPS):
        raise ValueError(f"Unexpected income group: {sorted(set(frame['income_group']) - set(INCOME_GROUPS))}")
    if not frame["country_code"].str.fullmatch(r"[A-Z]{3}").all():
        raise ValueError("Country codes must be three upper-case letters")
    for column, (low, high) in RANGES.items():
        values = pd.to_numeric(frame[column], errors="raise").dropna()
        if not values.between(low, high).all():
            raise ValueError(f"{column} outside its plausible range {low}-{high}")
    gap = frame["life_expectancy"] - frame["predicted_life_expectancy"] - frame["residual_years"]
    if gap.abs().max() > 0.002:
        raise ValueError("Residuals do not equal actual minus predicted life expectancy")
    per_year = frame.groupby("year")["country_code"].nunique()
    if (per_year < MIN_COUNTRIES_PER_YEAR).any():
        raise ValueError(f"Too few countries for a cross-country line in: {per_year[per_year < MIN_COUNTRIES_PER_YEAR].to_dict()}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--acquire", action="store_true", help="Refresh data/raw/ from the World Bank API and stop")
    parser.add_argument("--validate", action="store_true", help="Validate data/processed.csv and stop")
    parser.add_argument("--refresh-sample", action="store_true",
                        help="Live mode only: also rewrite data/sample.csv as the documented subset of years")
    args = parser.parse_args()
    sample_mode = os.getenv("DASHBOARD_SAMPLE_MODE", "0") == "1"
    if args.acquire:
        if sample_mode:
            parser.error("Unset DASHBOARD_SAMPLE_MODE before acquiring live data")
        acquire()
        return
    if args.validate:
        validate(read_dataset(PROCESSED))
        print("Processed data valid")
        return
    if sample_mode:
        if args.refresh_sample:
            parser.error("--refresh-sample needs live mode; unset DASHBOARD_SAMPLE_MODE")
        # The sample keeps every economy for its years, so refitting each year's
        # line on the sample reproduces the published predictions and residuals.
        sample = read_dataset(SAMPLE)
        frame = finalise(add_predictions(sample.drop(columns=["predicted_life_expectancy", "residual_years"])))
    else:
        if not (RAW_DIR / "countries.json").exists() or not all((RAW_DIR / f"{c}.json").exists() for c in INDICATORS):
            acquire()
        frame = finalise(transform(RAW_DIR))
    validate(frame)
    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(PROCESSED, index=False)
    print(f"Validated and wrote {len(frame)} rows to {PROCESSED}")
    if args.refresh_sample:
        subset = frame.loc[frame["year"].isin(SAMPLE_YEARS)]
        validate(subset)
        subset.to_csv(SAMPLE, index=False)
        print(f"Wrote {len(subset)} sample rows ({', '.join(map(str, SAMPLE_YEARS))}) to {SAMPLE}")


if __name__ == "__main__":
    main()
