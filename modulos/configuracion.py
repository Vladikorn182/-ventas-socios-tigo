import streamlit as st
from .comun import obtener_codigo_minimo, guardar_codigo_minimo

def configuracion():
    st.subheader("⚙️ Configuración")
    st.write("Define desde qué código una venta cuenta al objetivo.")
    st.write("Los códigos menores se mostrarán como crosselling y no sumarán al cumplimiento.")
    codigo_actual = obtener_codigo_minimo()
    nuevo = st.number_input("Código mínimo para contar al objetivo", min_value=0, value=int(codigo_actual), step=1)
    if st.button("💾 Guardar configuración"):
        guardar_codigo_minimo(nuevo)
        st.success("Configuración guardada. Presiona F5 para recalcular.")
