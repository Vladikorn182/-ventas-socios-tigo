import streamlit as st
import urllib.parse
from .comun import obtener_distincion, mensaje_motivador

def whatsapp(df, resumen):
    st.subheader("📱 Reportes para WhatsApp")
    if resumen is None:
        st.info("Primero sube el archivo GrossAdd."); return
    opcion = st.radio("Tipo de reporte", ["Resumen individual", "Seguimiento individual con códigos instalados", "Reporte general"], key="radio_whatsapp")
    if opcion in ["Resumen individual", "Seguimiento individual con códigos instalados"]:
        socio = st.selectbox("Selecciona socio", resumen["VENDEDOR_NOMBRE"], key="sel_whatsapp")
        fila = resumen[resumen["VENDEDOR_NOMBRE"] == socio].iloc[0]
        posicion = int(fila["POSICION"]); dist = obtener_distincion(posicion); motivador = mensaje_motivador(posicion)
        texto = "📊 AVANCE DE VENTAS\n\n"
        if dist: texto += f"{dist}\n\n"
        texto += (f"👤 {fila['VENDEDOR_NOMBRE']}\nEH: {fila['VENDEDOR_EH']}\n\n"
                  f"✅ Ventas objetivo: {fila['Ventas_Objetivo']}\n🔄 Crosselling: {fila['Crosselling']}\n📊 Total ventas: {fila['Total_Ventas']}\n\n"
                  f"🎯 Objetivo: {fila['OBJETIVO']}\n📈 Cumplimiento: {fila['CUMPLIMIENTO']}%\n⏳ Faltan: {fila['FALTAN']}\n\n{motivador}\n")
        if opcion == "Seguimiento individual con códigos instalados":
            detalle = df[df["VENDEDOR_NOMBRE"] == fila["VENDEDOR_NOMBRE"]][["CLIENTE_NRO","CLIENTE_NOMBRE","FECHA_INSTALACION","TIPO_CONTEO"]]
            ventas_objetivo = detalle[detalle["TIPO_CONTEO"] == "VENTA_OBJETIVO"]
            crosselling = detalle[detalle["TIPO_CONTEO"] == "CROSSSELLING"]
            texto += "\n✅ CÓDIGOS QUE CUENTAN AL OBJETIVO:\n\n"
            texto += "".join([f"🔹 {v['CLIENTE_NRO']} | {v['CLIENTE_NOMBRE']} | {v['FECHA_INSTALACION']}\n" for _, v in ventas_objetivo.iterrows()]) or "Sin códigos nuevos para objetivo.\n"
            texto += "\n🔄 CROSSSELLING / CÓDIGOS ANTIGUOS:\n\n"
            texto += "".join([f"🔸 {v['CLIENTE_NRO']} | {v['CLIENTE_NOMBRE']} | {v['FECHA_INSTALACION']}\n" for _, v in crosselling.iterrows()]) or "Sin crosselling registrado.\n"
        st.text_area("Mensaje", texto, height=520, key="txt_whatsapp")
        st.link_button("📲 Compartir por WhatsApp", "https://wa.me/?text=" + urllib.parse.quote(texto))
    else:
        texto = "📊 AVANCE GENERAL DE VENTAS\n\n"
        for _, row in resumen.iterrows():
            texto += (f"{row['MEDALLA']} {row['VENDEDOR_NOMBRE']}\n✅ Objetivo: {row['Ventas_Objetivo']}\n🔄 Crosselling: {row['Crosselling']}\n📊 Total: {row['Total_Ventas']}\n🎯 Meta: {row['OBJETIVO']}\n📈 {row['CUMPLIMIENTO']}% | Faltan: {row['FALTAN']}\n----------------------\n")
        st.text_area("Mensaje general", texto, height=520, key="txt_whatsapp_general")
        st.link_button("📲 Compartir reporte general", "https://wa.me/?text=" + urllib.parse.quote(texto))
