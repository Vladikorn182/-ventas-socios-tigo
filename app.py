# app.py
# Sistema de Autogestión Tigo - versión integrada
# Módulos incluidos: Agenda Técnica, Pendientes de Instalación con Pago y Suspendidas.

from __future__ import annotations

import streamlit as st

from agenda_tecnica import mostrar_agenda_tecnica
from pendientes_inst import mostrar_pendientes_inst
from suspendidas import mostrar_suspendidas


st.set_page_config(
    page_title="Autogestión Tigo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    .main-card {
        background: linear-gradient(135deg, #063baf 0%, #00a7df 100%);
        padding: 34px;
        border-radius: 22px;
        color: white;
        margin-bottom: 24px;
    }
    .main-card h1 {
        color: white;
        font-size: 44px;
        margin-bottom: 8px;
    }
    .main-card p {
        font-size: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def mostrar_inicio() -> None:
    st.markdown(
        """
        <div class="main-card">
            <h1>📊 Dashboard de Ventas Socios</h1>
            <p>Seguimiento de agenda técnica, pendientes de instalación y suspendidas.</p>
            <hr>
            <p>👷 💻 Desarrollado por Vladimir Cuenca López</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("🏠 Inicio")
    st.write("Selecciona un módulo desde el menú lateral.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("📅 **Agenda Técnica**\n\nInstalaciones programadas del día por EH/socio.")
    with c2:
        st.info("📋 **Pendientes con Pago**\n\nCasos antiguos de +3 días: código, nodo y fecha.")
    with c3:
        st.info("🚨 **Suspendidas**\n\nCasos suspendidos antiguos, clasificación CRM y WhatsApp.")


st.sidebar.title("📌 Menú")
opcion = st.sidebar.radio(
    "Selecciona módulo",
    [
        "Inicio",
        "Agenda Técnica",
        "Pendientes de Instalación",
        "Suspendidas",
    ],
)

try:
    if opcion == "Inicio":
        mostrar_inicio()
    elif opcion == "Agenda Técnica":
        mostrar_agenda_tecnica()
    elif opcion == "Pendientes de Instalación":
        mostrar_pendientes_inst(configurar_pagina=False)
    elif opcion == "Suspendidas":
        mostrar_suspendidas()
except Exception as exc:
    st.error("Ocurrió un error al cargar el módulo seleccionado.")
    st.exception(exc)
