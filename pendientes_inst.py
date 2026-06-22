# pendientes_inst.py
# Módulo: Pendientes de Instalación con Pago
# Incluye filtro de casos antiguos (+3 días) y mensaje WhatsApp global.

from __future__ import annotations

import re
from datetime import date, datetime
from io import BytesIO
from urllib.parse import quote

import pandas as pd

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
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


def normalizar_columna(columna: object) -> str:
    texto = str(columna).strip().lower()
    reemplazos = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n",
        " ": "_", "-": "_", "/": "_", ".": "_", "(": "", ")": "",
    }
    for origen, destino in reemplazos.items():
        texto = texto.replace(origen, destino)
    texto = re.sub(r"_+", "_", texto)
    return texto.strip("_")


def normalizar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [normalizar_columna(c) for c in df.columns]
    return df


def buscar_columna(df: pd.DataFrame, opciones: list[str]) -> str | None:
    columnas = set(df.columns)
    for opcion in opciones:
        opcion_norm = normalizar_columna(opcion)
        if opcion_norm in columnas:
            return opcion_norm
    return None


def obtener_serie(df: pd.DataFrame, opciones: list[str]) -> pd.Series:
    columna = buscar_columna(df, opciones)
    if columna is None:
        return pd.Series([""] * len(df), index=df.index)
    return df[columna]


def limpiar_texto(valor: object) -> str:
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def limpiar_codigo(valor: object) -> str:
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return re.sub(r"[^0-9A-Za-z-]", "", texto)


def limpiar_eh(valor: object) -> str:
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return re.sub(r"\D", "", texto)


def parsear_fecha(serie: pd.Series) -> pd.Series:
    fecha = pd.to_datetime(serie, errors="coerce", dayfirst=True)
    return fecha.dt.date


def leer_archivo(archivo) -> pd.DataFrame:
    nombre = getattr(archivo, "name", "").lower()
    if nombre.endswith(".csv"):
        return pd.read_csv(archivo, sep=None, engine="python")
    return pd.read_excel(archivo, engine="openpyxl")


def construir_socios(texto_extra: str = "") -> dict[str, str]:
    socios = dict(SOCIOS_EH_DEFAULT)
    for linea in str(texto_extra).splitlines():
        linea = linea.strip()
        if not linea:
            continue
        match = re.match(r"^(\d{3,8})\s*[-|,;:]?\s*(.+)$", linea)
        if match:
            socios[match.group(1)] = match.group(2).strip()
    return socios


