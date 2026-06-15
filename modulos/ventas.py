import streamlit as st
import pandas as pd
from .comun import leer_archivo, obtener_codigo_minimo, obtener_medalla, get_conn


def clasificar_tipo_conteo(row, codigo_minimo):
    """Clasifica la venta para objetivo.

    Regla principal:
    - Si TIPO_VENTA contiene CROSS => CROSSSELLING
    - Si TIPO_VENTA contiene GROSS => VENTA_OBJETIVO

    Regla de respaldo, solo si no existe TIPO_VENTA:
    - CLIENTE_NRO >= codigo_minimo => VENTA_OBJETIVO
    - CLIENTE_NRO < codigo_minimo => CROSSSELLING
    """
    tipo = str(row.get("TIPO_VENTA", "")).strip().upper().replace(" ", "_")

    if "CROSS" in tipo:
        return "CROSSSELLING"

    if "GROSS" in tipo:
        return "VENTA_OBJETIVO"

    codigo = row.get("CLIENTE_NRO_NUM", 0)
    return "VENTA_OBJETIVO" if codigo >= codigo_minimo else "CROSSSELLING"


def cargar_grossadd():
    codigo_minimo = obtener_codigo_minimo()
    st.info(
        f"🎯 Código mínimo de respaldo: {codigo_minimo}. "
        "Primero se usa TIPO_VENTA: GROSSADD cuenta al objetivo y CROSS_SELLING se muestra como crosselling."
    )

    archivo = st.file_uploader("📤 Sube el archivo GrossAdd", type=["csv", "xlsx"], key="grossadd")
    df = None
    resumen = None

    if archivo:
        try:
            df = leer_archivo(archivo)
            if df is None:
                return None, None, codigo_minimo

            st.success(f"Archivo GrossAdd cargado: {len(df)} registros")

            req = ["VENDEDOR_EH", "VENDEDOR_NOMBRE", "CLIENTE_NRO", "CLIENTE_NOMBRE", "FECHA_INSTALACION"]
            faltantes = [c for c in req if c not in df.columns]
            if faltantes:
                st.error(f"Faltan columnas en el GrossAdd: {faltantes}")
                return df, None, codigo_minimo

            if "TIPO_VENTA" not in df.columns:
                st.warning("El archivo no tiene TIPO_VENTA. Se usará el código mínimo como respaldo.")
                df["TIPO_VENTA"] = ""

            df["VENDEDOR_EH"] = df["VENDEDOR_EH"].astype(str)
            df["CLIENTE_NRO_NUM"] = pd.to_numeric(df["CLIENTE_NRO"], errors="coerce").fillna(0).astype(int)
            df["TIPO_CONTEO"] = df.apply(lambda row: clasificar_tipo_conteo(row, codigo_minimo), axis=1)

            resumen = df.groupby(["VENDEDOR_EH", "VENDEDOR_NOMBRE"]).agg(
                Ventas_Objetivo=("TIPO_CONTEO", lambda x: (x == "VENTA_OBJETIVO").sum()),
                Crosselling=("TIPO_CONTEO", lambda x: (x == "CROSSSELLING").sum()),
                Total_Ventas=("CLIENTE_NRO", "count")
            ).reset_index()

            conn = get_conn()
            objetivos = pd.read_sql("SELECT * FROM objetivos", conn)
            conn.close()

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
                lambda x: round((x["Ventas_Objetivo"] / x["OBJETIVO"]) * 100, 1) if x["OBJETIVO"] > 0 else 0,
                axis=1
            )
            resumen["FALTAN"] = (resumen["OBJETIVO"] - resumen["Ventas_Objetivo"]).clip(lower=0).astype(int)
            resumen = resumen.sort_values("Ventas_Objetivo", ascending=False).reset_index(drop=True)
            resumen["POSICION"] = resumen.index + 1
            resumen["MEDALLA"] = resumen["POSICION"].apply(obtener_medalla)

            with st.expander("🔎 Validación de clasificación"):
                st.write("Resumen por TIPO_VENTA y TIPO_CONTEO")
                st.dataframe(
                    df.groupby(["TIPO_VENTA", "TIPO_CONTEO"]).size().reset_index(name="Cantidad"),
                    use_container_width=True,
                    hide_index=True
                )

        except Exception as e:
            st.error(f"Error al procesar GrossAdd: {e}")

    return df, resumen, codigo_minimo


def dashboard(resumen):
    st.subheader("📊 Dashboard Global")
    if resumen is None:
        st.info("Primero sube el archivo GrossAdd.")
        return

    total_objetivo_ventas = resumen["Ventas_Objetivo"].sum()
    total_crosselling = resumen["Crosselling"].sum()
    total_ventas = resumen["Total_Ventas"].sum()
    total_objetivo = resumen["OBJETIVO"].sum()
    cumplimiento_total = round((total_objetivo_ventas / total_objetivo) * 100, 1) if total_objetivo > 0 else 0
    faltan_total = max(total_objetivo - total_objetivo_ventas, 0)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("👥 Socios", int(len(resumen)))
    c2.metric("✅ Ventas objetivo", int(total_objetivo_ventas))
    c3.metric("🔄 Crosselling", int(total_crosselling))
    c4.metric("📊 Total ventas", int(total_ventas))
    c5.metric("📈 Cumplimiento", f"{cumplimiento_total}%")

    st.progress(min(cumplimiento_total, 100) / 100)

    c6, c7 = st.columns(2)
    c6.metric("🎯 Objetivo global", int(total_objetivo))
    c7.metric("⏳ Faltan para objetivo", int(faltan_total))

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🏆 Ventas objetivo por socio")
        st.bar_chart(resumen.set_index("VENDEDOR_NOMBRE")["Ventas_Objetivo"])
    with col_b:
        st.subheader("🔄 Crosselling por socio")
        st.bar_chart(resumen.set_index("VENDEDOR_NOMBRE")["Crosselling"])

    st.subheader("🏅 Top 5 Socios")
    st.dataframe(
        resumen.head(5)[["MEDALLA", "POSICION", "VENDEDOR_NOMBRE", "Ventas_Objetivo", "Crosselling", "Total_Ventas", "OBJETIVO", "CUMPLIMIENTO", "FALTAN"]],
        use_container_width=True,
        hide_index=True
    )


def ranking(resumen):
    st.subheader("🏆 Ranking de Ventas")
    if resumen is None:
        st.info("Primero sube el archivo GrossAdd.")
        return

    st.dataframe(
        resumen[["MEDALLA", "POSICION", "VENDEDOR_EH", "VENDEDOR_NOMBRE", "Ventas_Objetivo", "Crosselling", "Total_Ventas", "OBJETIVO", "CUMPLIMIENTO", "FALTAN"]],
        use_container_width=True,
        hide_index=True
    )
