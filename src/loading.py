"""Load the dashboard dataset once and share it across pages."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample.csv"
PROCESSED = ROOT / "data" / "processed.csv"

TITLE = "Does getting richer mean living longer?"
QUESTION = (
    "As countries get richer, do their people live longer, and is the gap between a country's actual and "
    "expected life expectancy linked more to government health spending or to air pollution?"
)
AUDIENCE = (
    "Government policy analysts in health, finance and environment ministries, and academic researchers in "
    "development economics and public health"
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
    """The bundled sample in offline mode (or before the pipeline has run), otherwise the processed file."""
    sample_mode = os.getenv("DASHBOARD_SAMPLE_MODE", "0") == "1"
    if sample_mode or not PROCESSED.exists():
        return SAMPLE
    return PROCESSED


def get_data() -> pd.DataFrame:
    return load_data(str(data_path()))
