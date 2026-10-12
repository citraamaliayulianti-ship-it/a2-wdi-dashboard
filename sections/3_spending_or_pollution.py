"""Question 3: is the gap linked to government health spending or to air pollution?"""

import streamlit as st

from src.loading import get_data
from src.stories import PAGE_CONCLUSION, PAGE_GAPS, factors_summary, page_nav
from src.views import render_gap_factors


data = get_data()

st.caption("QUESTION 3 OF 3")
with st.container(key="gap_factors"):
    render_gap_factors(
        data,
        intro=(
            "**What this page shows.** Each dot is one country: its gap from page 2 (up) against either government "
            "health spending or PM2.5 air pollution (across). If idea 1 holds, dots should rise to the right for "
            "health spending; if idea 2 holds, they should fall to the right for air pollution. The grey line shows "
            "the overall direction."
        ),
    )
factors_summary(data)
page_nav(previous=(PAGE_GAPS, "Longer or shorter than predicted"), following=(PAGE_CONCLUSION, "Conclusion"))
