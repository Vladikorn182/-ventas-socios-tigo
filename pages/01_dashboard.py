import streamlit as st
from modulos.comun import init_db, header
from modulos.ventas import cargar_grossadd, dashboard, ranking

st.set_page_config(page_title="Dashboard", layout="wide")
init_db()
header()

df, resumen, codigo_minimo = cargar_grossadd()
dashboard(resumen)
st.divider()
ranking(resumen)
