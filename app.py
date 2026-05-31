import streamlit as st
import pandas as pd
import sqlite3
import urllib.parse

st.set_page_config(page_title="Dashboard de Ventas", layout="wide")
st.title("📊 Dashboard de Ventas Socios")

conn = sqlite3.connect("ventas.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS objetivos (
    EH TEXT PRIMARY KEY,
    NOMBRE TEXT,
    OBJETIVO INTEGER
)
""")
conn.commit()

archivo = st.file_uploader("📤 Sube el archivo GrossAdd", type=["csv"])

df = None
resumen = None

if archivo:
    try:
        df = pd.read_csv(archivo, sep=None, engine="python", encoding="latin1")
        st.success(f"Archivo cargado: {len(df)} registros")

        resumen = (
            df.groupby(["VENDEDOR_EH", "VENDEDOR_NOMBRE"])
            .agg(Ventas=("CLIENTE_NRO", "count"))
            .reset_index()
        )

        objetivos = pd.read_sql("SELECT * FROM objetivos", conn)

        if objetivos.empty:
            objetivos = pd.DataFrame(columns=["EH", "NOMBRE", "OBJETIVO"])

        resumen["VENDEDOR_EH"] = resumen["VENDEDOR_EH"].astype(str)
        objetivos["EH"] = objetivos["EH"].astype(str)

        resumen = resumen.merge(
            objetivos[["EH", "OBJETIVO"]],
            left_on="VENDEDOR_EH",
            right_on="EH",
            how="left"
        )

        resumen["OBJETIVO"] = resumen["OBJETIVO"].fillna(0).astype(int)

        resumen["CUMPLIMIENTO"] = resumen.apply(
            lambda x: round((x["Ventas"] / x["OBJETIVO"]) * 100, 1)
            if x["OBJETIVO"] > 0 else 0,
            axis=1
        )

        resumen["FALTAN"] = (
            resumen["OBJETIVO"] - resumen["Ventas"]
        ).clip(lower=0).astype(int)

        resumen = resumen.sort_values("CUMPLIMIENTO", ascending=False)

    except Exception as e:
        st.error(f"Error al procesar archivo: {e}")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard",
    "🏆 Ranking",
    "🎯 Objetivos",
    "📱 WhatsApp"
])

with tab1:
    st.subheader("📊 Resumen General")

    if resumen is not None:
        total_ventas = resumen["Ventas"].sum()
        total_objetivo = resumen["OBJETIVO"].sum()
        socios_activos = len(resumen)
        cumplimiento_total = round((total_ventas / total_objetivo) * 100, 1) if total_objetivo > 0 else 0
        faltan_total = max(total_objetivo - total_ventas, 0)

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("✅ Ventas", int(total_ventas))
        c2.metric("🎯 Objetivo", int(total_objetivo))
        c3.metric("📈 Cumplimiento", f"{cumplimiento_total}%")
        c4.metric("⏳ Faltan", int(faltan_total))

        st.progress(min(cumplimiento_total, 100) / 100)

        st.subheader("👥 Avance por Socio")

        for _, row in resumen.iterrows():
            with st.container(border=True):
                col1, col2, col3 = st.columns([4, 2, 2])

                with col1:
                    st.markdown(f"### 👤 {row['VENDEDOR_NOMBRE']}")
                    st.write(f"EH: {row['VENDEDOR_EH']}")

                with col2:
                    st.metric("Ventas", int(row["Ventas"]))
                    st.metric("Objetivo", int(row["OBJETIVO"]))

                with col3:
                    st.metric("Cumplimiento", f"{row['CUMPLIMIENTO']}%")
                    st.metric("Faltan", int(row["FALTAN"]))

                st.progress(min(float(row["CUMPLIMIENTO"]), 100) / 100)
    else:
        st.info("Primero sube el archivo GrossAdd.")

with tab2:
    st.subheader("🏆 Ranking de Ventas")

    if resumen is not None:
        st.dataframe(
            resumen[
                [
                    "VENDEDOR_EH",
                    "VENDEDOR_NOMBRE",
                    "Ventas",
                    "OBJETIVO",
                    "CUMPLIMIENTO",
                    "FALTAN"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Primero sube el archivo GrossAdd.")

with tab3:
    st.subheader("🎯 Administración de Objetivos")

    if df is not None:
        socios = (
            df[["VENDEDOR_EH", "VENDEDOR_NOMBRE"]]
            .drop_duplicates()
            .sort_values("VENDEDOR_NOMBRE")
        )

        with st.form("form_objetivos"):
            nuevos_objetivos = []

            for _, row in socios.iterrows():
                eh = str(row["VENDEDOR_EH"])
                nombre = row["VENDEDOR_NOMBRE"]

                actual = cursor.execute(
                    "SELECT OBJETIVO FROM objetivos WHERE EH=?",
                    (eh,)
                ).fetchone()

                valor_actual = int(actual[0]) if actual else 0

                col1, col2, col3 = st.columns([2, 5, 2])

                with col1:
                    st.write(eh)

                with col2:
                    st.write(nombre)

                with col3:
                    objetivo = st.number_input(
                        "Objetivo",
                        min_value=0,
                        value=valor_actual,
                        key=f"obj_{eh}",
                        label_visibility="collapsed"
                    )

                nuevos_objetivos.append((eh, nombre, int(objetivo)))

            guardar = st.form_submit_button("💾 Guardar objetivos")

            if guardar:
                for eh, nombre, objetivo in nuevos_objetivos:
                    cursor.execute("""
                        INSERT INTO objetivos (EH, NOMBRE, OBJETIVO)
                        VALUES (?, ?, ?)
                        ON CONFLICT(EH) DO UPDATE SET
                            NOMBRE=excluded.NOMBRE,
                            OBJETIVO=excluded.OBJETIVO
                    """, (eh, nombre, objetivo))

                conn.commit()
                st.success("Objetivos guardados correctamente. Presiona F5 para actualizar.")
    else:
        st.info("Primero sube el archivo GrossAdd.")

with tab4:
    st.subheader("📱 Reportes para WhatsApp")

    if resumen is not None:

        opcion = st.radio(
            "Selecciona el tipo de reporte",
            ["Reporte individual", "Reporte general"]
        )

        if opcion == "Reporte individual":
            socio = st.selectbox(
                "Selecciona un socio",
                resumen["VENDEDOR_NOMBRE"]
            )

            fila = resumen[resumen["VENDEDOR_NOMBRE"] == socio].iloc[0]

            texto = (
                f"📊 AVANCE DE VENTAS\n\n"
                f"👤 {fila['VENDEDOR_NOMBRE']}\n"
                f"EH: {fila['VENDEDOR_EH']}\n\n"
                f"✅ Ventas: {fila['Ventas']}\n"
                f"🎯 Objetivo: {fila['OBJETIVO']}\n"
                f"📈 Cumplimiento: {fila['CUMPLIMIENTO']}%\n"
                f"⏳ Faltan: {fila['FALTAN']}\n"
            )

            st.text_area("Mensaje individual", texto, height=250)

            link = "https://wa.me/?text=" + urllib.parse.quote(texto)
            st.link_button("📲 Compartir por WhatsApp", link)

        else:
            texto = "📊 AVANCE GENERAL DE VENTAS\n\n"

            for _, row in resumen.iterrows():
                texto += (
                    f"👤 {row['VENDEDOR_NOMBRE']}\n"
                    f"✅ {row['Ventas']} / 🎯 {row['OBJETIVO']}\n"
                    f"📈 {row['CUMPLIMIENTO']}% | Faltan: {row['FALTAN']}\n"
                    "----------------------\n"
                )

            st.text_area("Mensaje general", texto, height=400)

            link = "https://wa.me/?text=" + urllib.parse.quote(texto)
            st.link_button("📲 Compartir reporte general", link)

    else:
        st.info("Primero sube el archivo GrossAdd.")
