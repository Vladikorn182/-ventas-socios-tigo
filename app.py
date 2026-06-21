# app.py
# Aplicación independiente: Agenda Técnica / Instalaciones de Hoy

import streamlit as st
from agenda_tecnica_v2 import mostrar_agenda_tecnica

st.set_page_config(
    page_title="Agenda Técnica",
    page_icon="📅",
    layout="wide",
)

mostrar_agenda_tecnica()
