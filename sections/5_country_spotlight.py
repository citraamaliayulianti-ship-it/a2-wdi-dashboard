"""Country spotlight: compare one country with the ten countries closest to it in income."""

import streamlit as st

from src.loading import get_data
from src.spotlight import PEERS, render_spotlight
from src.stories import HOME, PAGE_CONCLUSION, page_nav
from src.theme import BANNER, banner, latest, pattern_gaps


data = get_data()

banner(
    "Tool",
    "Country spotlight",
    f"How does one country's life expectancy compare with what its income predicts, and with its {PEERS} closest "
    "income peers?",
    BANNER["spotlight"],
    pattern_gaps(latest(data)),
)
st.markdown(
    f"Pick a country and a year. Income peers are the {PEERS} countries whose GDP per capita is most similar in that "
    "year. Everything here comes from the same data as pages 1–3."
)
render_spotlight(data)
page_nav(previous=(PAGE_CONCLUSION, "Conclusion"), following=(HOME, "Back to the overview"))
