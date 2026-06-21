# agenda_tecnica_v2.py
# Módulo Streamlit: Agenda Técnica / Instalaciones de Hoy
# Versión 2: fecha automática según archivo + diagnóstico + compatibilidad Streamlit

from __future__ import annotations

from datetime import datetime, date
from io import BytesIO
from urllib.parse import quote
import re

import pandas as pd

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None


SOCIOS_EH = {
    "59509": "Adriana Paola Villafuerte Guerra",
    "63483": "Franklin Ramiro Quispe Rosas",
    "89859": "José Pablo Fernández Puente",
    "88463": "Alicia Graciela Zamora Buezo",
    "88426": "Sonia Noemí Mayta",
    "58984": "María Surco Aruquipa",
    "78099": "Geovana Carla Siñani Luna",
    "78340": "Olivia Sánchez Quispe",
    "89326": "Palmira Selaes Herrera",
    "83457": "Estrella Belén Quispe Flores",
    "89231": "Alex Rudy Mamani Guarachi",
    "72210": "Guadalupe Apaza Vila",
    "67755": "Sandro Iván Copa Velasco",
    "86737": "Anahi Oinca",
    "86963": "Teresa Eugenia Chipana Mamani De Sayes",
    "79030": "Víctor Hugo Chambilla Flores",
    "88874": "Gustavo Callejas Mamani",
    "77735": "Claudia Michme Ajno",
    "87933": "Pamela Mery Rojas Alarcón",
    "78272": "My Phone SRL",
}


# -------------------------
# Limpieza / normalización
# -------------------------
def fecha_hoy_bolivia() -> date:
    if ZoneInfo is None:
        return date.today()
    return datetime.now(ZoneInfo("America/La_Paz")).date()


def limpiar_texto(valor) -> str:
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def limpiar_codigo(valor) -> str:
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return re.sub(r"[^0-9A-Za-z-]", "", texto)


def limpiar_eh(valor) -> str:
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return re.sub(r"\D", "", texto)


def normalizar_nombre_columna(columna: str) -> str:
    texto = str(columna).strip().lower()
    reemplazos = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n",
        "/": "_", "-": "_", ".": "_", " ": "_",
    }
    for a, b in reemplazos.items():
        texto = texto.replace(a, b)
    texto = re.sub(r"_+", "_", texto)
    return texto.strip("_")


def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [normalizar_nombre_columna(c) for c in df.columns]
    return df


def col_existente(df: pd.DataFrame, opciones: list[str]) -> str | None:
    for c in opciones:
        c_norm = normalizar_nombre_columna(c)
        if c_norm in df.columns:
            return c_norm
    return None


def serie_col(df: pd.DataFrame, opciones: list[str]) -> pd.Series:
    c = col_existente(df, opciones)
    if c is None:
        return pd.Series([""] * len(df), index=df.index)
    return df[c]


def extraer_nodo(*valores) -> str:
    texto = " ".join(limpiar_texto(v).upper() for v in valores if limpiar_texto(v))
    if not texto:
        return ""
    texto = texto.replace("-", " ").replace("_", " ")
    texto = re.sub(r"\s+", " ", texto)
    patron = r"\b(EAL\s*\d{3,4}|LPZ\s*\d{3,4}|EAF\s*\d{3,4}|SCZ\s*\d{3,4}|PTS\s*\d{3,4}|[A-Z]{3}\s*\d{3,4})\b"
    m = re.search(patron, texto)
    return m.group(1).replace(" ", "") if m else ""


def leer_archivo_agenda(archivo) -> pd.DataFrame:
    nombre = getattr(archivo, "name", "").lower()
    if nombre.endswith(".csv"):
        return pd.read_csv(archivo)
    return pd.read_excel(archivo, engine="openpyxl")


# -------------------------
# Procesamiento
# -------------------------
def preparar_base(df_original: pd.DataFrame) -> pd.DataFrame:
    df = normalizar_columnas(df_original)

    col_fecha = col_existente(df, ["inicio_agendado", "inicio cita", "inicio_cita", "fecha_agendada", "data_agendamiento"])
    col_tipo = col_existente(df, ["tipo_trabajo_op", "tipo_trabajo", "tipo trabajo op", "tipo trabajo"])
    col_eh = col_existente(df, ["ehumano_promotor", "eh_promotor", "eh", "vendedor_eh", "codigo_eh"])

    faltantes = []
    if col_fecha is None:
        faltantes.append("inicio_agendado")
    if col_tipo is None:
        faltantes.append("tipo_trabajo_op")
    if col_eh is None:
        faltantes.append("ehumano_promotor")
    if faltantes:
        raise ValueError("Faltan columnas requeridas: " + ", ".join(faltantes))

    # Pandas detecta correctamente fechas tipo 2026-06-20 y también fechas Excel.
    # No forzamos dayfirst para evitar advertencias en Streamlit.
    df["_fecha_agendada"] = pd.to_datetime(df[col_fecha], errors="coerce").dt.date
    df["_tipo_op"] = df[col_tipo].fillna("").astype(str).str.upper().str.strip()
    df["_eh"] = df[col_eh].apply(limpiar_eh)
    return df


