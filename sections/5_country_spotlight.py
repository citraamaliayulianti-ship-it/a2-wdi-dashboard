"""Country spotlight: compare one country with the ten countries closest to it in income."""

import streamlit as st

from src.loading import get_data
from src.spotlight import PEERS, render_spotlight
from src.stories import HOME, PAGE_CONCLUSION, page_nav


data = get_data()

st.caption("TOOL")
st.header("Country spotlight")
st.markdown(
    f"Pick a country to see how its life expectancy compares with what its income predicts, and with its {PEERS} "
    "closest income peers: the countries whose GDP per capita is most similar in the selected year. Everything here "
    "comes from the same data as pages 1–3."
)
render_spotlight(data)
page_nav(previous=(PAGE_CONCLUSION, "Conclusion"), following=(HOME, "Back to the overview"))
