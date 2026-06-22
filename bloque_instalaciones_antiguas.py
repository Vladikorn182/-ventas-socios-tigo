# -*- coding: utf-8 -*-
"""
Bloque para agregar al modulo Pendientes de Instalacion con Pago.
Filtra casos antiguos de 3 dias hacia atras y genera mensaje WhatsApp con codigo y nodo.
"""

from __future__ import annotations

import io
import unicodedata
from urllib.parse import quote

import pandas as pd
import streamlit as st


def _normalizar_texto(valor: object) -> str:
    texto = str(valor).strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.replace(" ", "_").replace("-", "_")
    while "__" in texto:
        texto = texto.replace("__", "_")
    return texto


def _buscar_columna(df: pd.DataFrame, candidatos: list[str]) -> str | None:
    mapa = {_normalizar_texto(col): col for col in df.columns}
    for candidato in candidatos:
        clave = _normalizar_texto(candidato)
        if clave in mapa:
            return mapa[clave]
    return None


def _limpiar_codigo(valor: object) -> str:
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return texto


def _crear_excel(df_resultado: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_resultado.to_excel(writer, index=False, sheet_name="Antiguos +3 dias")
    return output.getvalue()


def mostrar_instalaciones_antiguas(df: pd.DataFrame, dias_antiguedad: int = 3) -> None:
    """
    Muestra en Streamlit una seccion para casos antiguos.

    Uso dentro de pendientes_inst.py, despues de cargar el DataFrame principal:

        from bloque_instalaciones_antiguas import mostrar_instalaciones_antiguas
        mostrar_instalaciones_antiguas(df)
    """

    st.markdown("---")
    st.subheader("⏳ Instalaciones antiguas +3 días")
    st.caption("Filtra casos con fecha de generación igual o anterior a hoy menos 3 días.")

    if df is None or df.empty:
        st.info("Primero sube el archivo de Pendientes de Instalación con Pago.")
        return

    col_codigo = _buscar_columna(df, ["CLIENTE_NRO", "CODIGO", "CODIGO_CLIENTE", "CLIENTE", "CÓDIGO"])
    col_nodo = _buscar_columna(df, ["NODO_NOMBRE", "NODO", "NODO_RED", "NODO NOMBRE"])
    col_fecha = _buscar_columna(df, ["FECHA_GENERACION_OT", "FECHA_GENERACION", "FECHA_REPORTE", "FECHA", "FECHA_INGRESO"])

    faltantes = []
    if not col_codigo:
        faltantes.append("CLIENTE_NRO / Código")
    if not col_nodo:
        faltantes.append("NODO_NOMBRE / Nodo")
    if not col_fecha:
        faltantes.append("FECHA_GENERACION_OT / Fecha")

    if faltantes:
        st.error("No se encontraron estas columnas necesarias: " + ", ".join(faltantes))
        st.write("Columnas detectadas en el archivo:")
        st.code("\n".join([str(c) for c in df.columns]))
        return

    df_trabajo = df.copy()
    df_trabajo[col_fecha] = pd.to_datetime(df_trabajo[col_fecha], errors="coerce", dayfirst=True)

    fecha_hoy = pd.Timestamp.today().normalize()
    fecha_corte = fecha_hoy - pd.Timedelta(days=int(dias_antiguedad))

    df_antiguos = df_trabajo[df_trabajo[col_fecha] <= fecha_corte].copy()

    columnas_salida = [col_codigo, col_nodo, col_fecha]
    col_socio = _buscar_columna(df_antiguos, ["VENDEDOR_NOMBRE", "VENDEDOR", "SOCIO", "NOMBRE_SOCIO"])
    col_eh = _buscar_columna(df_antiguos, ["VENDEDOR_EH", "EH", "COD_EH"])
    if col_eh:
        columnas_salida.append(col_eh)
    if col_socio:
        columnas_salida.append(col_socio)

    df_salida = df_antiguos[columnas_salida].copy()
    df_salida[col_codigo] = df_salida[col_codigo].apply(_limpiar_codigo)
    df_salida[col_nodo] = df_salida[col_nodo].astype(str).str.strip()
    df_salida = df_salida[df_salida[col_codigo] != ""]
    df_salida = df_salida.sort_values(by=col_fecha, ascending=True)

    # Renombrar columnas para que se vea claro en pantalla y Excel.
    renombrar = {
        col_codigo: "Código cliente",
        col_nodo: "Nodo",
        col_fecha: "Fecha generación",
    }
    if col_eh:
        renombrar[col_eh] = "EH"
    if col_socio:
        renombrar[col_socio] = "Socio"
    df_salida = df_salida.rename(columns=renombrar)

    total = len(df_salida)
    st.metric("Casos antiguos encontrados", total)
    st.caption(f"Corte aplicado: casos con fecha igual o anterior a {fecha_corte.strftime('%d/%m/%Y')}")

    if total == 0:
        st.success("No hay instalaciones antiguas con el corte seleccionado.")
        return

    st.dataframe(df_salida, use_container_width=True, hide_index=True)

    lineas = [
        "⏳ *PENDIENTES DE INSTALACIÓN ANTIGUOS +3 DÍAS*",
        "",
        f"📅 *Corte:* hasta {fecha_corte.strftime('%d/%m/%Y')}",
        f"🔢 *Total casos:* {total}",
        "",
        "📋 *Código | Nodo | Fecha*",
    ]

    for _, row in df_salida.iterrows():
        codigo = str(row.get("Código cliente", "")).strip()
        nodo = str(row.get("Nodo", "")).strip()
        fecha = row.get("Fecha generación", "")
        fecha_txt = fecha.strftime("%d/%m/%Y") if pd.notna(fecha) else ""
        lineas.append(f"• {codigo} | {nodo} | {fecha_txt}")

    lineas.extend([
        "",
        "✅ Favor priorizar estos códigos por antigüedad y confirmar avance durante el día.",
    ])
    mensaje = "\n".join(lineas)

    st.text_area("Mensaje WhatsApp global", mensaje, height=320)

    url = "https://wa.me/?text=" + quote(mensaje)
    st.markdown(f"[📲 Enviar mensaje global por WhatsApp]({url})")

    st.download_button(
        "⬇️ Descargar Excel de casos antiguos",
        data=_crear_excel(df_salida),
        file_name="pendientes_instalacion_antiguos_mas_3_dias.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
