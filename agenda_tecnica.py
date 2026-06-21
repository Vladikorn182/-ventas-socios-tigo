# agenda_tecnica.py
# Módulo Streamlit: Agenda Técnica / Instalaciones de Hoy
# Autor: Vladimir Cuenca / ChatGPT

from __future__ import annotations

from datetime import datetime, date
from io import BytesIO
from urllib.parse import quote
import re

import pandas as pd

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None


# =========================
# Socios EH configurados
# =========================
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


# =========================
# Utilidades
# =========================
def fecha_hoy_bolivia() -> date:
    if ZoneInfo is None:
        return date.today()
    return datetime.now(ZoneInfo("America/La_Paz")).date()


def limpiar_texto(valor) -> str:
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def limpiar_codigo(valor) -> str:
    """Convierte códigos numéricos de Excel a texto limpio: 2683049.0 -> 2683049."""
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    texto = re.sub(r"[^0-9A-Za-z-]", "", texto)
    return texto


def limpiar_eh(valor) -> str:
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return re.sub(r"\D", "", texto)


def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df


def extraer_nodo(*valores) -> str:
    """Extrae nodo desde campos como dato_onexion, zona_ramal o texto libre."""
    texto = " ".join(limpiar_texto(v).upper() for v in valores if limpiar_texto(v))
    if not texto:
        return ""

    # Ejemplos esperados: NODO EAL001 RAMAL..., LPZ556, EAF3345, EAL 400
    texto = texto.replace("-", " ").replace("_", " ")
    texto = re.sub(r"\s+", " ", texto)

    patron = r"\b(EAL\s*\d{3,4}|LPZ\s*\d{3,4}|EAF\s*\d{3,4}|SCZ\s*\d{3,4}|PTS\s*\d{3,4}|[A-Z]{3}\s*\d{3,4})\b"
    m = re.search(patron, texto)
    if m:
        return m.group(1).replace(" ", "")
    return ""


def leer_archivo_agenda(archivo) -> pd.DataFrame:
    nombre = archivo.name.lower()
    if nombre.endswith(".csv"):
        return pd.read_csv(archivo)
    return pd.read_excel(archivo)


def validar_columnas(df: pd.DataFrame) -> list[str]:
    necesarias = ["inicio_agendado", "tipo_trabajo_op", "ehumano_promotor"]
    faltantes = [c for c in necesarias if c not in df.columns]
    return faltantes


