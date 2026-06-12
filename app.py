import streamlit as st

from modulos.comun import init_db, header
from modulos.ventas import cargar_grossadd, dashboard, ranking
from modulos.objetivos import objetivos
from modulos.configuracion import configuracion
from modulos.whatsapp import whatsapp
from modulos.pendientes_instalacion import pendientes_instalacion
from modulos.pendientes_pago import pendientes_pago
from modulos.suspendidas import suspendidas

st.set_page_config(page_title="Dashboard Tigo Ventas", layout="wide")

init_db()
header()

df, resumen, codigo_minimo = cargar_grossadd()

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 Dashboard", "🏆 Ranking", "🎯 Objetivos", "⚙️ Configuración",
    "📱 WhatsApp", "📋 Pendientes Instalación", "💳 Pendientes Pago", "🚨 Suspendidas"
])

with tab1:
    dashboard(resumen)
with tab2:
    ranking(resumen)
with tab3:
    objetivos(df)
with tab4:
    configuracion()
with tab5:
    whatsapp(df, resumen)
with tab6:
    pendientes_instalacion()
with tab7:
    pendientes_pago()
with tab8:
    suspendidas()
