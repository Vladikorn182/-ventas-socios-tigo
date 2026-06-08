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
    <p>Seguimiento de objetivos, crosselling, agenda técnica y reportes para WhatsApp</p>
    <hr style="border:1px solid rgba(255,255,255,0.2);">
    <p style="font-size:13px;">👨‍💻 Desarrollado por Vladimir Cuenca López</p>
</div>
""", unsafe_allow_html=True)

# =========================
# BASE DE DATOS LOCAL
# =========================
conn = sqlite3.connect("ventas.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS objetivos (
    EH TEXT PRIMARY KEY,
    NOMBRE TEXT,
    OBJETIVO INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS configuracion (
    CLAVE TEXT PRIMARY KEY,
    VALOR TEXT
)
""")

conn.commit()

cursor.execute("""
INSERT OR IGNORE INTO configuracion (CLAVE, VALOR)
VALUES ('codigo_minimo_objetivo', '2671392')
""")
conn.commit()


# =========================
# FUNCIONES
# =========================
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
        str(c).strip().lower().replace(" ", "_")
        for c in df.columns
    ]
    return df


def obtener_codigo_minimo():
    valor = cursor.execute(
        "SELECT VALOR FROM configuracion WHERE CLAVE='codigo_minimo_objetivo'"
    ).fetchone()

    if valor:
        try:
            return int(valor[0])
        except:
            return 2671392

    return 2671392


def guardar_codigo_minimo(valor):
    cursor.execute("""
        INSERT INTO configuracion (CLAVE, VALOR)
        VALUES ('codigo_minimo_objetivo', ?)
        ON CONFLICT(CLAVE) DO UPDATE SET
            VALOR=excluded.VALOR
    """, (str(valor),))
    conn.commit()


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


def obtener_distincion(posicion):
    if posicion == 1:
        return "🥇 TOP 1 - Excelente trabajo"
    elif posicion == 2:
        return "🥈 TOP 2 - Muy buen avance"
    elif posicion == 3:
        return "🥉 TOP 3 - Gran desempeño"
    elif posicion in [4, 5]:
        return "🏆 TOP 5 - Dentro de los mejores socios"
    return ""


def mensaje_motivador(posicion):
    if posicion == 1:
        return "👏 Felicidades, estás liderando el ranking. Sigue así."
    elif posicion == 2:
        return "👏 Excelente avance, estás entre los mejores."
    elif posicion == 3:
        return "👏 Gran desempeño, mantén el ritmo."
    elif posicion in [4, 5]:
        return "👏 Muy buen trabajo, estás dentro del Top 5."
    return "💪 Sigamos avanzando hacia el objetivo del mes."


# =========================
# CARGA DE GROSSADD
# =========================
codigo_minimo_objetivo = obtener_codigo_minimo()

st.info(
    f"🎯 Código mínimo para contar al objetivo: {codigo_minimo_objetivo}. "
    f"Los códigos menores se mostrarán como 🔄 Crosselling y no sumarán al cumplimiento."
)

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
                df["CLIENTE_NRO_NUM"] = pd.to_numeric(
                    df["CLIENTE_NRO"],
                    errors="coerce"
                ).fillna(0).astype(int)

                df["TIPO_CONTEO"] = df["CLIENTE_NRO_NUM"].apply(
                    lambda x: "VENTA_OBJETIVO" if x >= codigo_minimo_objetivo else "CROSSSELLING"
                )

                resumen = (
                    df.groupby(["VENDEDOR_EH", "VENDEDOR_NOMBRE"])
                    .agg(
                        Ventas_Objetivo=("TIPO_CONTEO", lambda x: (x == "VENTA_OBJETIVO").sum()),
                        Crosselling=("TIPO_CONTEO", lambda x: (x == "CROSSSELLING").sum()),
                        Total_Ventas=("CLIENTE_NRO", "count")
                    )
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
                    lambda x: round((x["Ventas_Objetivo"] / x["OBJETIVO"]) * 100, 1)
                    if x["OBJETIVO"] > 0 else 0,
                    axis=1
                )

                resumen["FALTAN"] = (
                    resumen["OBJETIVO"] - resumen["Ventas_Objetivo"]
                ).clip(lower=0).astype(int)

                resumen = resumen.sort_values("Ventas_Objetivo", ascending=False).reset_index(drop=True)
                resumen["POSICION"] = resumen.index + 1
                resumen["MEDALLA"] = resumen["POSICION"].apply(obtener_medalla)
                resumen["DISTINCION"] = resumen["POSICION"].apply(obtener_distincion)

    except Exception as e:
        st.error(f"Error al procesar GrossAdd: {e}")


