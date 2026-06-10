import streamlit as st
import pandas as pd
import sqlite3
import urllib.parse

st.set_page_config(page_title="Dashboard Tigo Ventas", layout="wide")

st.markdown("""
<style>
.main {background-color: #0b1020;}
.tigo-header {
    background: linear-gradient(90deg, #0033A0, #00A3E0);
    padding: 22px;
    border-radius: 18px;
    color: white;
    margin-bottom: 18px;
}
.tigo-logo {
    font-size: 44px;
    font-weight: 900;
    color: white;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="tigo-header">
    <div class="tigo-logo">TIGO</div>
    <h2>📊 Dashboard de Ventas Socios</h2>
    <p>Seguimiento de objetivos, cumplimiento y reportes para WhatsApp</p>
    <hr style="border:1px solid rgba(255,255,255,0.2);">
    <p style="font-size:13px;">👨‍💻 Desarrollado por Vladimir Cuenca López</p>
</div>
""", unsafe_allow_html=True)

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

def leer_archivo(archivo):
    nombre = archivo.name.lower()
    if nombre.endswith(".csv"):
        return pd.read_csv(archivo, sep=None, engine="python", encoding="latin1")
    elif nombre.endswith(".xlsx"):
        return pd.read_excel(archivo)
    else:
        st.error("Formato no permitido. Sube CSV o Excel .xlsx")
        return None


def normalizar_columnas(df):
    df = df.copy()
    df.columns = [
        str(c).strip().upper().replace(" ", "_")
        for c in df.columns
    ]
    return df


def texto_limpio(valor):
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.upper() in ["", "NAN", "NONE", "NULL", "SIN DATO"]:
        return ""
    return texto


def analizar_crm_observacion(row):
    crm_obs = texto_limpio(row.get("CRM_OBSERVACION", ""))
    crm_motivo = texto_limpio(row.get("CRM_MOTIVO", ""))
    estado = texto_limpio(row.get("TIPO_TRANSACCION", ""))
    tipo_venta = texto_limpio(row.get("TIPO_VENTA", ""))

    texto = f"{crm_obs} {crm_motivo} {estado} {tipo_venta}".lower()

    if crm_obs == "" and crm_motivo == "":
        return "SIN CRM / SUSPENDIDA SIN RAZÓN"

    if any(p in texto for p in ["no quiere", "ya no quiere", "desiste", "desist", "anular", "anulacion", "cancel", "rechaza"]):
        return "CLIENTE DESISTE / NO QUIERE INSTALACIÓN"

    if any(p in texto for p in ["no contesta", "no responde", "sin contacto", "contacto con cliente", "cdc", "llamada", "llamar"]):
        return "INSTALACIÓN NO ATENDIDA / CONTACTAR CLIENTE"

    if any(p in texto for p in ["reagend", "agenda", "reprogram"]):
        return "REAGENDAR INSTALACIÓN"

    if any(p in texto for p in ["tap", "satur", "cobertura", "facilidad", "poste", "sin señal"]):
        return "REVISIÓN TÉCNICA / COBERTURA"

    return "INSTALACIÓN SUSPENDIDA - REVISAR OBSERVACIÓN CRM"


def recortar_texto(texto, largo=180):
    texto = texto_limpio(texto).replace("\\n", " ")
    if texto == "":
        return "Sin observación CRM registrada."
    if len(texto) > largo:
        return texto[:largo].strip() + "..."
    return texto

archivo = st.file_uploader("📤 Sube el archivo GrossAdd", type=["csv", "xlsx"])

df = None
resumen = None

if archivo:
    try:
        df = leer_archivo(archivo)

        if df is not None:
            st.success(f"Archivo cargado: {len(df)} registros")

            columnas_requeridas = [
                "VENDEDOR_EH",
                "VENDEDOR_NOMBRE",
                "CLIENTE_NRO",
                "FECHA_INSTALACION"
            ]

            faltantes = [c for c in columnas_requeridas if c not in df.columns]

            if faltantes:
                st.error(f"Faltan columnas en el archivo: {faltantes}")
            else:
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

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard",
    "🏆 Ranking",
    "🎯 Objetivos",
    "📱 WhatsApp",
    "🚨 Suspendidas"
])

