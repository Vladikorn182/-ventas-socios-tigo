import streamlit as st
import urllib.parse
from .comun import obtener_distincion, mensaje_motivador

def whatsapp(df, resumen):
    st.subheader("📱 Reportes para WhatsApp")

    if resumen is None:
        st.info("Primero sube el archivo GrossAdd.")
        return

    opcion = st.radio(
        "Tipo de reporte",
        ["Resumen individual", "Seguimiento individual con códigos instalados", "Reporte general"],
        key="radio_whatsapp"
    )

    if opcion in ["Resumen individual", "Seguimiento individual con códigos instalados"]:
        resumen_tmp = resumen.copy()
        resumen_tmp["VENDEDOR_EH"] = resumen_tmp["VENDEDOR_EH"].astype(str)
        resumen_tmp["MOSTRAR"] = (
            resumen_tmp["VENDEDOR_EH"] + " - " +
            resumen_tmp["VENDEDOR_NOMBRE"].astype(str)
        )

        socio_sel = st.selectbox(
            "Selecciona socio",
            resumen_tmp["MOSTRAR"].tolist(),
            key="sel_whatsapp"
        )

        eh_sel = str(socio_sel).split(" - ")[0]
        fila_df = resumen_tmp[resumen_tmp["VENDEDOR_EH"].astype(str) == eh_sel]

        if fila_df.empty:
            st.warning("No hay datos para el socio seleccionado.")
            return

        fila = fila_df.iloc[0]

        posicion = int(fila["POSICION"])
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
                df["VENDEDOR_EH"].astype(str) == eh_sel
            ][["CLIENTE_NRO", "CLIENTE_NOMBRE", "FECHA_INSTALACION", "TIPO_CONTEO"]].copy()

            ventas_objetivo = detalle[detalle["TIPO_CONTEO"] == "VENTA_OBJETIVO"]
            crosselling = detalle[detalle["TIPO_CONTEO"] == "CROSSSELLING"]

            texto += "\n✅ CÓDIGOS QUE CUENTAN AL OBJETIVO:\n\n"

            if len(ventas_objetivo) > 0:
                for _, v in ventas_objetivo.iterrows():
                    texto += f"🔹 {v['CLIENTE_NRO']} | {v['CLIENTE_NOMBRE']} | {v['FECHA_INSTALACION']}\n"
            else:
                texto += "Sin códigos nuevos para objetivo.\n"

            texto += "\n🔄 CROSSSELLING / CÓDIGOS ANTIGUOS:\n\n"

            if len(crosselling) > 0:
                for _, v in crosselling.iterrows():
                    texto += f"🔸 {v['CLIENTE_NRO']} | {v['CLIENTE_NOMBRE']} | {v['FECHA_INSTALACION']}\n"
            else:
                texto += "Sin crosselling registrado.\n"

        st.text_area(
            "Mensaje",
            value=texto,
            height=520,
            key=f"txt_whatsapp_{eh_sel}_{opcion}"
        )

        st.link_button(
            "📲 Compartir por WhatsApp",
            "https://wa.me/?text=" + urllib.parse.quote(texto)
        )

    else:
        texto = "📊 AVANCE GENERAL DE VENTAS\n\n"

        for _, row in resumen.iterrows():
            texto += (
                f"{row['MEDALLA']} {row['VENDEDOR_NOMBRE']}\n"
                f"✅ Objetivo: {row['Ventas_Objetivo']}\n"
                f"🔄 Crosselling: {row['Crosselling']}\n"
                f"📊 Total: {row['Total_Ventas']}\n"
                f"🎯 Meta: {row['OBJETIVO']}\n"
                f"📈 {row['CUMPLIMIENTO']}% | Faltan: {row['FALTAN']}\n"
                "----------------------\n"
            )

        st.text_area(
            "Mensaje general",
            value=texto,
            height=520,
            key="txt_whatsapp_general_actualizado"
        )

        st.link_button(
            "📲 Compartir reporte general",
            "https://wa.me/?text=" + urllib.parse.quote(texto)
        )
