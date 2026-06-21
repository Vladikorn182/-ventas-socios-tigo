# app_demo_agenda_tecnica.py
# App mínima para probar el módulo Agenda Técnica.

import streamlit as st
from agenda_tecnica import mostrar_agenda_tecnica

st.set_page_config(page_title="Agenda Técnica", layout="wide")
mostrar_agenda_tecnica()
