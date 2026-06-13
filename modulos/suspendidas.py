import streamlit as st
import urllib.parse
from .comun import leer_archivo, normalizar_columnas, analizar_crm

def suspendidas():
    st.subheader("🚨 Suspendidas / Instalaciones no atendidas")
    st.write("Sube el archivo diario de suspendidas para analizar CRM_OBSERVACION y generar reclamos por socio para WhatsApp.")
    archivo = st.file_uploader("📤 Sube archivo Suspendidas", type=["csv","xlsx"], key="suspendidas")
    if not archivo: return
    try:
        data = leer_archivo(archivo)
        if data is None: return
        data = normalizar_columnas(data)
        st.success(f"Archivo cargado: {len(data)} registros")
        if len(data) == 0:
            st.warning("El archivo no tiene registros."); return
        req = ["CLIENTE_NRO","FECHA_REPORTE","VENDEDOR_EH","VENDEDOR_NOMBRE","TIPO_VENTA","CLIENTE_TELEFONO1","NODO_NOMBRE","CRM_OBSERVACION"]
        faltantes = [c for c in req if c not in data.columns]
        if faltantes:
            st.error(f"Faltan columnas: {faltantes}"); st.write("Columnas detectadas:"); st.write(list(data.columns)); return
        data["VENDEDOR_EH"] = data["VENDEDOR_EH"].astype(str)
        data["OBSERVACION_SUGERIDA"] = data["CRM_OBSERVACION"].apply(analizar_crm)
        data["SOCIO_DISPLAY"] = data["VENDEDOR_EH"] + " - " + data["VENDEDOR_NOMBRE"].astype(str)
        resumen = data.groupby(["VENDEDOR_EH","VENDEDOR_NOMBRE","SOCIO_DISPLAY"]).agg(Casos=("CLIENTE_NRO","count")).reset_index().sort_values("VENDEDOR_NOMBRE")
        resumen["MOSTRAR"] = resumen["SOCIO_DISPLAY"] + " (" + resumen["Casos"].astype(str) + " casos)"
        socio_sel = st.selectbox("Selecciona socio", resumen["MOSTRAR"].tolist(), key="sel_susp")
        socio_display = resumen[resumen["MOSTRAR"] == socio_sel]["SOCIO_DISPLAY"].iloc[0]
        detalle = data[data["SOCIO_DISPLAY"] == socio_display].copy().reset_index(drop=True)
        eh = str(detalle["VENDEDOR_EH"].iloc[0]); nombre = str(detalle["VENDEDOR_NOMBRE"].iloc[0])
        st.metric("🚨 Suspendidas", len(detalle))
        texto = "🚨 SUSPENDIDAS / INSTALACIONES NO ATENDIDAS\n\n" + f"👤 Socio: {nombre}\nEH: {eh}\n📌 Total casos: {len(detalle)}\n\n"
        for _, row in detalle.iterrows():
            texto += f"🔹 Código: {row['CLIENTE_NRO']}\n📅 Reporte: {row['FECHA_REPORTE']}\n📞 Tel: {row['CLIENTE_TELEFONO1']}\n📍 Nodo: {row['NODO_NOMBRE']}\n🧾 Tipo venta: {row['TIPO_VENTA']}\n📝 Observación: {row['OBSERVACION_SUGERIDA']}\n\n"
        st.text_area("Mensaje WhatsApp", value=texto, height=520, key=f"txt_susp_{eh}_{len(detalle)}")
        st.link_button("📲 Compartir por WhatsApp", "https://wa.me/?text=" + urllib.parse.quote(texto))
        st.subheader("📋 Detalle analizado")
        st.dataframe(detalle[["CLIENTE_NRO","FECHA_REPORTE","VENDEDOR_EH","VENDEDOR_NOMBRE","TIPO_VENTA","CLIENTE_TELEFONO1","NODO_NOMBRE","CRM_OBSERVACION","OBSERVACION_SUGERIDA"]], use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Error al procesar suspendidas: {e}")
