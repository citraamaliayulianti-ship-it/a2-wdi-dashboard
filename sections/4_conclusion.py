"""Conclusion: what the evidence shows, and what it does not."""

import streamlit as st

from src.loading import QUESTION, get_data
from src.stories import PAGE_FACTORS, PAGE_SPOTLIGHT, conclusion, methods_and_limitations, page_nav


data = get_data()

st.header("Conclusion: what the evidence shows, and what it does not")
st.write(f"**Question:** {QUESTION}")
conclusion(data)
methods_and_limitations()
page_nav(previous=(PAGE_FACTORS, "Health spending or air pollution?"), following=(PAGE_SPOTLIGHT, "Country spotlight"))
