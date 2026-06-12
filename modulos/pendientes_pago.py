import streamlit as st
import urllib.parse
from .comun import leer_archivo, normalizar_columnas, SOCIOS_DICT

def pendientes_pago():
    st.subheader("💳 Pendientes de Pago")
    st.write("Sube el archivo PENDIENTE_INST_SIN_PAGO, selecciona un socio y envía sus pendientes por WhatsApp.")
    archivo = st.file_uploader("📤 Sube archivo PENDIENTE_INST_SIN_PAGO", type=["csv","xlsx"], key="pendientes_pago")
    if not archivo: return
    try:
        data = leer_archivo(archivo)
        if data is None: return
        data = normalizar_columnas(data)
        st.success(f"Archivo cargado: {len(data)} registros")
        if len(data) == 0:
            st.warning("El archivo no tiene registros pendientes. Solo tiene encabezados."); return
        req = ["CLIENTE_NRO","FECHA_REPORTE","VENDEDOR_EH","CLIENTE_NOMBRE","NODO_NOMBRE","FECHA_GENERACION_OT","CLIENTE_TELEFONO2"]
        faltantes = [c for c in req if c not in data.columns]
        if faltantes:
            st.error(f"Faltan columnas: {faltantes}"); st.write("Columnas detectadas:"); st.write(list(data.columns)); return
        data["VENDEDOR_EH"] = data["VENDEDOR_EH"].astype(str)
        data["SOCIO"] = data["VENDEDOR_EH"].map(SOCIOS_DICT).fillna("SIN NOMBRE")
        data["SOCIO_DISPLAY"] = data["VENDEDOR_EH"] + " - " + data["SOCIO"]
        resumen = data.groupby(["VENDEDOR_EH","SOCIO","SOCIO_DISPLAY"]).agg(Pendientes=("CLIENTE_NRO","count")).reset_index().sort_values("SOCIO")
        resumen["MOSTRAR"] = resumen["SOCIO_DISPLAY"] + " (" + resumen["Pendientes"].astype(str) + " pendientes)"
        socio_sel = st.selectbox("Selecciona socio", resumen["MOSTRAR"], key="sel_pago")
        socio_display = resumen[resumen["MOSTRAR"] == socio_sel]["SOCIO_DISPLAY"].iloc[0]
        detalle = data[data["SOCIO_DISPLAY"] == socio_display].copy().reset_index(drop=True)
        eh = str(detalle["VENDEDOR_EH"].iloc[0]); nombre = str(detalle["SOCIO"].iloc[0])
        st.metric("📌 Pendientes de pago", len(detalle))
        texto = "💳 PENDIENTES DE PAGO\n\n" + f"👤 Socio: {nombre}\nEH: {eh}\n📌 Total pendientes: {len(detalle)}\n\n"
        for _, row in detalle.iterrows():
            texto += f"🔹 Código: {row['CLIENTE_NRO']}\n📅 Reporte: {row['FECHA_REPORTE']}\n🗓️ Generación OT: {row['FECHA_GENERACION_OT']}\n👤 Cliente: {row['CLIENTE_NOMBRE']}\n📍 Nodo: {row['NODO_NOMBRE']}\n📞 Tel: {row['CLIENTE_TELEFONO2']}\n\n"
        st.text_area("Mensaje WhatsApp", texto, height=500, key="txt_pago")
        st.link_button("📲 Compartir por WhatsApp", "https://wa.me/?text=" + urllib.parse.quote(texto))
    except Exception as e:
        st.error(f"Error al procesar pendientes de pago: {e}")
