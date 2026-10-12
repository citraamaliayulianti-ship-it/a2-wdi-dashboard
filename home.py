"""Overview page: the question, the two ideas it tests, the data and how to explore it."""

import streamlit as st

from src.loading import AUDIENCE, QUESTION, TITLE, get_data
from src.overview import about_the_data, access_data, data_themes, introduction, question_cards


data = get_data()

st.title(TITLE)
st.write(f"**Question:** {QUESTION}")
st.caption(f"Audience: {AUDIENCE}")

introduction()
st.divider()
data_themes()
st.divider()
about_the_data(data)
st.divider()
question_cards(data)
st.divider()
access_data(data)
