import streamlit as st
import urllib.parse
import pandas as pd
from .comun import leer_archivo, normalizar_columnas, SOCIOS_DICT, analizar_crm, separar_telefonos, excel_download

def pendientes_instalacion():
    st.subheader("📋 Pendientes de Instalación")
    st.write("Sube el archivo PENDIENTE_INST_CON_PAGO, selecciona un socio y envía sus códigos por WhatsApp.")
    archivo = st.file_uploader("📤 Sube archivo Pendientes de Instalación", type=["csv","xlsx"], key="pendientes_instalacion")
    if not archivo: return
    try:
        data = leer_archivo(archivo)
        if data is None: return
        data = normalizar_columnas(data)
        st.success(f"Archivo cargado: {len(data)} registros")
        if len(data) == 0:
            st.warning("El archivo no tiene registros pendientes. Solo tiene encabezados."); return
        for col in ["VENDEDOR_NOMBRE", "CRM_MOTIVO", "NODO_NOMBRE", "CLIENTE_TELEFONO1", "CLIENTE_TELEFONO2"]:
            if col not in data.columns: data[col] = ""
        req = ["CLIENTE_NRO","FECHA_REPORTE","VENDEDOR_EH"]
        faltantes = [c for c in req if c not in data.columns]
        if faltantes:
            st.error(f"Faltan columnas: {faltantes}"); st.write("Columnas detectadas:"); st.write(list(data.columns)); return
        data["VENDEDOR_EH"] = data["VENDEDOR_EH"].astype(str)
        data["SOCIO"] = data.apply(lambda x: str(x["VENDEDOR_NOMBRE"]).strip() if str(x["VENDEDOR_NOMBRE"]).strip() not in ["", "nan", "None"] else SOCIOS_DICT.get(str(x["VENDEDOR_EH"]), "SIN NOMBRE"), axis=1)
        data["SOCIO_DISPLAY"] = data["VENDEDOR_EH"] + " - " + data["SOCIO"]
        data["ANALISIS_CRM"] = data["CRM_MOTIVO"].apply(analizar_crm)
        telefonos = data["CLIENTE_TELEFONO1"].astype(str) + "," + data["CLIENTE_TELEFONO2"].astype(str)
        tels = telefonos.apply(lambda x: pd.Series(separar_telefonos(x)))
        data["TEL_TITULAR"] = tels[0]; data["TEL_REF1"] = tels[1]; data["TEL_REF2"] = tels[2]
        resumen = data.groupby(["VENDEDOR_EH","SOCIO","SOCIO_DISPLAY"]).agg(Pendientes=("CLIENTE_NRO","count")).reset_index().sort_values("SOCIO")
        resumen["MOSTRAR"] = resumen["SOCIO_DISPLAY"] + " (" + resumen["Pendientes"].astype(str) + " pendientes)"
        socio_sel = st.selectbox("Selecciona socio", resumen["MOSTRAR"].tolist(), key="sel_pend_inst")
        socio_display = resumen[resumen["MOSTRAR"] == socio_sel]["SOCIO_DISPLAY"].iloc[0]
        detalle = data[data["SOCIO_DISPLAY"] == socio_display].copy().reset_index(drop=True)
        eh = str(detalle["VENDEDOR_EH"].iloc[0]); nombre = str(detalle["SOCIO"].iloc[0])
        st.metric("📌 Pendientes de instalación", len(detalle))
        vista_cols = [c for c in ["CLIENTE_NRO","FECHA_REPORTE","VENDEDOR_EH","SOCIO","NODO_NOMBRE","CRM_MOTIVO","ANALISIS_CRM","TEL_TITULAR","TEL_REF1","TEL_REF2"] if c in detalle.columns]
        st.dataframe(detalle[vista_cols], use_container_width=True, hide_index=True)
        excel = excel_download(detalle[vista_cols], "Pendientes")
        st.download_button("📥 Descargar Excel unificado", data=excel, file_name=f"pendientes_instalacion_{eh}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        texto = "📋 PENDIENTES DE INSTALACIÓN\n\n" + f"👤 Socio: {nombre}\nEH: {eh}\n📌 Total pendientes: {len(detalle)}\n\n"
        for _, row in detalle.iterrows():
            texto += f"🔹 Código: {row['CLIENTE_NRO']}\n📅 Generado: {row['FECHA_REPORTE']}\n📍 Nodo: {row.get('NODO_NOMBRE','')}\n📞 Titular: {row.get('TEL_TITULAR','')}\n"
            if row.get("TEL_REF1", ""): texto += f"📞 Ref. 1: {row.get('TEL_REF1','')}\n"
            if row.get("TEL_REF2", ""): texto += f"📞 Ref. 2: {row.get('TEL_REF2','')}\n"
            texto += f"📝 CRM: {row.get('ANALISIS_CRM','')}\n\n"
        st.text_area("Mensaje WhatsApp", value=texto, height=520, key=f"txt_pend_inst_{eh}_{len(detalle)}")
        st.link_button("📲 Compartir por WhatsApp", "https://wa.me/?text=" + urllib.parse.quote(texto))
    except Exception as e:
        st.error(f"Error al procesar pendientes de instalación: {e}")