# =========================
# Procesamiento principal
# =========================
def procesar_agenda(df_original: pd.DataFrame, fecha_consulta: date) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = normalizar_columnas(df_original)

    faltantes = validar_columnas(df)
    if faltantes:
        raise ValueError("Faltan columnas requeridas en el archivo: " + ", ".join(faltantes))

    df["_fecha_agendada"] = pd.to_datetime(df["inicio_agendado"], errors="coerce").dt.date
    df["_tipo_op"] = df["tipo_trabajo_op"].fillna("").astype(str).str.upper().str.strip()
    df["_eh"] = df["ehumano_promotor"].apply(limpiar_eh)

    df_filtrado = df[
        (df["_fecha_agendada"] == fecha_consulta)
        & (df["_tipo_op"] == "INSTALACION")
        & (df["_eh"].isin(SOCIOS_EH.keys()))
    ].copy()

    if df_filtrado.empty:
        detalle = pd.DataFrame(columns=[
            "EH", "Socio", "Código cliente", "Nodo", "Cliente", "Teléfono", "Ciudad",
            "Turno", "Hora inicio", "Contratista", "Técnico", "Estado", "Confirmación", "Dirección/Dato conexión"
        ])
    else:
        detalle = pd.DataFrame({
            "EH": df_filtrado["_eh"],
            "Socio": df_filtrado["_eh"].map(SOCIOS_EH),
            "Código cliente": df_filtrado.get("cliente_nro", pd.Series(index=df_filtrado.index)).apply(limpiar_codigo),
            "Nodo": df_filtrado.apply(
                lambda r: extraer_nodo(
                    r.get("dato_onexion", ""),
                    r.get("zona_ramal", ""),
                    r.get("descripcion", ""),
                    r.get("comentario", ""),
                ),
                axis=1,
            ),
            "Cliente": df_filtrado.get("nombre_contacto", pd.Series(index=df_filtrado.index)).apply(limpiar_texto),
            "Teléfono": df_filtrado.get("numero_telefono_cliente", pd.Series(index=df_filtrado.index)).apply(limpiar_texto),
            "Ciudad": df_filtrado.get("ciudad", pd.Series(index=df_filtrado.index)).apply(limpiar_texto),
            "Turno": df_filtrado.get("turno_agendamiento", pd.Series(index=df_filtrado.index)).apply(limpiar_texto),
            "Hora inicio": df_filtrado.get("hora_inicio", pd.Series(index=df_filtrado.index)).apply(limpiar_texto),
            "Contratista": df_filtrado.get("contratista", pd.Series(index=df_filtrado.index)).apply(limpiar_texto),
            "Técnico": df_filtrado.get("tecnico_nombre", pd.Series(index=df_filtrado.index)).apply(limpiar_texto),
            "Estado": df_filtrado.get("estado", pd.Series(index=df_filtrado.index)).apply(limpiar_texto),
            "Confirmación": df_filtrado.get("estado_confirmacion", pd.Series(index=df_filtrado.index)).apply(limpiar_texto),
            "Dirección/Dato conexión": df_filtrado.get("dato_onexion", pd.Series(index=df_filtrado.index)).apply(limpiar_texto),
        })

        detalle = detalle.sort_values(["Socio", "Código cliente"], ascending=[True, True]).reset_index(drop=True)

    resumen = (
        detalle.groupby(["EH", "Socio"], as_index=False)["Código cliente"]
        .count()
        .rename(columns={"Código cliente": "Instalaciones"})
        .sort_values("Instalaciones", ascending=False)
        .reset_index(drop=True)
    )

    socios_df = pd.DataFrame({"EH": list(SOCIOS_EH.keys()), "Socio": list(SOCIOS_EH.values())})
    sin_instalacion = socios_df[~socios_df["EH"].isin(resumen["EH"] if not resumen.empty else [])].copy()
    sin_instalacion = sin_instalacion.sort_values("Socio").reset_index(drop=True)

    return resumen, detalle, sin_instalacion


# =========================
# Mensajes y exportación
# =========================
def mensaje_whatsapp_general(resumen: pd.DataFrame, fecha_consulta: date) -> str:
    total = int(resumen["Instalaciones"].sum()) if not resumen.empty else 0
    fecha_txt = fecha_consulta.strftime("%d/%m/%Y")

    lineas = [
        f"📌 INSTALACIONES PROGRAMADAS PARA HOY - {fecha_txt}",
        "",
        f"Total instalaciones: {total}",
        "",
    ]

    if resumen.empty:
        lineas.append("No se encontraron instalaciones para los EH de mis socios.")
    else:
        for _, r in resumen.iterrows():
            nombre_corto = str(r["Socio"]).split()[0] + " " + str(r["Socio"]).split()[1] if len(str(r["Socio"]).split()) >= 2 else str(r["Socio"])
            lineas.append(f"{r['EH']} - {nombre_corto}: {int(r['Instalaciones'])}")

    lineas += [
        "",
        "Por favor realizar seguimiento para asegurar la instalación del día.",
    ]
    return "\n".join(lineas)


def mensaje_whatsapp_socio(detalle_socio: pd.DataFrame, fecha_consulta: date) -> str:
    if detalle_socio.empty:
        return ""

    eh = detalle_socio.iloc[0]["EH"]
    socio = detalle_socio.iloc[0]["Socio"]
    fecha_txt = fecha_consulta.strftime("%d/%m/%Y")

    lineas = [
        f"📌 INSTALACIONES PROGRAMADAS - {fecha_txt}",
        f"EH: {eh}",
        f"Socio: {socio}",
        f"Total: {len(detalle_socio)}",
        "",
    ]

    for _, r in detalle_socio.iterrows():
        codigo = r.get("Código cliente", "")
        nodo = r.get("Nodo", "")
        tel = r.get("Teléfono", "")
        turno = r.get("Turno", "")
        lineas.append(f"• {codigo} | {nodo} | Turno: {turno} | Ref: {tel}")

    lineas += [
        "",
        "Por favor realizar seguimiento y confirmar avance.",
    ]
    return "\n".join(lineas)


