"""Conclusion: what the evidence shows, and what it does not."""

import streamlit as st

from src.loading import QUESTION, get_data
from src.stories import PAGE_FACTORS, PAGE_SPOTLIGHT, conclusion, methods_and_limitations, page_nav
from src.theme import BANNER, banner, latest, pattern_income


data = get_data()

banner("Conclusion", "What the evidence shows, and what it does not", QUESTION, BANNER["conclusion"],
       pattern_income(latest(data)))
conclusion(data)
methods_and_limitations()
page_nav(previous=(PAGE_FACTORS, "Health spending or air pollution?"), following=(PAGE_SPOTLIGHT, "Country spotlight"))
