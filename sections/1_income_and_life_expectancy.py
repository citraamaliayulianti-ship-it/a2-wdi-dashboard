"""Question 1: how closely does life expectancy track income?"""

import streamlit as st

from src.loading import get_data
from src.stories import HOME, PAGE_GAPS, change_over_time, income_summary, page_nav
from src.views import render_income_health


data = get_data()

with st.container(key="income_health"):
    render_income_health(
        data,
        intro=(
            "**What this page shows.** Each dot is one country in the selected year: how rich it is (across) and how "
            "long its people are expected to live (up). The grey line is the life expectancy that is typical for each "
            "income level, fitted across all countries. The closer the dots sit to the line, the more closely life "
            "expectancy follows income."
        ),
    )
income_summary(data)
st.divider()
change_over_time(data)
page_nav(previous=(HOME, "Overview"), following=(PAGE_GAPS, "Longer or shorter than predicted"))
