import streamlit as st
from modulos.comun import init_db, header
from modulos.pendientes_instalacion import pendientes_instalacion

st.set_page_config(page_title="Pendientes Instalación", layout="wide")
init_db()
header()
pendientes_instalacion()
