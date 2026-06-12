import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO

SOCIOS_DICT = {
    "91207": "GUALBERTO FERNANDO SANJINES", "91208": "DANNY QUISBERT MENDOZA",
    "91262": "WARNES RIVERA CHUQUIMIA", "91283": "SOLAGEL QUENTA GUTIERREZ",
    "89859": "JOSE PABLO FERNANDEZ", "89326": "PALMIRA SELAES",
    "88874": "GUSTAVO CALLEJAS", "88463": "ALICIA GRACIELA ZAMORA BUEZO",
    "86963": "TERESA CHIPANA", "83457": "ESTRELLA BELEN QUISPE FLORES",
    "63483": "FRANKLIN RAMIRO QUISPE ROSAS", "79030": "VICTOR HUGO CHAMBILLA FLORES",
    "72210": "GUADALUPE APAZA VILA", "59509": "ADRIANA PAOLA VILLAFUERTE GUERRA",
    "58984": "MARIA SURCO ARUQUIPA", "88426": "SONIA NOEMI MAYTA",
    "89231": "ALEX RUDY MAMANI GUARACHI", "86737": "ANAHI OINCA",
    "78340": "OLIVIA SANCHEZ QUISPE", "78099": "GEOVANA CARLA SIÑANI LUNA",
}

def get_conn():
    return sqlite3.connect("ventas.db", check_same_thread=False)

def init_db():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS objetivos (EH TEXT PRIMARY KEY, NOMBRE TEXT, OBJETIVO INTEGER)")
    cur.execute("CREATE TABLE IF NOT EXISTS configuracion (CLAVE TEXT PRIMARY KEY, VALOR TEXT)")
    cur.execute("INSERT OR IGNORE INTO configuracion (CLAVE, VALOR) VALUES ('codigo_minimo_objetivo', '2671392')")
    conn.commit(); conn.close()

def header():
    st.markdown('''
    <style>
    .main {background-color: #0b1020;}
    .tigo-header {background: linear-gradient(90deg, #0033A0, #00A3E0); padding: 22px; border-radius: 18px; color: white; margin-bottom: 18px;}
    .tigo-logo {font-size: 44px; font-weight: 900; color: white;}
    </style>
    <div class="tigo-header">
        <div class="tigo-logo">TIGO</div>
        <h2>📊 Dashboard de Ventas Socios</h2>
        <p>Seguimiento de objetivos, crosselling, instalados, pendientes y suspendidas</p>
        <hr style="border:1px solid rgba(255,255,255,0.2);">
        <p style="font-size:13px;">👨‍💻 Desarrollado por Vladimir Cuenca López</p>
    </div>
    ''', unsafe_allow_html=True)

def leer_archivo(archivo):
    nombre = archivo.name.lower()
    if nombre.endswith('.csv'):
        return pd.read_csv(archivo, sep=None, engine='python', encoding='latin1')
    if nombre.endswith('.xlsx'):
        return pd.read_excel(archivo)
    st.error('Formato no permitido. Sube CSV o Excel .xlsx')
    return None

def normalizar_columnas(df):
    df = df.copy()
    df.columns = [str(c).strip().upper().replace(' ', '_') for c in df.columns]
    return df

def obtener_codigo_minimo():
    conn = get_conn(); cur = conn.cursor()
    valor = cur.execute("SELECT VALOR FROM configuracion WHERE CLAVE='codigo_minimo_objetivo'").fetchone()
    conn.close()
    try:
        return int(valor[0]) if valor else 2671392
    except Exception:
        return 2671392

def guardar_codigo_minimo(valor):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO configuracion (CLAVE, VALOR) VALUES ('codigo_minimo_objetivo', ?)
        ON CONFLICT(CLAVE) DO UPDATE SET VALOR=excluded.VALOR
    """, (str(valor),))
    conn.commit(); conn.close()

def obtener_medalla(posicion):
    return "🥇" if posicion == 1 else "🥈" if posicion == 2 else "🥉" if posicion == 3 else "🏆" if posicion in [4,5] else "📊"

def obtener_distincion(posicion):
    return {1:"🥇 TOP 1 - Excelente trabajo",2:"🥈 TOP 2 - Muy buen avance",3:"🥉 TOP 3 - Gran desempeño",4:"🏆 TOP 5 - Dentro de los mejores socios",5:"🏆 TOP 5 - Dentro de los mejores socios"}.get(posicion, "")

def mensaje_motivador(posicion):
    return {1:"👏 Felicidades, estás liderando el ranking. Sigue así.",2:"👏 Excelente avance, estás entre los mejores.",3:"👏 Gran desempeño, mantén el ritmo.",4:"👏 Muy buen trabajo, estás dentro del Top 5.",5:"👏 Muy buen trabajo, estás dentro del Top 5."}.get(posicion,"💪 Sigamos avanzando hacia el objetivo del mes.")

def analizar_crm(valor):
    obs = str(valor).strip(); o = obs.lower()
    if obs == '' or o in ['nan','none','null']: return 'Sin CRM / sin motivo registrado'
    if any(x in o for x in ['no atend','no se atend','no contacto','no contesta','sin contacto']): return 'Instalación no atendida / contactar cliente'
    if any(x in o for x in ['desiste','desist','rechaza','rechaz','anula','anulacion','cancel']): return 'Cliente desiste / validar cierre'
    if any(x in o for x in ['reagend','agenda','programar','reprogram']): return 'Reagendar instalación'
    if any(x in o for x in ['tecnico','técnico','tap','satur','poste','nodo','factibilidad','cobertura']): return 'Revisión técnica / validar con operaciones'
    if 'transaccion' in o or 'transacción' in o: return 'Transacción / validar estado'
    return 'Instalación pendiente / validar motivo'

def separar_telefonos(valor):
    texto = str(valor)
    partes = [p.strip() for p in texto.replace(';', ',').split(',') if p.strip()]
    nums = []
    for p in partes:
        n = ''.join([c for c in p if c.isdigit()])
        if len(n) >= 7 and n not in nums:
            nums.append(n)
    return (nums[0] if len(nums)>0 else '', nums[1] if len(nums)>1 else '', nums[2] if len(nums)>2 else '')

def excel_download(df, sheet_name='Datos'):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output