# =========================
# PESTAÑAS
# =========================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Dashboard",
    "🏆 Ranking",
    "🎯 Objetivos",
    "⚙️ Configuración",
    "📱 WhatsApp",
    "🗺️ Agenda Técnica"
])


# =========================
# DASHBOARD
# =========================
with tab1:
    st.subheader("📊 Dashboard Global")

    if resumen is not None:
        total_objetivo_ventas = resumen["Ventas_Objetivo"].sum()
        total_crosselling = resumen["Crosselling"].sum()
        total_ventas = resumen["Total_Ventas"].sum()
        total_objetivo = resumen["OBJETIVO"].sum()
        cumplimiento_total = round((total_objetivo_ventas / total_objetivo) * 100, 1) if total_objetivo > 0 else 0
        faltan_total = max(total_objetivo - total_objetivo_ventas, 0)
        socios_activos = len(resumen)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("👥 Socios", int(socios_activos))
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
            resumen.head(5)[[
                "MEDALLA",
                "POSICION",
                "VENDEDOR_NOMBRE",
                "Ventas_Objetivo",
                "Crosselling",
                "Total_Ventas",
                "OBJETIVO",
                "CUMPLIMIENTO",
                "FALTAN"
            ]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Primero sube el archivo GrossAdd.")


# =========================
# RANKING
# =========================
with tab2:
    st.subheader("🏆 Ranking de Ventas")

    if resumen is not None:
        st.dataframe(
            resumen[[
                "MEDALLA",
                "POSICION",
                "VENDEDOR_EH",
                "VENDEDOR_NOMBRE",
                "Ventas_Objetivo",
                "Crosselling",
                "Total_Ventas",
                "OBJETIVO",
                "CUMPLIMIENTO",
                "FALTAN"
            ]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Primero sube el archivo GrossAdd.")


# =========================
# OBJETIVOS
# =========================
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


# =========================
# CONFIGURACIÓN
# =========================
with tab4:
    st.subheader("⚙️ Configuración")

    st.write("Define desde qué código una venta cuenta al objetivo.")
    st.write("Los códigos menores se mostrarán como crosselling y no sumarán al cumplimiento.")

    nuevo_codigo_minimo = st.number_input(
        "Código mínimo para contar al objetivo",
        min_value=0,
        value=int(codigo_minimo_objetivo),
        step=1
    )

    if st.button("💾 Guardar configuración"):
        guardar_codigo_minimo(nuevo_codigo_minimo)
        st.success("Configuración guardada. Presiona F5 para recalcular.")


# =========================
# WHATSAPP
# =========================
with tab5:
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

            posicion = int(fila["POSICION"]) if "POSICION" in fila else 0
            dist = obtener_distincion(posicion)
            motivador = mensaje_motivador(posicion)

            texto = "📊 AVANCE DE VENTAS\n\n"

            if dist:
                texto += f"{dist}\n\n"

            texto += (
                f"👤 {fila['VENDEDOR_NOMBRE']}\n"
                f"EH: {fila['VENDEDOR_EH']}\n\n"
                f"✅ Ventas objetivo: {fila['Ventas_Objetivo']}\n"
                f"🔄 Crosselling: {fila['Crosselling']}\n"
                f"📊 Total ventas: {fila['Total_Ventas']}\n\n"
                f"🎯 Objetivo: {fila['OBJETIVO']}\n"
                f"📈 Cumplimiento: {fila['CUMPLIMIENTO']}%\n"
                f"⏳ Faltan: {fila['FALTAN']}\n\n"
                f"{motivador}\n"
            )

            if opcion == "Seguimiento individual con códigos":
                detalle = df[
                    df["VENDEDOR_NOMBRE"] == fila["VENDEDOR_NOMBRE"]
                ][["CLIENTE_NRO", "CLIENTE_NOMBRE", "FECHA_INSTALACION", "TIPO_CONTEO"]]

                ventas_objetivo = detalle[detalle["TIPO_CONTEO"] == "VENTA_OBJETIVO"]
                crosselling = detalle[detalle["TIPO_CONTEO"] == "CROSSSELLING"]

                texto += "\n✅ CÓDIGOS QUE CUENTAN AL OBJETIVO:\n\n"

                if len(ventas_objetivo) > 0:
                    for _, venta in ventas_objetivo.iterrows():
                        texto += f"🔹 {venta['CLIENTE_NRO']} | {venta['CLIENTE_NOMBRE']} | {venta['FECHA_INSTALACION']}\n"
                else:
                    texto += "Sin códigos nuevos para objetivo.\n"

                texto += "\n🔄 CROSSSELLING / CÓDIGOS ANTIGUOS:\n\n"

                if len(crosselling) > 0:
                    for _, venta in crosselling.iterrows():
                        texto += f"🔸 {venta['CLIENTE_NRO']} | {venta['CLIENTE_NOMBRE']} | {venta['FECHA_INSTALACION']}\n"
                else:
                    texto += "Sin crosselling registrado.\n"

            st.text_area("Mensaje", texto, height=520)

            st.link_button(
                "📲 Compartir por WhatsApp",
                "https://wa.me/?text=" + urllib.parse.quote(texto)
            )

        else:
            texto = "📊 AVANCE GENERAL DE VENTAS\n\n"

            for _, row in resumen.iterrows():
                medalla = row["MEDALLA"] if "MEDALLA" in row else "📊"
                texto += (
                    f"{medalla} {row['VENDEDOR_NOMBRE']}\n"
                    f"✅ Objetivo: {row['Ventas_Objetivo']}\n"
                    f"🔄 Crosselling: {row['Crosselling']}\n"
                    f"📊 Total: {row['Total_Ventas']}\n"
                    f"🎯 Meta: {row['OBJETIVO']}\n"
                    f"📈 {row['CUMPLIMIENTO']}% | Faltan: {row['FALTAN']}\n"
                    "----------------------\n"
                )

            st.text_area("Mensaje general", texto, height=520)

            st.link_button(
                "📲 Compartir reporte general",
                "https://wa.me/?text=" + urllib.parse.quote(texto)
            )
    else:
        st.info("Primero sube el archivo GrossAdd.")


# =========================
# AGENDA TÉCNICA
# =========================
with tab6:
    st.subheader("🗺️ Agenda Técnica")

    st.write("Sube el archivo diario de agenda técnica para ver instalaciones, supervisiones, contratistas, turnos y mapa.")

    archivo_agenda = st.file_uploader(
        "📤 Sube archivo Agenda Técnica",
        type=["csv", "xlsx"],
        key="agenda_tecnica"
    )

    agenda = None

    if archivo_agenda:
        try:
            agenda = leer_archivo(archivo_agenda)

            if agenda is not None:
                agenda = normalizar_columnas(agenda)

                st.success(f"Archivo de agenda cargado: {len(agenda)} registros")

                columnas_agenda = [
                    "cliente_nro",
                    "estado",
                    "contratista",
                    "tipo_trabajo",
                    "turno_agendamiento",
                    "dato_conexion",
                    "latitud",
                    "longitud"
                ]

                faltantes_agenda = [c for c in columnas_agenda if c not in agenda.columns]

                if faltantes_agenda:
                    st.error(f"Faltan columnas en agenda técnica: {faltantes_agenda}")
                    st.write("Columnas detectadas:")
                    st.write(list(agenda.columns))
                else:
                    agenda["latitud"] = pd.to_numeric(agenda["latitud"], errors="coerce")
                    agenda["longitud"] = pd.to_numeric(agenda["longitud"], errors="coerce")

                    total_agenda = len(agenda)
                    total_instalacion = len(agenda[agenda["tipo_trabajo"].astype(str).str.lower().str.contains("instalacion", na=False)])
                    total_supervision = len(agenda[agenda["tipo_trabajo"].astype(str).str.lower().str.contains("supervision", na=False)])
                    contratistas = agenda["contratista"].nunique()
                    turnos = agenda["turno_agendamiento"].nunique()

                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("📋 Total agenda", total_agenda)
                    c2.metric("🛠️ Instalaciones", total_instalacion)
                    c3.metric("🔍 Supervisiones", total_supervision)
                    c4.metric("👷 Contratistas", contratistas)
                    c5.metric("🕒 Turnos", turnos)

                    st.divider()

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        filtro_contratista = st.selectbox(
                            "Filtrar por contratista",
                            ["Todos"] + sorted(agenda["contratista"].dropna().astype(str).unique().tolist())
                        )

                    with col2:
                        filtro_tipo = st.selectbox(
                            "Filtrar por tipo de trabajo",
                            ["Todos"] + sorted(agenda["tipo_trabajo"].dropna().astype(str).unique().tolist())
                        )

                    with col3:
                        filtro_turno = st.selectbox(
                            "Filtrar por turno",
                            ["Todos"] + sorted(agenda["turno_agendamiento"].dropna().astype(str).unique().tolist())
                        )

                    agenda_filtrada = agenda.copy()

                    if filtro_contratista != "Todos":
                        agenda_filtrada = agenda_filtrada[
                            agenda_filtrada["contratista"].astype(str) == filtro_contratista
                        ]

                    if filtro_tipo != "Todos":
                        agenda_filtrada = agenda_filtrada[
                            agenda_filtrada["tipo_trabajo"].astype(str) == filtro_tipo
                        ]

                    if filtro_turno != "Todos":
                        agenda_filtrada = agenda_filtrada[
                            agenda_filtrada["turno_agendamiento"].astype(str) == filtro_turno
                        ]

                    st.subheader("🔎 Buscar por código cliente")

                    codigo_busqueda = st.text_input("Ingrese código cliente")

                    if codigo_busqueda:
                        resultado = agenda[
                            agenda["cliente_nro"].astype(str).str.contains(codigo_busqueda, na=False)
                        ]

                        if len(resultado) > 0:
                            st.dataframe(resultado, use_container_width=True, hide_index=True)
                        else:
                            st.warning("No se encontró el código en la agenda.")

                    st.subheader("🗺️ Mapa de agenda técnica")

                    agenda_mapa = agenda_filtrada.dropna(subset=["latitud", "longitud"]).copy()

                    if len(agenda_mapa) > 0:
                        mapa = agenda_mapa.rename(columns={"latitud": "lat", "longitud": "lon"})
                        st.map(mapa[["lat", "lon"]])
                    else:
                        st.warning("No hay coordenadas válidas para mostrar en el mapa.")

                    st.subheader("📊 Resumen por contratista")

                    resumen_contratista = (
                        agenda_filtrada.groupby("contratista")
                        .agg(
                            Total=("cliente_nro", "count"),
                            Instalaciones=("tipo_trabajo", lambda x: x.astype(str).str.lower().str.contains("instalacion", na=False).sum()),
                            Supervisiones=("tipo_trabajo", lambda x: x.astype(str).str.lower().str.contains("supervision", na=False).sum())
                        )
                        .reset_index()
                        .sort_values("Total", ascending=False)
                    )

                    st.dataframe(resumen_contratista, use_container_width=True, hide_index=True)

                    st.subheader("📋 Detalle de agenda")

                    columnas_vista = [
                        "cliente_nro",
                        "estado",
                        "contratista",
                        "tipo_trabajo",
                        "turno_agendamiento",
                        "dato_conexion",
                        "latitud",
                        "longitud"
                    ]

                    st.dataframe(
                        agenda_filtrada[columnas_vista],
                        use_container_width=True,
                        hide_index=True
                    )

                    st.subheader("📱 Reporte WhatsApp Agenda Técnica")

                    texto_agenda = "🗺️ AGENDA TÉCNICA DEL DÍA\n\n"

                    for contratista, grupo in agenda_filtrada.groupby("contratista"):
                        texto_agenda += f"👷 Contratista: {contratista}\n"
                        texto_agenda += f"📋 Total: {len(grupo)}\n\n"

                        for _, row in grupo.iterrows():
                            texto_agenda += (
                                f"🔹 {row['cliente_nro']} | {row['tipo_trabajo']} | {row['estado']} | {row['turno_agendamiento']}\n"
                            )

                        texto_agenda += "----------------------\n"

                    st.text_area("Mensaje agenda técnica", texto_agenda, height=420)

                    st.link_button(
                        "📲 Compartir agenda por WhatsApp",
                        "https://wa.me/?text=" + urllib.parse.quote(texto_agenda)
                    )

        except Exception as e:
            st.error(f"Error al procesar agenda técnica: {e}")
