"""Question 2: which countries live longer or shorter than their income predicts?"""

import streamlit as st

from src.loading import get_data
from src.geography import gap_distribution, gap_map
from src.stories import PAGE_FACTORS, PAGE_INCOME, gaps_summary, page_nav
from src.views import render_residual_ranking


data = get_data()

with st.container(key="residual_ranking"):
    render_residual_ranking(
        data,
        intro=(
            "**What this page shows.** For every country, the *gap* is its actual life expectancy minus the life "
            "expectancy that the line on page 1 predicts for its income. Blue bars are countries whose people live "
            "longer than predicted; red bars live shorter. The table lists every selected country."
        ),
    )
gaps_summary(data)
# The map and distribution follow the year chosen in the view above.
selected_year = int(st.session_state.get("ranking_year", data["year"].max()))
st.divider()
gap_map(data, selected_year)
st.divider()
gap_distribution(data, selected_year)
page_nav(previous=(PAGE_INCOME, "Income and life expectancy"), following=(PAGE_FACTORS, "Health spending or air pollution?"))
