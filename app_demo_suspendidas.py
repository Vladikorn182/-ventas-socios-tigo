import streamlit as st
from suspendidas import mostrar_suspendidas

st.set_page_config(page_title="Suspendidas", page_icon="🚨", layout="wide")
mostrar_suspendidas()