def generar_excel(resumen: pd.DataFrame, detalle: pd.DataFrame, sin_instalacion: pd.DataFrame) -> BytesIO:
    salida = BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        resumen.to_excel(writer, index=False, sheet_name="Resumen")
        detalle.to_excel(writer, index=False, sheet_name="Detalle")
        sin_instalacion.to_excel(writer, index=False, sheet_name="Sin instalacion")

        for hoja in writer.book.worksheets:
            for col in hoja.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    value = "" if cell.value is None else str(cell.value)
                    max_len = max(max_len, len(value))
                hoja.column_dimensions[col_letter].width = min(max(max_len + 2, 10), 42)
            hoja.freeze_panes = "A2"

    salida.seek(0)
    return salida


def link_whatsapp(texto: str) -> str:
    return "https://wa.me/?text=" + quote(texto)


# =========================
# Interfaz Streamlit
# =========================
def mostrar_agenda_tecnica():
    import streamlit as st

    st.title("📅 Agenda Técnica / Instalaciones de Hoy")
    st.caption("Carga el archivo BO-CITA SERVICIO NACIONAL y filtra automáticamente las instalaciones del día para los EH de tus socios.")

    archivo = st.file_uploader(
        "Subir archivo de agenda técnica",
        type=["xlsx", "xls", "csv"],
        key="agenda_tecnica_uploader",
    )

    col_fecha, col_info = st.columns([1, 2])
    with col_fecha:
        fecha_consulta = st.date_input("Fecha a consultar", value=fecha_hoy_bolivia(), format="DD/MM/YYYY")
    with col_info:
        st.info("Criterio: tipo_trabajo_op = INSTALACION + inicio_agendado = fecha seleccionada + EH registrado en socios.")

    with st.expander("Ver EH configurados"):
        socios_df = pd.DataFrame({"EH": list(SOCIOS_EH.keys()), "Socio": list(SOCIOS_EH.values())})
        st.dataframe(socios_df, use_container_width=True, hide_index=True)

    if archivo is None:
        st.warning("Sube el archivo diario para generar el reporte.")
        return

    try:
        df = leer_archivo_agenda(archivo)
        resumen, detalle, sin_instalacion = procesar_agenda(df, fecha_consulta)
    except Exception as e:
        st.error(f"No se pudo procesar el archivo: {e}")
        return

    total = int(resumen["Instalaciones"].sum()) if not resumen.empty else 0
    socios_con_instalacion = resumen["EH"].nunique() if not resumen.empty else 0

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Instalaciones", total)
    kpi2.metric("Socios con agenda", socios_con_instalacion)
    kpi3.metric("Socios sin agenda", len(sin_instalacion))

    st.subheader("Resumen por socio")
    st.dataframe(resumen, use_container_width=True, hide_index=True)

    st.subheader("Detalle de instalaciones")
    st.dataframe(detalle, use_container_width=True, hide_index=True)

    st.subheader("Mensaje general para WhatsApp")
    texto_general = mensaje_whatsapp_general(resumen, fecha_consulta)
    st.text_area("Copiar mensaje", texto_general, height=250)
    st.markdown(f"[Enviar por WhatsApp]({link_whatsapp(texto_general)})")

    st.subheader("Mensaje por socio")
    if detalle.empty:
        st.info("No hay detalle por socio para la fecha seleccionada.")
    else:
        opciones = [f"{eh} - {SOCIOS_EH[eh]}" for eh in sorted(detalle["EH"].unique())]
        seleccion = st.selectbox("Selecciona socio", opciones)
        eh_sel = seleccion.split(" - ")[0]
        detalle_socio = detalle[detalle["EH"] == eh_sel]
        texto_socio = mensaje_whatsapp_socio(detalle_socio, fecha_consulta)
        st.text_area("Mensaje individual", texto_socio, height=220)
        st.markdown(f"[Enviar mensaje individual por WhatsApp]({link_whatsapp(texto_socio)})")

    with st.expander("Socios sin instalaciones para la fecha"):
        st.dataframe(sin_instalacion, use_container_width=True, hide_index=True)

    excel = generar_excel(resumen, detalle, sin_instalacion)
    nombre_excel = f"agenda_tecnica_{fecha_consulta.strftime('%Y%m%d')}.xlsx"
    st.download_button(
        "⬇️ Descargar Excel del reporte",
        data=excel,
        file_name=nombre_excel,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
