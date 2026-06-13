import streamlit as st
from modulos.comun import init_db, header

st.set_page_config(page_title="Sistema Tigo Ventas", layout="wide")
init_db()
header()

st.subheader("🏠 Inicio")
st.write("Sistema separado por páginas para evitar que una actualización afecte a otra.")

st.info("Usa el menú lateral para ingresar a cada módulo.")

st.markdown("""
### Módulos disponibles
- 📊 Dashboard y Ranking
- 📱 WhatsApp ventas objetivo y crosselling
- 📋 Pendientes de Instalación
- 💳 Pendientes de Pago
- 🚨 Suspendidas
- 🎯 Objetivos y Configuración
""")
