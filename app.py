"""Entry point: page navigation for the dashboard.

Each page is its own file. The overview introduces the question and the data;
pages 1-3 each answer one part of the question; page 4 draws the conclusion.
"""

import streamlit as st

from src.stories import HOME, PAGE_CONCLUSION, PAGE_FACTORS, PAGE_GAPS, PAGE_INCOME


st.set_page_config(page_title="Does getting richer mean living longer?", layout="wide")

navigation = st.navigation(
    [
        st.Page(HOME, title="Overview", icon=":material/home:", default=True),
        st.Page(PAGE_INCOME, title="1. Income and life expectancy", url_path="income"),
        st.Page(PAGE_GAPS, title="2. Longer or shorter than predicted", url_path="gaps"),
        st.Page(PAGE_FACTORS, title="3. Health spending or air pollution?", url_path="factors"),
        st.Page(PAGE_CONCLUSION, title="Conclusion", url_path="conclusion"),
    ],
    position="top",
)
navigation.run()
