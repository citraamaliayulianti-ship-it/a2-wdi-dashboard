"""Overview page: the question, the two ideas it tests, the data and how to explore it."""

import streamlit as st

from src.loading import QUESTION, TITLE, get_data
from src.overview import about_the_data, access_data, data_themes, hero, introduction, question_cards


data = get_data()

hero(data, TITLE, QUESTION)
introduction()
st.divider()
data_themes()
st.divider()
about_the_data(data)
st.divider()
question_cards(data)
st.divider()
access_data(data)