def fechas_disponibles(df_preparado: pd.DataFrame) -> list[date]:
    fechas = sorted([f for f in df_preparado["_fecha_agendada"].dropna().unique()])
    return fechas


def procesar_agenda(df_original: pd.DataFrame, fecha_consulta: date) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    df = preparar_base(df_original)

    es_fecha = df["_fecha_agendada"] == fecha_consulta
    es_instalacion = df["_tipo_op"].str.contains("INSTALACION", na=False)
    es_socio = df["_eh"].isin(SOCIOS_EH.keys())

    df_filtrado = df[es_fecha & es_instalacion & es_socio].copy()

    diagnostico = {
        "total_filas": int(len(df)),
        "filas_fecha": int(es_fecha.sum()),
        "filas_instalacion": int((es_fecha & es_instalacion).sum()),
        "filas_socios": int((es_fecha & es_instalacion & es_socio).sum()),
        "fechas": fechas_disponibles(df),
    }

    columnas_detalle = [
        "EH", "Socio", "Código cliente", "Nodo", "Cliente", "Teléfono", "Ciudad",
        "Turno", "Hora inicio", "Contratista", "Técnico", "Estado", "Confirmación", "Dirección/Dato conexión",
    ]

    if df_filtrado.empty:
        detalle = pd.DataFrame(columns=columnas_detalle)
    else:
        detalle = pd.DataFrame({
            "EH": df_filtrado["_eh"],
            "Socio": df_filtrado["_eh"].map(SOCIOS_EH),
            "Código cliente": serie_col(df_filtrado, ["cliente_nro", "codigo_cliente", "cod_cliente", "cliente"]).apply(limpiar_codigo),
            "Nodo": df_filtrado.apply(
                lambda r: extraer_nodo(
                    r.get("dato_onexion", ""),
                    r.get("dato_conexion", ""),
                    r.get("zona_ramal", ""),
                    r.get("tap_nap", ""),
                    r.get("descripcion", ""),
                    r.get("comentario", ""),
                ),
                axis=1,
            ),
            "Cliente": serie_col(df_filtrado, ["nombre_contacto", "cliente_nombre", "nombre_cliente"]).apply(limpiar_texto),
            "Teléfono": serie_col(df_filtrado, ["numero_telefono_cliente", "cliente_telefono1", "cliente_telefono2", "telefono"]).apply(limpiar_texto),
            "Ciudad": serie_col(df_filtrado, ["ciudad"]).apply(limpiar_texto),
            "Turno": serie_col(df_filtrado, ["turno_agendamiento", "rango_cita_acordada_con_cliente", "turno"]).apply(limpiar_texto),
            "Hora inicio": serie_col(df_filtrado, ["hora_inicio", "inicio_cita"]).apply(limpiar_texto),
            "Contratista": serie_col(df_filtrado, ["contratista"]).apply(limpiar_texto),
            "Técnico": serie_col(df_filtrado, ["tecnico_nombre", "tecnico"]).apply(limpiar_texto),
            "Estado": serie_col(df_filtrado, ["estado"]).apply(limpiar_texto),
            "Confirmación": serie_col(df_filtrado, ["estado_confirmacion", "confirmacion"]).apply(limpiar_texto),
            "Dirección/Dato conexión": serie_col(df_filtrado, ["dato_onexion", "dato_conexion", "descripcion", "comentario"]).apply(limpiar_texto),
        })
        detalle = detalle.sort_values(["Socio", "Código cliente"], ascending=[True, True]).reset_index(drop=True)

    resumen = (
        detalle.groupby(["EH", "Socio"], as_index=False)["Código cliente"]
        .count()
        .rename(columns={"Código cliente": "Instalaciones"})
        .sort_values("Instalaciones", ascending=False)
        .reset_index(drop=True)
    ) if not detalle.empty else pd.DataFrame(columns=["EH", "Socio", "Instalaciones"])

    socios_df = pd.DataFrame({"EH": list(SOCIOS_EH.keys()), "Socio": list(SOCIOS_EH.values())})
    sin_instalacion = socios_df[~socios_df["EH"].isin(resumen["EH"] if not resumen.empty else [])].copy()
    sin_instalacion = sin_instalacion.sort_values("Socio").reset_index(drop=True)

    return resumen, detalle, sin_instalacion, diagnostico


