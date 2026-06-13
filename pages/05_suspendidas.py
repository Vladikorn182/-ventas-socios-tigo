import streamlit as st
from modulos.comun import init_db, header
from modulos.suspendidas import suspendidas

st.set_page_config(page_title="Suspendidas", layout="wide")
init_db()
header()
suspendidas()
