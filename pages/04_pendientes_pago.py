import streamlit as st
from modulos.comun import init_db, header
from modulos.pendientes_pago import pendientes_pago

st.set_page_config(page_title="Pendientes Pago", layout="wide")
init_db()
header()
pendientes_pago()
