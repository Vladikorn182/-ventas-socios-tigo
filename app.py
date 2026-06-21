# app.py
# Agenda Técnica / Instalaciones de Hoy - App independiente V3
# Archivo único para evitar errores de importación al subir a Render/GitHub.

from __future__ import annotations

import re
import warnings
from datetime import datetime, date
from io import BytesIO
from urllib.parse import quote

import pandas as pd

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

SOCIOS_EH_DEFAULT = {
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


def hoy_bolivia() -> date:
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
    txt = str(valor).strip()
    if txt.endswith(".0"):
        txt = txt[:-2]
    return re.sub(r"[^0-9A-Za-z-]", "", txt)


def limpiar_eh(valor) -> str:
    if pd.isna(valor):
        return ""
    txt = str(valor).strip()
    if txt.endswith(".0"):
        txt = txt[:-2]
    return re.sub(r"\D", "", txt)


def norm_col(col) -> str:
    txt = str(col).strip().lower()
    reemplazos = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n",
        "/": "_", "-": "_", ".": "_", " ": "_", "(": "", ")": "",
    }
    for a, b in reemplazos.items():
        txt = txt.replace(a, b)
    txt = re.sub(r"_+", "_", txt)
    return txt.strip("_")


def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [norm_col(c) for c in df.columns]
    return df


def buscar_columna(df: pd.DataFrame, opciones: list[str]) -> str | None:
    cols = set(df.columns)
    for op in opciones:
        opn = norm_col(op)
        if opn in cols:
            return opn
    return None


def serie(df: pd.DataFrame, opciones: list[str]) -> pd.Series:
    col = buscar_columna(df, opciones)
    if col is None:
        return pd.Series([""] * len(df), index=df.index)
    return df[col]


def extraer_nodo_texto(*valores) -> str:
    texto = " ".join(limpiar_texto(v).upper() for v in valores if limpiar_texto(v))
    if not texto:
        return ""
    texto = texto.replace("-", " ").replace("_", " ")
    texto = re.sub(r"\s+", " ", texto)
    patron = r"\b(EAL\s*\d{3,4}|LPZ\s*\d{3,4}|EAF\s*\d{3,4}|SCZ\s*\d{3,4}|PTS\s*\d{3,4}|[A-Z]{3}\s*\d{3,4})\b"
    m = re.search(patron, texto)
    return m.group(1).replace(" ", "") if m else ""


def parsear_fechas(s: pd.Series) -> pd.Series:
    # Primer intento: fechas normales/Excel.
    f1 = pd.to_datetime(s, errors="coerce")
    # Segundo intento: solo para valores no detectados, con formato día/mes/año.
    pendientes = f1.isna()
    if pendientes.any():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            f2 = pd.to_datetime(s[pendientes], errors="coerce", dayfirst=True)
        f1.loc[pendientes] = f2
    return f1.dt.date


def leer_archivo(archivo, hoja: str | None = None) -> pd.DataFrame:
    nombre = getattr(archivo, "name", "").lower()
    if nombre.endswith(".csv"):
        # Soporta CSV separado por coma o punto y coma.
        return pd.read_csv(archivo, sep=None, engine="python")
    if hoja:
        return pd.read_excel(archivo, sheet_name=hoja, engine="openpyxl")
    return pd.read_excel(archivo, engine="openpyxl")


def obtener_hojas(archivo) -> list[str]:
    nombre = getattr(archivo, "name", "").lower()
    if nombre.endswith(".csv"):
        return []
    pos = archivo.tell()
    try:
        archivo.seek(0)
        xls = pd.ExcelFile(archivo, engine="openpyxl")
        return xls.sheet_names
    finally:
        archivo.seek(pos)


