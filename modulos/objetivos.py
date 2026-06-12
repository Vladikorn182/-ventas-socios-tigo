import streamlit as st
import pandas as pd
from .comun import leer_archivo, normalizar_columnas, get_conn

def objetivos(df):
    st.subheader("🎯 Administración de Objetivos")
    st.write("Carga masiva desde Excel/CSV con columnas:")
    st.code("POS_CODE | POS_OWNER | BU JUNIO")
    archivo_obj = st.file_uploader("📤 Subir archivo de objetivos", type=["csv", "xlsx"], key="objetivos_masivo")
    if archivo_obj:
        try:
            obj = leer_archivo(archivo_obj)
            if obj is not None:
                obj = normalizar_columnas(obj)
                req = ["POS_CODE","POS_OWNER","BU_JUNIO"]
                faltantes = [c for c in req if c not in obj.columns]
                if faltantes:
                    st.error(f"Faltan columnas en el archivo de objetivos: {faltantes}")
                    st.write("Columnas detectadas:"); st.write(list(obj.columns))
                else:
                    obj["POS_CODE"] = obj["POS_CODE"].astype(str)
                    obj["BU_JUNIO"] = pd.to_numeric(obj["BU_JUNIO"], errors="coerce").fillna(0).astype(int)
                    vista = obj[["POS_CODE","POS_OWNER","BU_JUNIO"]].copy(); vista.columns = ["EH","NOMBRE","OBJETIVO"]
                    st.success(f"Objetivos detectados: {len(vista)} socios")
                    st.dataframe(vista, use_container_width=True, hide_index=True)
                    if st.button("💾 Guardar objetivos desde archivo"):
                        conn = get_conn(); cur = conn.cursor()
                        for _, row in vista.iterrows():
                            cur.execute("""
                                INSERT INTO objetivos (EH, NOMBRE, OBJETIVO) VALUES (?, ?, ?)
                                ON CONFLICT(EH) DO UPDATE SET NOMBRE=excluded.NOMBRE, OBJETIVO=excluded.OBJETIVO
                            """, (str(row["EH"]), str(row["NOMBRE"]), int(row["OBJETIVO"])))
                        conn.commit(); conn.close()
                        st.success("Objetivos actualizados correctamente. Presiona F5 para recalcular.")
        except Exception as e:
            st.error(f"Error al procesar objetivos: {e}")
    st.divider(); st.subheader("✍️ Edición manual")
    if df is None:
        st.info("También puedes editar manualmente después de subir el GrossAdd."); return
    socios = df[["VENDEDOR_EH","VENDEDOR_NOMBRE"]].drop_duplicates().sort_values("VENDEDOR_NOMBRE")
    conn = get_conn(); cur = conn.cursor()
    with st.form("form_objetivos"):
        nuevos = []
        for _, row in socios.iterrows():
            eh = str(row["VENDEDOR_EH"]); nombre = row["VENDEDOR_NOMBRE"]
            actual = cur.execute("SELECT OBJETIVO FROM objetivos WHERE EH=?", (eh,)).fetchone()
            valor = int(actual[0]) if actual else 0
            c1,c2,c3 = st.columns([2,5,2]); c1.write(eh); c2.write(nombre)
            objetivo = c3.number_input("Objetivo", min_value=0, value=valor, key=f"obj_{eh}", label_visibility="collapsed")
            nuevos.append((eh,nombre,int(objetivo)))
        if st.form_submit_button("💾 Guardar objetivos manuales"):
            for eh,nombre,objetivo in nuevos:
                cur.execute("""
                    INSERT INTO objetivos (EH, NOMBRE, OBJETIVO) VALUES (?, ?, ?)
                    ON CONFLICT(EH) DO UPDATE SET NOMBRE=excluded.NOMBRE, OBJETIVO=excluded.OBJETIVO
                """, (eh,nombre,objetivo))
            conn.commit(); st.success("Objetivos guardados. Presiona F5 para actualizar.")
    conn.close()