# -------------------------
# Mensajes / exportación
# -------------------------
def nombre_corto(nombre: str) -> str:
    partes = str(nombre).split()
    return " ".join(partes[:2]) if len(partes) >= 2 else str(nombre)


def mensaje_whatsapp_general(resumen: pd.DataFrame, fecha_consulta: date) -> str:
    total = int(resumen["Instalaciones"].sum()) if not resumen.empty else 0
    fecha_txt = fecha_consulta.strftime("%d/%m/%Y")
    socios_con_agenda = resumen["EH"].nunique() if not resumen.empty else 0

    lineas = [
        "📌 *AGENDA TÉCNICA DEL DÍA*",
        f"📅 Fecha: *{fecha_txt}*",
        f"🔧 Total instalaciones: *{total}*",
        f"👥 Socios con agenda: *{socios_con_agenda}*",
        "",
    ]

    if resumen.empty:
        lineas += [
            "⚠️ No se encontraron instalaciones programadas para los EH configurados.",
            "",
            "Por favor validar si el archivo corresponde a la fecha correcta.",
        ]
        return "\n".join(lineas)

    lineas.append("📋 *Resumen por socio:*")
    for i, (_, r) in enumerate(resumen.iterrows(), start=1):
        medalla = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🔹"
        lineas.append(
            f"{medalla} *{r['EH']}* - {nombre_corto(r['Socio'])}: *{int(r['Instalaciones'])}* inst."
        )

    lineas += [
        "",
        "✅ *Acción requerida:*",
        "Por favor realizar seguimiento temprano, confirmar contacto con el cliente y reportar cualquier inconveniente durante el día.",
    ]
    return "\n".join(lineas)

def mensaje_whatsapp_socio(detalle_socio: pd.DataFrame, fecha_consulta: date) -> str:
    if detalle_socio.empty:
        return ""

    eh = detalle_socio.iloc[0]["EH"]
    socio = detalle_socio.iloc[0]["Socio"]
    fecha_txt = fecha_consulta.strftime("%d/%m/%Y")

    lineas = [
        "📌 *AGENDA TÉCNICA DEL DÍA*",
        "",
        f"📅 *Fecha:* {fecha_txt}",
        f"👤 *Socio:* {socio}",
        f"🆔 *EH:* {eh}",
        f"🔧 *Total:* {len(detalle_socio)} instalaciones",
        "",
        "📋 *Clientes agendados:*",
    ]

    for i, (_, r) in enumerate(detalle_socio.iterrows(), start=1):
        codigo = r.get("Código cliente", "") or "S/D"
        nodo = r.get("Nodo", "") or "S/D"
        turno = r.get("Turno", "") or "S/D"
        lineas.append(f"{i}. {codigo} | {nodo} | {turno}")

    lineas += [
        "",
        "✅ Favor realizar seguimiento y reportar cualquier observación.",
    ]
    return "
".join(lineas)


def generar_excel(resumen: pd.DataFrame, detalle: pd.DataFrame, sin_instalacion: pd.DataFrame, diagnostico: dict) -> BytesIO:
    salida = BytesIO()
    diag_df = pd.DataFrame({
        "Métrica": ["Total filas", "Filas fecha", "Filas instalación", "Filas socios"],
        "Valor": [
            diagnostico.get("total_filas", 0),
            diagnostico.get("filas_fecha", 0),
            diagnostico.get("filas_instalacion", 0),
            diagnostico.get("filas_socios", 0),
        ],
    })
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        resumen.to_excel(writer, index=False, sheet_name="Resumen")
        detalle.to_excel(writer, index=False, sheet_name="Detalle")
        sin_instalacion.to_excel(writer, index=False, sheet_name="Sin instalacion")
        diag_df.to_excel(writer, index=False, sheet_name="Diagnostico")
        for hoja in writer.book.worksheets:
            hoja.freeze_panes = "A2"
            for col in hoja.columns:
                col_letter = col[0].column_letter
                max_len = max(len(str(cell.value)) if cell.value is not None else 0 for cell in col)
                hoja.column_dimensions[col_letter].width = min(max(max_len + 2, 10), 45)
    salida.seek(0)
    return salida


def link_whatsapp(texto: str) -> str:
    return "https://wa.me/?text=" + quote(texto)


def fecha_txt(fecha: date) -> str:
    return fecha.strftime("%d/%m/%Y")