def preparar_pendientes(df_original: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str | None]]:
    df = normalizar_dataframe(df_original)

    col_codigo = buscar_columna(df, [
        "CLIENTE_NRO", "CODIGO_CLIENTE", "COD_CLIENTE", "CODIGO", "COD", "CLIENTE",
    ])
    col_nodo = buscar_columna(df, [
        "NODO_NOMBRE", "NODO", "NODO_ACTUAL", "NODO RED", "NODO_RED",
    ])
    col_fecha_ot = buscar_columna(df, [
        "FECHA_GENERACION_OT", "FECHA GENERACION OT", "FECHA_OT", "FECHA_VENTA", "FECHA_GENERACION",
    ])
    col_fecha_reporte = buscar_columna(df, [
        "FECHA_REPORTE", "FECHA REPORTE", "FECHA_CARGA", "FECHA",
    ])
    col_eh = buscar_columna(df, [
        "VENDEDOR_EH", "EH", "CODIGO_EH", "EHUMANO", "EH_PROMOTOR", "EJECUTIVO_EH",
    ])
    col_socio = buscar_columna(df, [
        "VENDEDOR_NOMBRE", "NOMBRE_VENDEDOR", "SOCIO", "VENDEDOR", "NOMBRE_SOCIO",
    ])
    col_tipo = buscar_columna(df, [
        "TIPO_VENTA", "TIPO", "TIPO_VTA", "TIPO_OPERACION",
    ])
    col_cliente = buscar_columna(df, [
        "CLIENTE_NOMBRE", "NOMBRE_CLIENTE", "CLIENTE", "NOMBRE",
    ])
    col_tel1 = buscar_columna(df, [
        "CLIENTE_TELEFONO1", "TELEFONO1", "TEL1", "TELEFONO", "CELULAR",
    ])
    col_tel2 = buscar_columna(df, [
        "CLIENTE_TELEFONO2", "TELEFONO2", "TEL2", "REFERENCIA", "REF",
    ])
    col_obs = buscar_columna(df, [
        "CRM_OBSERVACION", "OBSERVACION", "OBS", "COMENTARIO", "COMENTARIOS",
    ])

    columnas = {
        "codigo": col_codigo,
        "nodo": col_nodo,
        "fecha_generacion_ot": col_fecha_ot,
        "fecha_reporte": col_fecha_reporte,
        "eh": col_eh,
        "socio": col_socio,
        "tipo_venta": col_tipo,
        "cliente": col_cliente,
        "telefono1": col_tel1,
        "telefono2": col_tel2,
        "observacion": col_obs,
    }

    faltantes = [k for k in ["codigo", "nodo"] if columnas[k] is None]
    if faltantes:
        raise ValueError(
            "No se encontraron columnas obligatorias: "
            + ", ".join(faltantes)
            + ". Columnas encontradas: "
            + ", ".join(df.columns[:80])
        )

    df["_codigo"] = df[col_codigo].apply(limpiar_codigo) if col_codigo else ""
    df["_nodo"] = df[col_nodo].apply(limpiar_texto).str.upper() if col_nodo else ""
    df["_eh"] = df[col_eh].apply(limpiar_eh) if col_eh else ""
    df["_socio"] = df[col_socio].apply(limpiar_texto) if col_socio else ""
    df["_tipo_venta"] = df[col_tipo].apply(limpiar_texto).str.upper() if col_tipo else ""
    df["_cliente"] = df[col_cliente].apply(limpiar_texto) if col_cliente else ""
    df["_telefono1"] = df[col_tel1].apply(limpiar_texto) if col_tel1 else ""
    df["_telefono2"] = df[col_tel2].apply(limpiar_texto) if col_tel2 else ""
    df["_observacion"] = df[col_obs].apply(limpiar_texto) if col_obs else ""

    if col_fecha_ot:
        df["_fecha_base"] = parsear_fecha(df[col_fecha_ot])
        columnas["fecha_base_usada"] = col_fecha_ot
    elif col_fecha_reporte:
        df["_fecha_base"] = parsear_fecha(df[col_fecha_reporte])
        columnas["fecha_base_usada"] = col_fecha_reporte
    else:
        df["_fecha_base"] = pd.NaT
        columnas["fecha_base_usada"] = None

    return df, columnas


