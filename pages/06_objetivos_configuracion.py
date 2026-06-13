import streamlit as st
from modulos.comun import init_db, header
from modulos.objetivos import objetivos
from modulos.configuracion import configuracion

st.set_page_config(page_title="Objetivos y Configuración", layout="wide")
init_db()
header()

st.subheader("🎯 Objetivos")
objetivos(None)
st.divider()
configuracion()
