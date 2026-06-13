import streamlit as st
from modulos.comun import init_db, header
from modulos.ventas import cargar_grossadd
from modulos.whatsapp import whatsapp

st.set_page_config(page_title="WhatsApp Ventas", layout="wide")
init_db()
header()

df, resumen, codigo_minimo = cargar_grossadd()
whatsapp(df, resumen)
