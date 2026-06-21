# app_agenda_tecnica_v2.py
# App independiente para probar Agenda Técnica.

import streamlit as st
from agenda_tecnica_v2 import mostrar_agenda_tecnica

st.set_page_config(page_title="Agenda Técnica", layout="wide")
mostrar_agenda_tecnica()