def construir_socios(texto: str) -> dict[str, str]:
    socios = dict(SOCIOS_EH_DEFAULT)
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        # Formato aceptado: 59509 Nombre Apellido o 59509 - Nombre Apellido
        m = re.match(r"^(\d{3,8})\s*[-|,;:]?\s*(.+)$", linea)
        if m:
            socios[m.group(1)] = m.group(2).strip() or m.group(1)
    return socios


def preparar(df_original: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = normalizar_columnas(df_original)

    col_fecha = buscar_columna(df, [
        "inicio_agendado", "inicio cita", "inicio_cita", "fecha_agendada", "data_agendamiento", "fecha agenda",
    ])
    col_tipo = buscar_columna(df, [
        "tipo_trabajo_op", "tipo_trabajo", "tipo trabajo op", "tipo trabajo", "descripcion_trabajo",
    ])
    col_eh = buscar_columna(df, [
        "ehumano_promotor", "eh_promotor", "eh", "vendedor_eh", "codigo_eh", "promotor", "ehumano",
    ])

    columnas_detectadas = {
        "fecha": col_fecha,
        "tipo_trabajo": col_tipo,
        "eh": col_eh,
    }

    faltantes = [k for k, v in columnas_detectadas.items() if v is None]
    if faltantes:
        raise ValueError(
            "No se encontraron columnas requeridas: " + ", ".join(faltantes) +
            ". Columnas del archivo: " + ", ".join(df.columns[:80])
        )

    df["_fecha_agendada"] = parsear_fechas(df[col_fecha])
    df["_tipo_op"] = df[col_tipo].fillna("").astype(str).str.upper().str.strip()
    df["_eh"] = df[col_eh].apply(limpiar_eh)
    return df, columnas_detectadas


def procesar(df_original: pd.DataFrame, fecha_consulta: date, socios: dict[str, str], solo_mis_socios: bool = True):
    df, columnas_detectadas = preparar(df_original)

    mask_fecha = df["_fecha_agendada"] == fecha_consulta
    mask_inst = df["_tipo_op"].str.contains("INSTALACION", na=False)
    if solo_mis_socios:
        mask_eh = df["_eh"].isin(socios.keys())
    else:
        mask_eh = df["_eh"].ne("")

    filtrado = df[mask_fecha & mask_inst & mask_eh].copy()

    diagnostico = {
        "total_filas": int(len(df)),
        "filas_fecha": int(mask_fecha.sum()),
        "filas_instalacion_fecha": int((mask_fecha & mask_inst).sum()),
        "filas_eh_fecha_instalacion": int((mask_fecha & mask_inst & mask_eh).sum()),
        "fechas": sorted([f for f in df["_fecha_agendada"].dropna().unique()]),
        "columnas_detectadas": columnas_detectadas,
        "tipos_en_fecha": df.loc[mask_fecha, "_tipo_op"].value_counts().head(20).reset_index(),
        "eh_en_fecha_instalacion": df.loc[mask_fecha & mask_inst, "_eh"].value_counts().head(50).reset_index(),
    }

    cols = [
        "EH", "Socio", "Código cliente", "Nodo", "Cliente", "Teléfono", "Ciudad", "Turno", "Hora inicio",
        "Contratista", "Técnico", "Estado", "Confirmación", "Dirección/Dato conexión",
    ]

    if filtrado.empty:
        detalle = pd.DataFrame(columns=cols)
    else:
        detalle = pd.DataFrame({
            "EH": filtrado["_eh"],
            "Socio": filtrado["_eh"].map(socios).fillna("SIN NOMBRE CONFIGURADO"),
            "Código cliente": serie(filtrado, ["cliente_nro", "codigo_cliente", "cod_cliente", "cliente"]).apply(limpiar_codigo),
            "Nodo": filtrado.apply(lambda r: extraer_nodo_texto(
                r.get("dato_onexion", ""), r.get("dato_conexion", ""), r.get("zona_ramal", ""),
                r.get("tap_nap", ""), r.get("descripcion", ""), r.get("comentario", ""), r.get("territorio_servicio", ""),
            ), axis=1),
            "Cliente": serie(filtrado, ["nombre_contacto", "cliente_nombre", "nombre_cliente"]).apply(limpiar_texto),
            "Teléfono": serie(filtrado, ["numero_telefono_cliente", "cliente_telefono1", "cliente_telefono2", "telefono"]).apply(limpiar_texto),
            "Ciudad": serie(filtrado, ["ciudad"]).apply(limpiar_texto),
            "Turno": serie(filtrado, ["turno_agendamiento", "rango_cita_acordada_con_cliente", "turno"]).apply(limpiar_texto),
            "Hora inicio": serie(filtrado, ["hora_inicio", "inicio_cita"]).apply(limpiar_texto),
            "Contratista": serie(filtrado, ["contratista"]).apply(limpiar_texto),
            "Técnico": serie(filtrado, ["tecnico_nombre", "tecnico"]).apply(limpiar_texto),
            "Estado": serie(filtrado, ["estado"]).apply(limpiar_texto),
            "Confirmación": serie(filtrado, ["estado_confirmacion", "confirmacion"]).apply(limpiar_texto),
            "Dirección/Dato conexión": serie(filtrado, ["dato_onexion", "dato_conexion", "descripcion", "comentario"]).apply(limpiar_texto),
        })
        detalle = detalle.sort_values(["Socio", "Código cliente"], ascending=[True, True]).reset_index(drop=True)

    if detalle.empty:
        resumen = pd.DataFrame(columns=["EH", "Socio", "Instalaciones"])
    else:
        resumen = (
            detalle.groupby(["EH", "Socio"], as_index=False)["Código cliente"]
            .count()
            .rename(columns={"Código cliente": "Instalaciones"})
            .sort_values("Instalaciones", ascending=False)
            .reset_index(drop=True)
        )

    socios_df = pd.DataFrame({"EH": list(socios.keys()), "Socio": list(socios.values())})
    sin_instalacion = socios_df[~socios_df["EH"].isin(resumen["EH"] if not resumen.empty else [])].copy()
    sin_instalacion = sin_instalacion.sort_values("Socio").reset_index(drop=True)
    return resumen, detalle, sin_instalacion, diagnostico


def nombre_corto(nombre: str) -> str:
    p = str(nombre).split()
    return " ".join(p[:2]) if len(p) >= 2 else str(nombre)


def mensaje_general(resumen: pd.DataFrame, fecha_consulta: date) -> str:
    total = int(resumen["Instalaciones"].sum()) if not resumen.empty else 0
    lineas = [
        f"📌 INSTALACIONES PROGRAMADAS - {fecha_consulta.strftime('%d/%m/%Y')}",
        "",
        f"Total instalaciones: {total}",
        "",
    ]
    if resumen.empty:
        lineas.append("No se encontraron instalaciones para los EH configurados.")
    else:
        for _, r in resumen.iterrows():
            lineas.append(f"{r['EH']} - {nombre_corto(r['Socio'])}: {int(r['Instalaciones'])}")
    lineas += ["", "Por favor realizar seguimiento para asegurar la instalación del día."]
    return "\n".join(lineas)


def mensaje_socio(detalle_socio: pd.DataFrame, fecha_consulta: date) -> str:
    if detalle_socio.empty:
        return ""
    eh = detalle_socio.iloc[0]["EH"]
    socio = detalle_socio.iloc[0]["Socio"]
    lineas = [
        f"📌 INSTALACIONES PROGRAMADAS - {fecha_consulta.strftime('%d/%m/%Y')}",
        f"EH: {eh}",
        f"Socio: {socio}",
        f"Total: {len(detalle_socio)}",
        "",
    ]
    for _, r in detalle_socio.iterrows():
        lineas.append(f"• {r.get('Código cliente','')} | {r.get('Nodo','')} | Turno: {r.get('Turno','')} | Ref: {r.get('Teléfono','')}")
    lineas += ["", "Por favor realizar seguimiento y confirmar avance."]
    return "\n".join(lineas)


def generar_excel(resumen, detalle, sin_instalacion, diagnostico) -> BytesIO:
    salida = BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        resumen.to_excel(writer, index=False, sheet_name="Resumen")
        detalle.to_excel(writer, index=False, sheet_name="Detalle")
        sin_instalacion.to_excel(writer, index=False, sheet_name="Sin instalacion")
        diag = pd.DataFrame({
            "Métrica": ["Total filas", "Filas fecha", "Instalaciones fecha", "Instalaciones EH"],
            "Valor": [
                diagnostico["total_filas"], diagnostico["filas_fecha"],
                diagnostico["filas_instalacion_fecha"], diagnostico["filas_eh_fecha_instalacion"],
            ],
        })
        diag.to_excel(writer, index=False, sheet_name="Diagnostico")
        diagnostico["tipos_en_fecha"].to_excel(writer, index=False, sheet_name="Tipos fecha")
        diagnostico["eh_en_fecha_instalacion"].to_excel(writer, index=False, sheet_name="EH fecha")
        for hoja in writer.book.worksheets:
            hoja.freeze_panes = "A2"
            for col in hoja.columns:
                letra = col[0].column_letter
                ancho = max(len(str(c.value)) if c.value is not None else 0 for c in col)
                hoja.column_dimensions[letra].width = min(max(ancho + 2, 10), 45)
    salida.seek(0)
    return salida


def whatsapp_link(texto: str) -> str:
    return "https://wa.me/?text=" + quote(texto)


def app():
    import streamlit as st
    st.set_page_config(page_title="Agenda Técnica", page_icon="📅", layout="wide")
    st.title("📅 Agenda Técnica / Instalaciones de Hoy")
    st.caption("App independiente V3. Sube el Excel diario de agenda técnica, no el ZIP.")

    with st.sidebar:
        st.subheader("Configuración")
        solo_mis_socios = st.checkbox("Filtrar solo mis socios EH", value=True)
        with st.expander("Agregar o corregir EH", expanded=False):
            st.caption("Opcional. Formato por línea: 59509 Nombre del socio")
            extra_eh = st.text_area("EH adicionales", height=130, placeholder="91207 Nombre Socio\n91208 Otro Socio")
        socios = construir_socios(extra_eh)
        st.write(f"EH configurados: **{len(socios)}**")

    archivo = st.file_uploader("Subir archivo BO-CITA SERVICIO NACIONAL", type=["xlsx", "xls", "csv"])
    if archivo is None:
        st.warning("Sube el archivo Excel diario para generar el reporte.")
        st.info("Importante: aquí se sube el Excel de agenda, no el ZIP de la aplicación.")
        return

    hoja = None
    try:
        hojas = obtener_hojas(archivo)
        if hojas and len(hojas) > 1:
            hoja = st.selectbox("Seleccionar hoja", hojas)
        elif hojas:
            hoja = hojas[0]
        archivo.seek(0)
        df_original = leer_archivo(archivo, hoja)
    except Exception as e:
        st.error(f"No se pudo leer el archivo: {e}")
        return

    st.success(f"Archivo leído correctamente: {len(df_original)} filas y {len(df_original.columns)} columnas.")

    try:
        df_preparado, cols_detectadas = preparar(df_original)
        fechas = sorted([f for f in df_preparado["_fecha_agendada"].dropna().unique()])
    except Exception as e:
        st.error(str(e))
        with st.expander("Ver columnas detectadas del archivo", expanded=True):
            st.write(list(normalizar_columnas(df_original).columns))
            st.dataframe(df_original.head(10), use_container_width=True)
        return

    if not fechas:
        st.error("No se encontraron fechas válidas en el archivo.")
        st.dataframe(df_original.head(10), use_container_width=True)
        return

    hoy = hoy_bolivia()
    fecha_default = hoy if hoy in fechas else max(fechas)
    if hoy not in fechas:
        st.warning(f"La fecha de hoy ({hoy.strftime('%d/%m/%Y')}) no aparece en el archivo. Seleccioné la última fecha disponible: {fecha_default.strftime('%d/%m/%Y')}.")

    opciones = [f.strftime("%d/%m/%Y") for f in fechas]
    fecha_txt = st.selectbox("Fecha a consultar", opciones, index=fechas.index(fecha_default))
    fecha_consulta = fechas[opciones.index(fecha_txt)]

    resumen, detalle, sin_instalacion, diagnostico = procesar(df_original, fecha_consulta, socios, solo_mis_socios)

    total = int(resumen["Instalaciones"].sum()) if not resumen.empty else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Instalaciones", total)
    c2.metric("Socios con agenda", resumen["EH"].nunique() if not resumen.empty else 0)
    c3.metric("Socios sin agenda", len(sin_instalacion) if solo_mis_socios else 0)

    if total == 0:
        st.error("El filtro quedó en 0. Abajo se muestra el diagnóstico para identificar la causa.")

    with st.expander("Diagnóstico del archivo", expanded=(total == 0)):
        st.write("Columnas detectadas:", diagnostico["columnas_detectadas"])
        st.write(f"Total filas: **{diagnostico['total_filas']}**")
        st.write(f"Filas de la fecha seleccionada: **{diagnostico['filas_fecha']}**")
        st.write(f"Filas INSTALACION en esa fecha: **{diagnostico['filas_instalacion_fecha']}**")
        st.write(f"Filas de EH configurados en esa fecha: **{diagnostico['filas_eh_fecha_instalacion']}**")
        st.write("Fechas encontradas:", ", ".join(f.strftime("%d/%m/%Y") for f in diagnostico["fechas"]))
        st.write("Tipos de trabajo en la fecha:")
        st.dataframe(diagnostico["tipos_en_fecha"], use_container_width=True, hide_index=True)
        st.write("EH encontrados en instalaciones de la fecha:")
        st.dataframe(diagnostico["eh_en_fecha_instalacion"], use_container_width=True, hide_index=True)

    st.subheader("Resumen por socio")
    st.dataframe(resumen, use_container_width=True, hide_index=True)

    st.subheader("Detalle de instalaciones")
    st.dataframe(detalle, use_container_width=True, hide_index=True)

    st.subheader("Mensaje general WhatsApp")
    texto = mensaje_general(resumen, fecha_consulta)
    st.text_area("Copiar mensaje", texto, height=220)
    st.markdown(f"[Enviar por WhatsApp]({whatsapp_link(texto)})")

    st.subheader("Mensaje por socio")
    if detalle.empty:
        st.info("No hay instalaciones por socio para la fecha seleccionada.")
    else:
        opciones_socios = [f"{eh} - {socios.get(eh, 'SIN NOMBRE')}" for eh in sorted(detalle["EH"].unique())]
        sel = st.selectbox("Seleccionar socio", opciones_socios)
        eh_sel = sel.split(" - ")[0]
        det_socio = detalle[detalle["EH"] == eh_sel]
        texto_socio = mensaje_socio(det_socio, fecha_consulta)
        st.text_area("Mensaje individual", texto_socio, height=220)
        st.markdown(f"[Enviar mensaje individual]({whatsapp_link(texto_socio)})")

    if solo_mis_socios:
        with st.expander("Socios sin instalaciones"):
            st.dataframe(sin_instalacion, use_container_width=True, hide_index=True)

    excel = generar_excel(resumen, detalle, sin_instalacion, diagnostico)
    st.download_button(
        "⬇️ Descargar Excel",
        data=excel,
        file_name=f"agenda_tecnica_{fecha_consulta.strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    app()
