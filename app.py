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
    df.columns = [str(c).strip().upper().replace(" ", "_") for c in df.columns]
    return df

def obtener_medalla(posicion):
    if posicion == 1:
        return "🥇"
    elif posicion == 2:
        return "🥈"
    elif posicion == 3:
        return "🥉"
    elif posicion in [4, 5]:
        return "🏆"
    return "📊"

archivo = st.file_uploader("📤 Sube el archivo GrossAdd", type=["csv", "xlsx"])

df = None
resumen = None

if archivo:
    try:
        df = leer_archivo(archivo)

        if df is not None:
            st.success(f"Archivo GrossAdd cargado: {len(df)} registros")

            columnas_requeridas = [
                "VENDEDOR_EH",
                "VENDEDOR_NOMBRE",
                "CLIENTE_NRO",
                "CLIENTE_NOMBRE",
                "FECHA_INSTALACION"
            ]

            faltantes = [c for c in columnas_requeridas if c not in df.columns]

            if faltantes:
                st.error(f"Faltan columnas en el GrossAdd: {faltantes}")
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

                resumen = resumen.sort_values("Ventas", ascending=False).reset_index(drop=True)
                resumen["POSICION"] = resumen.index + 1
                resumen["MEDALLA"] = resumen["POSICION"].apply(obtener_medalla)

    except Exception as e:
        st.error(f"Error al procesar GrossAdd: {e}")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard",
    "🏆 Ranking",
    "🎯 Objetivos",
    "📱 WhatsApp",
    "📋 Pendientes de Pago"
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
        st.metric("⏳ Faltan para objetivo", int(faltan_total))

        st.subheader("🏅 Top 5 Socios")
        st.dataframe(
            resumen.head(5)[["MEDALLA", "POSICION", "VENDEDOR_NOMBRE", "Ventas", "OBJETIVO", "CUMPLIMIENTO", "FALTAN"]],
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
                "MEDALLA",
                "POSICION",
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
        opcion = st.radio("Tipo de reporte", ["Resumen individual", "Reporte general"])

        if opcion == "Resumen individual":
            socio = st.selectbox("Selecciona socio", resumen["VENDEDOR_NOMBRE"])
            fila = resumen[resumen["VENDEDOR_NOMBRE"] == socio].iloc[0]

            texto = (
                f"📊 AVANCE DE VENTAS\n\n"
                f"{fila['MEDALLA']} {fila['VENDEDOR_NOMBRE']}\n"
                f"EH: {fila['VENDEDOR_EH']}\n\n"
                f"✅ Ventas: {fila['Ventas']}\n"
                f"🎯 Objetivo: {fila['OBJETIVO']}\n"
                f"📈 Cumplimiento: {fila['CUMPLIMIENTO']}%\n"
                f"⏳ Faltan: {fila['FALTAN']}\n"
            )

            st.text_area("Mensaje", texto, height=300)
            st.link_button("📲 Compartir por WhatsApp", "https://wa.me/?text=" + urllib.parse.quote(texto))

        else:
            texto = "📊 AVANCE GENERAL DE VENTAS\n\n"

            for _, row in resumen.iterrows():
                texto += (
                    f"{row['MEDALLA']} {row['VENDEDOR_NOMBRE']}\n"
                    f"✅ {row['Ventas']} / 🎯 {row['OBJETIVO']}\n"
                    f"📈 {row['CUMPLIMIENTO']}% | Faltan: {row['FALTAN']}\n"
                    "----------------------\n"
                )

            st.text_area("Mensaje general", texto, height=450)
            st.link_button("📲 Compartir reporte general", "https://wa.me/?text=" + urllib.parse.quote(texto))
    else:
        st.info("Primero sube el archivo GrossAdd.")

with tab5:
    st.subheader("📋 Pendientes de Pago")

    st.write("Sube el archivo PENDIENTE_INST_SIN_PAGO, selecciona un socio y envía sus pendientes por WhatsApp.")

    socios_dict = {
        "91207": "GUALBERTO FERNANDO SANJINES",
        "91208": "DANNY QUISBERT MENDOZA",
        "91262": "WARNES RIVERA CHUQUIMIA",
        "91283": "SOLAGEL QUENTA GUTIERREZ",
        "89859": "JOSE PABLO FERNANDEZ",
        "89326": "PALMIRA SELAES",
        "88874": "GUSTAVO CALLEJAS",
        "88463": "ALICIA GRACIELA ZAMORA BUEZO",
        "86963": "TERESA CHIPANA",
        "83457": "ESTRELLA BELEN QUISPE FLORES",
        "63483": "FRANKLIN RAMIRO QUISPE ROSAS",
        "79030": "VICTOR HUGO CHAMBILLA FLORES",
        "72210": "GUADALUPE APAZA VILA",
        "59509": "ADRIANA PAOLA VILLAFUERTE GUERRA",
        "58984": "MARIA SURCO ARUQUIPA",
        "88426": "SONIA NOEMI MAYTA",
        "89231": "ALEX RUDY MAMANI GUARACHI",
        "86737": "ANAHI OINCA",
        "78340": "OLIVIA SANCHEZ QUISPE",
        "78099": "GEOVANA CARLA SIÑANI LUNA",
    }

    archivo_pago = st.file_uploader(
        "📤 Sube archivo PENDIENTE_INST_SIN_PAGO",
        type=["csv", "xlsx"],
        key="pendientes_pago"
    )

    if archivo_pago:
        try:
            pagos = leer_archivo(archivo_pago)

            if pagos is not None:
                pagos = normalizar_columnas(pagos)
                st.success(f"Archivo cargado: {len(pagos)} registros")

                columnas = [
                    "CLIENTE_NRO",
                    "FECHA_REPORTE",
                    "VENDEDOR_EH",
                    "CLIENTE_NOMBRE",
                    "NODO_NOMBRE",
                    "FECHA_GENERACION_OT",
                    "CLIENTE_TELEFONO2"
                ]

                faltantes = [c for c in columnas if c not in pagos.columns]

                if faltantes:
                    st.error(f"Faltan columnas: {faltantes}")
                    st.write("Columnas detectadas:")
                    st.write(list(pagos.columns))
                else:
                    pagos["VENDEDOR_EH"] = pagos["VENDEDOR_EH"].astype(str)
                    pagos["SOCIO"] = pagos["VENDEDOR_EH"].map(socios_dict).fillna("SIN NOMBRE")
                    pagos["SOCIO_DISPLAY"] = pagos["VENDEDOR_EH"] + " - " + pagos["SOCIO"]

                    socios_con_pendientes = (
                        pagos[["VENDEDOR_EH", "SOCIO", "SOCIO_DISPLAY"]]
                        .drop_duplicates()
                        .sort_values("SOCIO")
                    )

                    socio_sel = st.selectbox("Selecciona socio", socios_con_pendientes["SOCIO_DISPLAY"])

                    detalle = pagos[pagos["SOCIO_DISPLAY"] == socio_sel].copy()

                    eh = detalle.iloc[0]["VENDEDOR_EH"]
                    nombre = detalle.iloc[0]["SOCIO"]

                    st.metric("📌 Pendientes de pago", len(detalle))

                    texto = "📋 PENDIENTES DE PAGO\n\n"
                    texto += f"👤 Socio: {nombre}\n"
                    texto += f"EH: {eh}\n"
                    texto += f"📌 Total pendientes: {len(detalle)}\n\n"

                    for _, row in detalle.iterrows():
                        texto += (
                            f"🔹 Código: {row['CLIENTE_NRO']}\n"
                            f"📅 Reporte: {row['FECHA_REPORTE']}\n"
                            f"🗓️ Generación OT: {row['FECHA_GENERACION_OT']}\n"
                            f"👤 Cliente: {row['CLIENTE_NOMBRE']}\n"
                            f"📍 Nodo: {row['NODO_NOMBRE']}\n"
                            f"📞 Tel: {row['CLIENTE_TELEFONO2']}\n\n"
                        )

                    st.text_area("Mensaje WhatsApp", texto, height=500)

                    st.link_button(
                        "📲 Compartir por WhatsApp",
                        "https://wa.me/?text=" + urllib.parse.quote(texto)
                    )

        except Exception as e:
            st.error(f"Error al procesar pendientes de pago: {e}")
