import streamlit as st
import pandas as pd
import sqlite3
import urllib.parse
import re
from io import BytesIO

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
    <p>Seguimiento de objetivos, crosselling, instalados, pendientes y suspendidas</p>
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


SOCIOS_DICT = {
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

def convertir_excel_descarga(df_exportar, nombre_hoja="Datos"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_exportar.to_excel(writer, index=False, sheet_name=nombre_hoja)
    output.seek(0)
    return output

def extraer_telefonos_limpios(*valores):
    telefonos = []
    for valor in valores:
        if pd.isna(valor):
            continue
        texto = str(valor)
        encontrados = re.findall(r"\d{7,8}", texto)
        for tel in encontrados:
            if tel not in telefonos:
                telefonos.append(tel)
    return telefonos


def formatear_telefonos_whatsapp(*valores):
    telefonos = extraer_telefonos_limpios(*valores)
    if not telefonos:
        return "📞 Titular: Sin referencia\n"

    lineas = []
    lineas.append(f"📞 Titular: {telefonos[0]}")
    for i, tel in enumerate(telefonos[1:], start=1):
        lineas.append(f"📞 Ref. {i}: {tel}")
    return "\n".join(lineas) + "\n"


def obtener_codigo_minimo():
    valor = cursor.execute(
        "SELECT VALOR FROM configuracion WHERE CLAVE='codigo_minimo_objetivo'"
    ).fetchone()
    if valor:
        try:
            return int(valor[0])
        except Exception:
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


def analizar_crm_observacion(valor):
    obs = str(valor).strip()
    obs_lower = obs.lower()

    if obs == "" or obs_lower in ["nan", "none", "null"]:
        return "Sin CRM / suspendida sin razón"

    if any(x in obs_lower for x in ["no atend", "no se atend", "no atendida", "no atendido", "no contacto", "no contesta", "sin contacto"]):
        return "Instalación no atendida / contactar cliente"

    if any(x in obs_lower for x in ["desiste", "desist", "rechaza", "rechaz", "anula", "anulación", "anulacion", "cancel"]):
        return "Cliente desiste / validar cierre"

    if any(x in obs_lower for x in ["reagend", "agenda", "programar", "reprogram"]):
        return "Reagendar instalación"

    if any(x in obs_lower for x in ["tecnico", "técnico", "tap", "satur", "poste", "nodo", "factibilidad", "cobertura"]):
        return "Revisión técnica / validar con operaciones"

    return "Instalación suspendida / validar motivo"


# =========================
# CARGA GROSSADD
# =========================
codigo_minimo_objetivo = obtener_codigo_minimo()

st.info(
    f"🎯 Código mínimo para contar al objetivo: {codigo_minimo_objetivo}. "
    "Los códigos menores se mostrarán como 🔄 Crosselling y no sumarán al cumplimiento."
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 Dashboard",
    "🏆 Ranking",
    "🎯 Objetivos",
    "⚙️ Configuración",
    "📱 WhatsApp",
    "📋 Pendientes Instalación",
    "💳 Pendientes Pago",
    "🚨 Suspendidas"
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

    st.write("Puedes actualizar los objetivos de forma masiva subiendo un Excel con las columnas:")
    st.code("POS_CODE | POS_OWNER | BU JUNIO")

    archivo_objetivos = st.file_uploader(
        "📤 Subir archivo de objetivos",
        type=["csv", "xlsx"],
        key="objetivos_masivo"
    )

    if archivo_objetivos:
        try:
            obj = leer_archivo(archivo_objetivos)

            if obj is not None:
                obj = normalizar_columnas(obj)

                columnas_obj = ["POS_CODE", "POS_OWNER", "BU_JUNIO"]
                faltantes_obj = [c for c in columnas_obj if c not in obj.columns]

                if faltantes_obj:
                    st.error(f"Faltan columnas en el archivo de objetivos: {faltantes_obj}")
                    st.write("Columnas detectadas:")
                    st.write(list(obj.columns))
                else:
                    obj["POS_CODE"] = obj["POS_CODE"].astype(str)
                    obj["BU_JUNIO"] = pd.to_numeric(obj["BU_JUNIO"], errors="coerce").fillna(0).astype(int)

                    vista_obj = obj[["POS_CODE", "POS_OWNER", "BU_JUNIO"]].copy()
                    vista_obj.columns = ["EH", "NOMBRE", "OBJETIVO"]

                    st.success(f"Objetivos detectados: {len(vista_obj)} socios")
                    st.dataframe(vista_obj, use_container_width=True, hide_index=True)

                    if st.button("💾 Guardar objetivos desde archivo"):
                        for _, row in vista_obj.iterrows():
                            cursor.execute("""
                                INSERT INTO objetivos (EH, NOMBRE, OBJETIVO)
                                VALUES (?, ?, ?)
                                ON CONFLICT(EH) DO UPDATE SET
                                    NOMBRE=excluded.NOMBRE,
                                    OBJETIVO=excluded.OBJETIVO
                            """, (
                                str(row["EH"]),
                                str(row["NOMBRE"]),
                                int(row["OBJETIVO"])
                            ))

                        conn.commit()
                        st.success("Objetivos actualizados correctamente. Presiona F5 para recalcular el dashboard.")

        except Exception as e:
            st.error(f"Error al procesar objetivos: {e}")

    st.divider()

    st.subheader("✍️ Edición manual de objetivos")

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

            if st.form_submit_button("💾 Guardar objetivos manuales"):
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
        st.info("También puedes editar manualmente después de subir el GrossAdd.")


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
                "Seguimiento individual con códigos instalados",
                "Reporte general"
            ]
        )

        if opcion in ["Resumen individual", "Seguimiento individual con códigos instalados"]:
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

            if opcion == "Seguimiento individual con códigos instalados":
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
# PENDIENTES INSTALACIÓN
# =========================
with tab6:
    st.subheader("📋 Pendientes de Instalación")

    st.write("Sube el archivo PENDIENTE_INST_CON_PAGO, selecciona un socio y envía sus códigos por WhatsApp.")

    archivo_pendientes_inst = st.file_uploader(
        "📤 Sube archivo Pendientes de Instalación",
        type=["csv", "xlsx"],
        key="pendientes_instalacion"
    )

    def analizar_crm_motivo(valor):
        motivo = str(valor).strip()
        motivo_lower = motivo.lower()

        if motivo == "" or motivo_lower in ["nan", "none", "null"]:
            return "Sin CRM / sin motivo registrado"

        if any(x in motivo_lower for x in ["no atend", "no se atend", "no contact", "no contesta", "sin contacto"]):
            return "Instalación no atendida / contactar cliente"

        if any(x in motivo_lower for x in ["pendiente", "pago", "sin pago"]):
            return "Pendiente de validación de pago"

        if any(x in motivo_lower for x in ["reagend", "agenda", "programar", "reprogram"]):
            return "Reagendar instalación"

        if any(x in motivo_lower for x in ["tap", "satur", "nodo", "técnic", "tecnic", "cobertura", "factibilidad", "poste"]):
            return "Revisión técnica / validar con operaciones"

        if any(x in motivo_lower for x in ["cliente", "desiste", "rechaza", "anula", "cancel"]):
            return "Validar con cliente / posible desistimiento"

        return motivo

    if archivo_pendientes_inst:
        try:
            pend_inst = leer_archivo(archivo_pendientes_inst)

            if pend_inst is not None:
                pend_inst = normalizar_columnas(pend_inst)
                st.success(f"Archivo cargado: {len(pend_inst)} registros")

                if len(pend_inst) == 0:
                    st.warning("El archivo no tiene registros pendientes. Solo tiene encabezados, por eso no aparecen socios para seleccionar.")
                    st.stop()

                columnas_base = [
                    "CLIENTE_NRO",
                    "FECHA_REPORTE",
                    "VENDEDOR_EH",
                    "NODO_NOMBRE",
                    "CRM_MOTIVO"
                ]

                faltantes = [c for c in columnas_base if c not in pend_inst.columns]

                if faltantes:
                    st.error(f"Faltan columnas: {faltantes}")
                    st.write("Columnas detectadas:")
                    st.write(list(pend_inst.columns))
                else:
                    pend_inst["VENDEDOR_EH"] = pend_inst["VENDEDOR_EH"].astype(str)

                    if "VENDEDOR_NOMBRE" in pend_inst.columns:
                        pend_inst["SOCIO"] = pend_inst["VENDEDOR_NOMBRE"].astype(str)
                    else:
                        pend_inst["SOCIO"] = pend_inst["VENDEDOR_EH"].map(SOCIOS_DICT).fillna("SIN NOMBRE")

                    pend_inst["SOCIO_DISPLAY"] = pend_inst["VENDEDOR_EH"] + " - " + pend_inst["SOCIO"]
                    pend_inst["ANALISIS_CRM"] = pend_inst["CRM_MOTIVO"].apply(analizar_crm_motivo)

                    socios_inst = (
                        pend_inst.groupby(["VENDEDOR_EH", "SOCIO", "SOCIO_DISPLAY"])
                        .agg(Pendientes=("CLIENTE_NRO", "count"))
                        .reset_index()
                        .sort_values("SOCIO")
                    )

                    if len(socios_inst) == 0:
                        st.warning("No hay socios con pendientes en este archivo.")
                        st.stop()

                    socios_inst["MOSTRAR"] = (
                        socios_inst["SOCIO_DISPLAY"]
                        + " ("
                        + socios_inst["Pendientes"].astype(str)
                        + " pendientes)"
                    )

                    socio_sel = st.selectbox(
                        "Selecciona socio",
                        socios_inst["MOSTRAR"].tolist(),
                        key="sel_pend_inst"
                    )

                    socio_display = socios_inst[
                        socios_inst["MOSTRAR"] == socio_sel
                    ]["SOCIO_DISPLAY"].iloc[0]

                    detalle = pend_inst[
                        pend_inst["SOCIO_DISPLAY"] == socio_display
                    ].copy()

                    if len(detalle) == 0:
                        st.warning("No hay pendientes para el socio seleccionado.")
                        st.stop()

                    eh = str(detalle.iloc[0]["VENDEDOR_EH"])
                    nombre = str(detalle.iloc[0]["SOCIO"])

                    st.metric("📌 Pendientes de instalación", len(detalle))

                    columnas_mostrar = [
                        "CLIENTE_NRO",
                        "FECHA_REPORTE",
                        "VENDEDOR_EH",
                        "SOCIO",
                        "NODO_NOMBRE",
                        "CRM_MOTIVO",
                        "ANALISIS_CRM"
                    ]

                    if "CLIENTE_TELEFONO1" in detalle.columns:
                        columnas_mostrar.append("CLIENTE_TELEFONO1")
                    if "CLIENTE_TELEFONO2" in detalle.columns:
                        columnas_mostrar.append("CLIENTE_TELEFONO2")

                    st.dataframe(
                        detalle[columnas_mostrar],
                        use_container_width=True,
                        hide_index=True
                    )

                    texto = "📋 PENDIENTES DE INSTALACIÓN\n\n"
                    texto += f"👤 Socio: {nombre}\n"
                    texto += f"EH: {eh}\n"
                    texto += f"📌 Total pendientes: {len(detalle)}\n\n"

                    for _, row in detalle.iterrows():
                        telefono_1 = row["CLIENTE_TELEFONO1"] if "CLIENTE_TELEFONO1" in detalle.columns else ""
                        telefono_2 = row["CLIENTE_TELEFONO2"] if "CLIENTE_TELEFONO2" in detalle.columns else ""
                        telefonos_txt = formatear_telefonos_whatsapp(telefono_1, telefono_2)

                        texto += (
                            f"🔹 Código: {row['CLIENTE_NRO']}\n"
                            f"📅 Generado: {row['FECHA_REPORTE']}\n"
                            f"📍 Nodo: {row['NODO_NOMBRE']}\n"
                            f"{telefonos_txt}"
                            f"📝 CRM: {row['ANALISIS_CRM']}\n\n"
                        )


                    # Descargar Excel unificado
                    columnas_exportar = [c for c in [
                        "CLIENTE_NRO",
                        "FECHA_REPORTE",
                        "VENDEDOR_EH",
                        "VENDEDOR_NOMBRE",
                        "CLIENTE_NOMBRE",
                        "NODO_NOMBRE",
                        "CRM_MOTIVO",
                        "ANALISIS_CRM",
                        "CLIENTE_TELEFONO1",
                        "CLIENTE_TELEFONO2"
                    ] if c in detalle.columns]

                    excel_unificado = convertir_excel_descarga(
                        detalle[columnas_exportar],
                        "Pendientes"
                    )

                    st.download_button(
                        label="📥 Descargar Excel unificado",
                        data=excel_unificado,
                        file_name=f"pendientes_instalacion_{eh}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                    st.text_area("Mensaje WhatsApp", texto, height=520, key=f"txt_pend_inst_{eh}")
                    st.link_button("📲 Compartir por WhatsApp", "https://wa.me/?text=" + urllib.parse.quote(texto))

        except Exception as e:
            st.error(f"Error al procesar pendientes de instalación: {e}")


# =========================
# PENDIENTES PAGO
# =========================
with tab7:
    st.subheader("💳 Pendientes de Pago")

    st.write("Sube el archivo PENDIENTE_INST_SIN_PAGO, selecciona un socio y envía sus pendientes por WhatsApp.")

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
                    pagos["SOCIO"] = pagos["VENDEDOR_EH"].map(SOCIOS_DICT).fillna("SIN NOMBRE")
                    pagos["SOCIO_DISPLAY"] = pagos["VENDEDOR_EH"] + " - " + pagos["SOCIO"]

                    socios_con_pendientes = (
                        pagos[["VENDEDOR_EH", "SOCIO", "SOCIO_DISPLAY"]]
                        .drop_duplicates()
                        .sort_values("SOCIO")
                    )

                    socio_sel = st.selectbox("Selecciona socio", socios_con_pendientes["SOCIO_DISPLAY"], key="sel_pago")
                    detalle = pagos[pagos["SOCIO_DISPLAY"] == socio_sel].copy()

                    eh = detalle.iloc[0]["VENDEDOR_EH"]
                    nombre = detalle.iloc[0]["SOCIO"]

                    st.metric("📌 Pendientes de pago", len(detalle))

                    texto = "💳 PENDIENTES DE PAGO\n\n"
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

                    st.text_area("Mensaje WhatsApp", texto, height=500, key="txt_pago")
                    st.link_button("📲 Compartir por WhatsApp", "https://wa.me/?text=" + urllib.parse.quote(texto))

        except Exception as e:
            st.error(f"Error al procesar pendientes de pago: {e}")


# =========================
# SUSPENDIDAS
# =========================
with tab8:
    st.subheader("🚨 Suspendidas / Instalaciones no atendidas")

    st.write("Sube el archivo diario de suspendidas para analizar CRM_OBSERVACION y generar reclamos por socio para WhatsApp.")

    archivo_suspendidas = st.file_uploader(
        "📤 Sube archivo Suspendidas",
        type=["csv", "xlsx"],
        key="suspendidas"
    )

    if archivo_suspendidas:
        try:
            susp = leer_archivo(archivo_suspendidas)

            if susp is not None:
                susp = normalizar_columnas(susp)
                st.success(f"Archivo cargado: {len(susp)} registros")

                columnas = [
                    "CLIENTE_NRO",
                    "FECHA_REPORTE",
                    "VENDEDOR_EH",
                    "VENDEDOR_NOMBRE",
                    "TIPO_VENTA",
                    "CLIENTE_TELEFONO1",
                    "NODO_NOMBRE",
                    "CRM_OBSERVACION"
                ]

                faltantes = [c for c in columnas if c not in susp.columns]

                if faltantes:
                    st.error(f"Faltan columnas: {faltantes}")
                    st.write("Columnas detectadas:")
                    st.write(list(susp.columns))
                else:
                    susp["VENDEDOR_EH"] = susp["VENDEDOR_EH"].astype(str)
                    susp["OBSERVACION_SUGERIDA"] = susp["CRM_OBSERVACION"].apply(analizar_crm_observacion)
                    susp["SOCIO_DISPLAY"] = susp["VENDEDOR_EH"] + " - " + susp["VENDEDOR_NOMBRE"].astype(str)

                    socios_susp = (
                        susp[["VENDEDOR_EH", "VENDEDOR_NOMBRE", "SOCIO_DISPLAY"]]
                        .drop_duplicates()
                        .sort_values("VENDEDOR_NOMBRE")
                    )

                    socio_sel = st.selectbox("Selecciona socio", socios_susp["SOCIO_DISPLAY"], key="sel_susp")
                    detalle = susp[susp["SOCIO_DISPLAY"] == socio_sel].copy()

                    eh = detalle.iloc[0]["VENDEDOR_EH"]
                    nombre = detalle.iloc[0]["VENDEDOR_NOMBRE"]

                    st.metric("🚨 Suspendidas", len(detalle))

                    texto = "🚨 SUSPENDIDAS / INSTALACIONES NO ATENDIDAS\n\n"
                    texto += f"👤 Socio: {nombre}\n"
                    texto += f"EH: {eh}\n"
                    texto += f"📌 Total casos: {len(detalle)}\n\n"

                    for _, row in detalle.iterrows():
                        texto += (
                            f"🔹 Código: {row['CLIENTE_NRO']}\n"
                            f"📅 Reporte: {row['FECHA_REPORTE']}\n"
                            f"📞 Tel: {row['CLIENTE_TELEFONO1']}\n"
                            f"📍 Nodo: {row['NODO_NOMBRE']}\n"
                            f"🧾 Tipo venta: {row['TIPO_VENTA']}\n"
                            f"📝 Observación: {row['OBSERVACION_SUGERIDA']}\n\n"
                        )

                    st.text_area("Mensaje WhatsApp", texto, height=520, key="txt_susp")
                    st.link_button("📲 Compartir por WhatsApp", "https://wa.me/?text=" + urllib.parse.quote(texto))

                    st.subheader("📋 Detalle analizado")
                    st.dataframe(
                        detalle[[
                            "CLIENTE_NRO",
                            "FECHA_REPORTE",
                            "VENDEDOR_EH",
                            "VENDEDOR_NOMBRE",
                            "TIPO_VENTA",
                            "CLIENTE_TELEFONO1",
                            "NODO_NOMBRE",
                            "CRM_OBSERVACION",
                            "OBSERVACION_SUGERIDA"
                        ]],
                        use_container_width=True,
                        hide_index=True
                    )

        except Exception as e:
            st.error(f"Error al procesar suspendidas: {e}")