def calcular_antiguos(
    df_original: pd.DataFrame,
    dias_antiguedad: int,
    fecha_hoy: date,
    solo_eh_configurados: bool,
    socios: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    df, columnas = preparar_pendientes(df_original)

    fecha_corte = fecha_hoy - pd.Timedelta(days=int(dias_antiguedad))

    mask_codigo = df["_codigo"].ne("")
    mask_fecha = pd.Series([True] * len(df), index=df.index)
    if columnas.get("fecha_base_usada"):
        mask_fecha = df["_fecha_base"].notna() & (df["_fecha_base"] <= fecha_corte)

    mask_eh = pd.Series([True] * len(df), index=df.index)
    if solo_eh_configurados and "_eh" in df.columns:
        mask_eh = df["_eh"].isin(socios.keys())

    antiguos = df[mask_codigo & mask_fecha & mask_eh].copy()

    if antiguos.empty:
        detalle = pd.DataFrame(columns=[
            "Código cliente", "Nodo", "Fecha", "Días", "EH", "Socio", "Tipo venta",
            "Cliente", "Teléfono 1", "Teléfono 2", "Observación",
        ])
    else:
        fecha_base = pd.to_datetime(antiguos["_fecha_base"], errors="coerce")
        hoy_dt = pd.to_datetime(fecha_hoy)
        dias = (hoy_dt - fecha_base).dt.days

        detalle = pd.DataFrame({
            "Código cliente": antiguos["_codigo"],
            "Nodo": antiguos["_nodo"],
            "Fecha": antiguos["_fecha_base"],
            "Días": dias,
            "EH": antiguos["_eh"],
            "Socio": antiguos.apply(
                lambda r: r["_socio"] or socios.get(r["_eh"], "SIN NOMBRE"), axis=1
            ),
            "Tipo venta": antiguos["_tipo_venta"],
            "Cliente": antiguos["_cliente"],
            "Teléfono 1": antiguos["_telefono1"],
            "Teléfono 2": antiguos["_telefono2"],
            "Observación": antiguos["_observacion"],
        })
        detalle = detalle.sort_values(["Días", "Fecha", "Socio"], ascending=[False, True, True]).reset_index(drop=True)

    if detalle.empty:
        resumen = pd.DataFrame(columns=["EH", "Socio", "Pendientes antiguos"])
    else:
        resumen = (
            detalle.groupby(["EH", "Socio"], as_index=False)["Código cliente"]
            .count()
            .rename(columns={"Código cliente": "Pendientes antiguos"})
            .sort_values("Pendientes antiguos", ascending=False)
            .reset_index(drop=True)
        )

    diagnostico = {
        "columnas": columnas,
        "total_filas": len(df),
        "fecha_corte": fecha_corte,
        "fecha_hoy": fecha_hoy,
        "total_antiguos": len(detalle),
    }
    return resumen, detalle, diagnostico


def mensaje_whatsapp_antiguos(detalle: pd.DataFrame, dias_antiguedad: int, fecha_hoy: date) -> str:
    fecha_txt = fecha_hoy.strftime("%d/%m/%Y")
    total = len(detalle)
    lineas = [
        f"⏳ *PENDIENTES DE INSTALACIÓN +{dias_antiguedad} DÍAS*",
        f"📅 Fecha revisión: *{fecha_txt}*",
        f"🔢 Total casos: *{total}*",
        "",
    ]

    if detalle.empty:
        lineas.append("✅ No se encontraron pendientes antiguos con el filtro seleccionado.")
        return "\n".join(lineas)

    lineas.append("📋 *Código | Nodo | Fecha | Días*")
    for i, (_, r) in enumerate(detalle.iterrows(), start=1):
        codigo = r.get("Código cliente", "") or "S/D"
        nodo = r.get("Nodo", "") or "S/D"
        fecha = r.get("Fecha", "")
        if pd.notna(fecha) and fecha != "":
            fecha_txt_item = pd.to_datetime(fecha).strftime("%d/%m")
        else:
            fecha_txt_item = "S/F"
        dias = r.get("Días", "")
        try:
            dias_txt = str(int(dias))
        except Exception:
            dias_txt = "S/D"
        lineas.append(f"{i}. {codigo} | {nodo} | {fecha_txt_item} | {dias_txt} días")

    lineas += [
        "",
        "✅ Favor priorizar estos códigos por antigüedad y reportar avance.",
    ]
    return "\n".join(lineas)


def mensaje_whatsapp_por_socio(detalle: pd.DataFrame, dias_antiguedad: int, fecha_hoy: date) -> str:
    fecha_txt = fecha_hoy.strftime("%d/%m/%Y")
    total = len(detalle)
    lineas = [
        f"⏳ *PENDIENTES DE INSTALACIÓN +{dias_antiguedad} DÍAS*",
        f"📅 Fecha revisión: *{fecha_txt}*",
        f"🔢 Total casos: *{total}*",
        "",
    ]

    if detalle.empty:
        lineas.append("✅ No se encontraron pendientes antiguos con el filtro seleccionado.")
        return "\n".join(lineas)

    for (eh, socio), grupo in detalle.groupby(["EH", "Socio"], dropna=False):
        lineas.append(f"👤 *{socio}* | EH: *{eh or 'S/D'}* | *{len(grupo)}* casos")
        for i, (_, r) in enumerate(grupo.iterrows(), start=1):
            codigo = r.get("Código cliente", "") or "S/D"
            nodo = r.get("Nodo", "") or "S/D"
            dias = r.get("Días", "")
            try:
                dias_txt = str(int(dias))
            except Exception:
                dias_txt = "S/D"
            lineas.append(f"{i}. {codigo} | {nodo} | {dias_txt} días")
        lineas.append("")

    lineas.append("✅ Favor priorizar por antigüedad y reportar avance.")
    return "\n".join(lineas).strip()


def generar_excel(resumen: pd.DataFrame, detalle: pd.DataFrame, diagnostico: dict) -> BytesIO:
    salida = BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        resumen.to_excel(writer, index=False, sheet_name="Resumen")
        detalle.to_excel(writer, index=False, sheet_name="Antiguos +3 dias")
        pd.DataFrame({
            "Métrica": ["Total filas", "Total antiguos", "Fecha hoy", "Fecha corte", "Fecha base usada"],
            "Valor": [
                diagnostico.get("total_filas"),
                diagnostico.get("total_antiguos"),
                diagnostico.get("fecha_hoy"),
                diagnostico.get("fecha_corte"),
                diagnostico.get("columnas", {}).get("fecha_base_usada"),
            ],
        }).to_excel(writer, index=False, sheet_name="Diagnostico")
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


def mostrar_pendientes_inst(configurar_pagina: bool = False) -> None:
    import streamlit as st

    if configurar_pagina:
        try:
            st.set_page_config(page_title="Pendientes de Instalación", page_icon="📋", layout="wide")
        except Exception:
            pass

    st.title("📋 Pendientes de Instalación con Pago")
    st.caption("Filtra casos antiguos de 3 días hacia atrás y genera mensaje para WhatsApp.")

    with st.sidebar:
        st.subheader("Configuración")
        dias_antiguedad = st.number_input("Antigüedad mínima en días", min_value=1, max_value=30, value=3, step=1)
        solo_eh_configurados = st.checkbox("Solo mis socios EH", value=False)
        with st.expander("Agregar/corregir EH", expanded=False):
            st.caption("Formato por línea: 59509 Nombre del socio")
            texto_eh_extra = st.text_area("EH adicionales", height=120)
        socios = construir_socios(texto_eh_extra)

    archivo = st.file_uploader(
        "📤 Sube archivo Pendientes de Instalación con Pago",
        type=["csv", "xlsx", "xls"],
        key="uploader_pendientes_inst",
    )

    if archivo is None:
        st.info("Sube el archivo PENDIENTE_INST_CON_PAGO para generar el reporte.")
        return

    try:
        df_original = leer_archivo(archivo)
    except Exception as e:
        st.error(f"No se pudo leer el archivo: {e}")
        return

    st.success(f"Archivo leído correctamente: {len(df_original)} filas y {len(df_original.columns)} columnas.")

    try:
        fecha_hoy = hoy_bolivia()
        resumen, detalle, diagnostico = calcular_antiguos(
            df_original=df_original,
            dias_antiguedad=int(dias_antiguedad),
            fecha_hoy=fecha_hoy,
            solo_eh_configurados=solo_eh_configurados,
            socios=socios,
        )
    except Exception as e:
        st.error(str(e))
        with st.expander("Ver primeras filas y columnas", expanded=True):
            st.write(list(normalizar_dataframe(df_original).columns))
            st.dataframe(df_original.head(10), use_container_width=True)
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Pendientes antiguos", len(detalle))
    c2.metric("Socios/EH", resumen["EH"].nunique() if not resumen.empty else 0)
    c3.metric("Fecha corte", pd.to_datetime(diagnostico["fecha_corte"]).strftime("%d/%m/%Y"))

    with st.expander("Diagnóstico", expanded=False):
        st.write("Columnas detectadas:")
        st.json(diagnostico["columnas"])

    st.subheader(f"⏳ Casos antiguos +{int(dias_antiguedad)} días")

    if detalle.empty:
        st.warning("No se encontraron casos antiguos con el filtro actual.")
    else:
        col_socio, col_nodo = st.columns(2)
        socios_opciones = ["Todos"] + sorted([s for s in detalle["Socio"].dropna().unique() if str(s).strip()])
        nodos_opciones = ["Todos"] + sorted([n for n in detalle["Nodo"].dropna().unique() if str(n).strip()])
        socio_sel = col_socio.selectbox("Filtrar por socio", socios_opciones)
        nodo_sel = col_nodo.selectbox("Filtrar por nodo", nodos_opciones)

        detalle_filtrado = detalle.copy()
        if socio_sel != "Todos":
            detalle_filtrado = detalle_filtrado[detalle_filtrado["Socio"] == socio_sel]
        if nodo_sel != "Todos":
            detalle_filtrado = detalle_filtrado[detalle_filtrado["Nodo"] == nodo_sel]

        st.dataframe(
            detalle_filtrado[["Código cliente", "Nodo", "Fecha", "Días", "EH", "Socio", "Tipo venta"]],
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("📊 Resumen por socio")
        st.dataframe(resumen, use_container_width=True, hide_index=True)

        st.subheader("📲 Mensaje WhatsApp global")
        formato = st.radio("Formato", ["Código + nodo", "Agrupado por socio"], horizontal=True)
        texto = (
            mensaje_whatsapp_antiguos(detalle_filtrado, int(dias_antiguedad), fecha_hoy)
            if formato == "Código + nodo"
            else mensaje_whatsapp_por_socio(detalle_filtrado, int(dias_antiguedad), fecha_hoy)
        )
        st.text_area("Copiar mensaje", texto, height=320)
        st.markdown(f"[Enviar por WhatsApp]({whatsapp_link(texto)})")

        excel = generar_excel(resumen, detalle_filtrado, diagnostico)
        st.download_button(
            "⬇️ Descargar Excel",
            data=excel,
            file_name=f"pendientes_inst_antiguos_{fecha_hoy.strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


# Alias por si tu app anterior importaba con otro nombre.
def app() -> None:
    mostrar_pendientes_inst(configurar_pagina=False)


def main() -> None:
    mostrar_pendientes_inst(configurar_pagina=True)


if __name__ == "__main__":
    main()