with tab1:
    st.subheader("📊 Dashboard Global")

    if resumen is not None:
        total_ventas = resumen["Ventas"].sum()
        total_objetivo = resumen["OBJETIVO"].sum()
        cumplimiento_total = round((total_ventas / total_objetivo) * 100, 1) if total_objetivo > 0 else 0
        faltan_total = max(total_objetivo - total_ventas, 0)
        socios_activos = len(resumen)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("👥 Socios", int(socios_activos))
        c2.metric("✅ Ventas", int(total_ventas))
        c3.metric("🎯 Objetivo", int(total_objetivo))
        c4.metric("📈 Cumplimiento", f"{cumplimiento_total}%")

        st.progress(min(cumplimiento_total, 100) / 100)
        st.metric("⏳ Faltan para el objetivo global", int(faltan_total))

        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("🏆 Top ventas")
            st.bar_chart(resumen.set_index("VENDEDOR_NOMBRE")["Ventas"])

        with col_b:
            st.subheader("📈 Cumplimiento")
            st.bar_chart(resumen.set_index("VENDEDOR_NOMBRE")["CUMPLIMIENTO"])

        st.subheader("🏅 Top 5 Socios")
        st.dataframe(
            resumen.head(5)[["VENDEDOR_NOMBRE", "Ventas", "OBJETIVO", "CUMPLIMIENTO", "FALTAN"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Primero sube el archivo GrossAdd.")

with tab2:
    st.subheader("🏆 Ranking de Ventas")

    if resumen is not None:
        st.dataframe(
            resumen[[
                "VENDEDOR_EH",
                "VENDEDOR_NOMBRE",
                "Ventas",
                "OBJETIVO",
                "CUMPLIMIENTO",
                "FALTAN"
            ]],
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
            nuevos = []

            for _, row in socios.iterrows():
                eh = str(row["VENDEDOR_EH"])
                nombre = row["VENDEDOR_NOMBRE"]

                actual = cursor.execute(
                    "SELECT OBJETIVO FROM objetivos WHERE EH=?",
                    (eh,)
                ).fetchone()

                valor = int(actual[0]) if actual else 0

                col1, col2, col3 = st.columns([2, 5, 2])
                col1.write(eh)
                col2.write(nombre)

                objetivo = col3.number_input(
                    "Objetivo",
                    min_value=0,
                    value=valor,
                    key=f"obj_{eh}",
                    label_visibility="collapsed"
                )

                nuevos.append((eh, nombre, int(objetivo)))

            if st.form_submit_button("💾 Guardar objetivos"):
                for eh, nombre, objetivo in nuevos:
                    cursor.execute("""
                        INSERT INTO objetivos (EH, NOMBRE, OBJETIVO)
                        VALUES (?, ?, ?)
                        ON CONFLICT(EH) DO UPDATE SET
                            NOMBRE=excluded.NOMBRE,
                            OBJETIVO=excluded.OBJETIVO
                    """, (eh, nombre, objetivo))

                conn.commit()
                st.success("Objetivos guardados. Presiona F5 para actualizar.")
    else:
        st.info("Primero sube el archivo GrossAdd.")

with tab4:
    st.subheader("📱 Reportes para WhatsApp")

    if resumen is not None:
        opcion = st.radio(
            "Tipo de reporte",
            [
                "Resumen individual",
                "Seguimiento individual con códigos",
                "Reporte general"
            ]
        )

        if opcion in ["Resumen individual", "Seguimiento individual con códigos"]:
            socio = st.selectbox("Selecciona socio", resumen["VENDEDOR_NOMBRE"])
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

            if opcion == "Seguimiento individual con códigos":
                detalle = df[
                    df["VENDEDOR_NOMBRE"] == fila["VENDEDOR_NOMBRE"]
                ][["CLIENTE_NRO", "FECHA_INSTALACION"]]

                texto += "\n📋 CÓDIGOS PARA SEGUIMIENTO:\n\n"

                for _, venta in detalle.iterrows():
                    texto += f"🔹 {venta['CLIENTE_NRO']} | {venta['FECHA_INSTALACION']}\n"

            st.text_area("Mensaje", texto, height=450)

            st.link_button(
                "📲 Compartir por WhatsApp",
                "https://wa.me/?text=" + urllib.parse.quote(texto)
            )

        else:
            texto = "📊 AVANCE GENERAL DE VENTAS\n\n"

            for _, row in resumen.iterrows():
                texto += (
                    f"👤 {row['VENDEDOR_NOMBRE']}\n"
                    f"✅ {row['Ventas']} / 🎯 {row['OBJETIVO']}\n"
                    f"📈 {row['CUMPLIMIENTO']}% | Faltan: {row['FALTAN']}\n"
                    "----------------------\n"
                )

            st.text_area("Mensaje general", texto, height=450)

            st.link_button(
                "📲 Compartir reporte general",
                "https://wa.me/?text=" + urllib.parse.quote(texto)
            )
    else:
        st.info("Primero sube el archivo GrossAdd.")

# =========================
# SUSPENDIDAS / RECLAMOS
# =========================
with tab5:
    st.subheader("🚨 Suspendidas / Instalaciones no atendidas")

    st.write("Sube el archivo diario de suspendidas para analizar CRM_OBSERVACION y generar reclamos por socio para WhatsApp.")

    archivo_suspendidas = st.file_uploader(
        "📤 Sube archivo SUSPENDIDA",
        type=["csv", "xlsx"],
        key="suspendidas_reclamos"
    )

    if archivo_suspendidas:
        try:
            suspendidas = leer_archivo(archivo_suspendidas)

            if suspendidas is not None:
                suspendidas = normalizar_columnas(suspendidas)
                st.success(f"Archivo de suspendidas cargado: {len(suspendidas)} registros")

                columnas_requeridas_susp = [
                    "CLIENTE_NRO",
                    "FECHA_REPORTE",
                    "VENDEDOR_EH",
                    "VENDEDOR_NOMBRE",
                    "TIPO_VENTA",
                    "CLIENTE_TELEFONO1",
                    "NODO_NOMBRE",
                    "CRM_OBSERVACION"
                ]

                faltantes_susp = [
                    c for c in columnas_requeridas_susp
                    if c not in suspendidas.columns
                ]

                if faltantes_susp:
                    st.error(f"Faltan columnas en el archivo de suspendidas: {faltantes_susp}")
                    st.write("Columnas detectadas:")
                    st.write(list(suspendidas.columns))
                else:
                    suspendidas["VENDEDOR_EH"] = suspendidas["VENDEDOR_EH"].astype(str)
                    suspendidas["OBSERVACION_ANALISIS"] = suspendidas.apply(analizar_crm_observacion, axis=1)
                    suspendidas["SOCIO"] = suspendidas["VENDEDOR_EH"] + " - " + suspendidas["VENDEDOR_NOMBRE"].astype(str)

                    st.subheader("📊 Resumen")

                    total_casos = len(suspendidas)
                    socios_casos = suspendidas["VENDEDOR_EH"].nunique()
                    sin_crm = len(suspendidas[suspendidas["OBSERVACION_ANALISIS"] == "SIN CRM / SUSPENDIDA SIN RAZÓN"])
                    no_atendidas = len(suspendidas[suspendidas["OBSERVACION_ANALISIS"] == "INSTALACIÓN NO ATENDIDA / CONTACTAR CLIENTE"])

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("📋 Total casos", total_casos)
                    c2.metric("👥 Socios", socios_casos)
                    c3.metric("⚠️ Sin CRM", sin_crm)
                    c4.metric("📞 No atendidas", no_atendidas)

                    resumen_susp = (
                        suspendidas.groupby(["VENDEDOR_EH", "VENDEDOR_NOMBRE", "SOCIO"])
                        .agg(Casos=("CLIENTE_NRO", "count"))
                        .reset_index()
                        .sort_values("Casos", ascending=False)
                    )

                    st.subheader("👤 Seleccionar socio")

                    socio_sel = st.selectbox(
                        "Socio",
                        resumen_susp["SOCIO"]
                    )

                    detalle = suspendidas[
                        suspendidas["SOCIO"] == socio_sel
                    ].copy()

                    eh_sel = detalle.iloc[0]["VENDEDOR_EH"]
                    nombre_socio = detalle.iloc[0]["VENDEDOR_NOMBRE"]

                    st.metric("📌 Casos del socio", len(detalle))

                    st.subheader("📋 Casos detectados")

                    st.dataframe(
                        detalle[[
                            "CLIENTE_NRO",
                            "FECHA_REPORTE",
                            "TIPO_VENTA",
                            "CLIENTE_TELEFONO1",
                            "NODO_NOMBRE",
                            "OBSERVACION_ANALISIS",
                            "CRM_OBSERVACION"
                        ]],
                        use_container_width=True,
                        hide_index=True
                    )

                    texto_susp = "🚨 RECLAMOS / SUSPENDIDAS\n\n"
                    texto_susp += f"👤 Socio: {nombre_socio}\n"
                    texto_susp += f"EH: {eh_sel}\n"
                    texto_susp += f"📌 Total casos: {len(detalle)}\n\n"

                    for _, row in detalle.iterrows():
                        texto_susp += (
                            f"⚠️ {row['OBSERVACION_ANALISIS']}\n"
                            f"🔹 Código: {row['CLIENTE_NRO']}\n"
                            f"📅 Fecha reporte: {row['FECHA_REPORTE']}\n"
                            f"📌 Tipo venta: {row['TIPO_VENTA']}\n"
                            f"📞 Teléfono: {row['CLIENTE_TELEFONO1']}\n"
                            f"📍 Nodo: {row['NODO_NOMBRE']}\n"
                            f"📝 Observación: {recortar_texto(row['CRM_OBSERVACION'])}\n\n"
                        )

                    st.subheader("📱 Mensaje para WhatsApp")

                    st.text_area(
                        "Mensaje",
                        texto_susp,
                        height=520
                    )

                    st.link_button(
                        "📲 Compartir por WhatsApp",
                        "https://wa.me/?text=" + urllib.parse.quote(texto_susp)
                    )

                    st.subheader("📊 Resumen general por socio")

                    st.dataframe(
                        resumen_susp[["SOCIO", "Casos"]],
                        use_container_width=True,
                        hide_index=True
                    )

                    texto_general_susp = "🚨 RESUMEN GENERAL SUSPENDIDAS\n\n"

                    for _, row in resumen_susp.iterrows():
                        texto_general_susp += (
                            f"👤 {row['SOCIO']}\n"
                            f"📌 Casos: {row['Casos']}\n"
                            "----------------------\n"
                        )

                    st.text_area(
                        "Resumen general para WhatsApp",
                        texto_general_susp,
                        height=360
                    )

                    st.link_button(
                        "📲 Compartir resumen general",
                        "https://wa.me/?text=" + urllib.parse.quote(texto_general_susp)
                    )

        except Exception as e:
            st.error(f"Error al procesar suspendidas: {e}")