# -------------------------
# Interfaz Streamlit
# -------------------------
def mostrar_agenda_tecnica():
    import streamlit as st

    st.title("📅 Agenda Técnica / Instalaciones de Hoy")
    st.caption("Carga el archivo BO-CITA SERVICIO NACIONAL. El sistema detecta las fechas del archivo y filtra solo instalaciones de tus EH.")

    archivo = st.file_uploader(
        "Subir archivo de agenda técnica",
        type=["xlsx", "xls", "csv"],
        key="agenda_tecnica_uploader_v2",
    )

    if archivo is None:
        st.warning("Sube el archivo diario para generar el reporte.")
        return

    try:
        df_original = leer_archivo_agenda(archivo)
        df_preparado = preparar_base(df_original)
        fechas = fechas_disponibles(df_preparado)
    except Exception as e:
        st.error(f"No se pudo leer el archivo: {e}")
        st.info("Verifica que el archivo tenga las columnas: inicio_agendado, tipo_trabajo_op y ehumano_promotor.")
        return

    if not fechas:
        st.error("El archivo no tiene fechas válidas en la columna inicio_agendado.")
        return

    hoy = fecha_hoy_bolivia()
    fecha_default = hoy if hoy in fechas else max(fechas)

    if hoy not in fechas:
        st.warning(f"La fecha de hoy ({fecha_txt(hoy)}) no aparece en el archivo. Se seleccionó automáticamente la última fecha encontrada: {fecha_txt(fecha_default)}.")

    opciones_fecha = [fecha_txt(f) for f in fechas]
    index_default = fechas.index(fecha_default)
    fecha_sel_txt = st.selectbox("Fecha a consultar", opciones_fecha, index=index_default, key="agenda_fecha_select_v2")
    fecha_consulta = fechas[opciones_fecha.index(fecha_sel_txt)]

    try:
        resumen, detalle, sin_instalacion, diagnostico = procesar_agenda(df_original, fecha_consulta)
    except Exception as e:
        st.error(f"No se pudo procesar el archivo: {e}")
        return

    total = int(resumen["Instalaciones"].sum()) if not resumen.empty else 0
    socios_con_instalacion = resumen["EH"].nunique() if not resumen.empty else 0

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Instalaciones", total)
    kpi2.metric("Socios con agenda", socios_con_instalacion)
    kpi3.metric("Socios sin agenda", len(sin_instalacion))

    with st.expander("Diagnóstico del archivo"):
        st.write(f"Total filas del archivo: **{diagnostico['total_filas']}**")
        st.write(f"Filas con fecha seleccionada: **{diagnostico['filas_fecha']}**")
        st.write(f"Filas con tipo instalación en esa fecha: **{diagnostico['filas_instalacion']}**")
        st.write(f"Filas de tus EH en esa fecha: **{diagnostico['filas_socios']}**")
        st.write("Fechas encontradas:", ", ".join(fecha_txt(f) for f in fechas))

    st.subheader("Resumen por socio")
    st.dataframe(resumen, use_container_width=True, hide_index=True)

    st.subheader("Detalle de instalaciones")
    st.dataframe(detalle, use_container_width=True, hide_index=True)

    st.subheader("Mensaje general para WhatsApp")
    texto_general = mensaje_whatsapp_general(resumen, fecha_consulta)
    st.text_area("Copiar mensaje", texto_general, height=230, key="mensaje_general_agenda_v2")
    st.markdown(f"[Enviar por WhatsApp]({link_whatsapp(texto_general)})")

    st.subheader("Mensaje por socio")
    if detalle.empty:
        st.info("No hay detalle por socio para la fecha seleccionada.")
    else:
        opciones = [f"{eh} - {SOCIOS_EH[eh]}" for eh in sorted(detalle["EH"].unique())]
        seleccion = st.selectbox("Selecciona socio", opciones, key="agenda_socio_select_v2")
        eh_sel = seleccion.split(" - ")[0]
        detalle_socio = detalle[detalle["EH"] == eh_sel]
        texto_socio = mensaje_whatsapp_socio(detalle_socio, fecha_consulta)
        st.text_area("Mensaje individual", texto_socio, height=220, key="mensaje_socio_agenda_v2")
        st.markdown(f"[Enviar mensaje individual por WhatsApp]({link_whatsapp(texto_socio)})")

    with st.expander("Socios sin instalaciones para la fecha"):
        st.dataframe(sin_instalacion, use_container_width=True, hide_index=True)

    with st.expander("EH configurados"):
        socios_df = pd.DataFrame({"EH": list(SOCIOS_EH.keys()), "Socio": list(SOCIOS_EH.values())})
        st.dataframe(socios_df, use_container_width=True, hide_index=True)

    excel = generar_excel(resumen, detalle, sin_instalacion, diagnostico)
    nombre_excel = f"agenda_tecnica_{fecha_consulta.strftime('%Y%m%d')}.xlsx"
    st.download_button(
        "⬇️ Descargar Excel del reporte",
        data=excel,
        file_name=nombre_excel,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="descargar_agenda_v2",
    )
