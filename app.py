import streamlit as st
import mysql.connector
from datetime import date, datetime
import time
import pandas as pd
from fpdf import FPDF
# Reemplaza la línea vieja por esta:
from admin_dashboard import renderizar_tablero_combos_admin

# =====================================================================
# 🛠️ 1. CONEXIÓN A LA BASE DE DATOS LOCAL (MySQL Original de la App)
# =====================================================================
def conectar_db():
    """
    Establece la conexión con la base de datos local de control de cajas.
    """
    return mysql.connector.connect(
        host="localhost",
        user="SysAdmin",          
        password="edPZTX__0RWhE-LQ",  
        database="control_happywok"
    )

# =====================================================================
# FUNCTION AGREGADA DIRECTAMENTE EN APP.PY PARA EVITAR ERROR DE IMPORT
# =====================================================================

def renderizar_tablero_cobros_admin(id_sucursal, nombre_sucursal):
    st.markdown(f"### 💳 Auditoría de Cobros en Sistema - {nombre_sucursal}")
    st.caption("Consulta en tiempo real de importes de cobros registrados en Microsip")
    
    # Usamos tu diccionario de mapeo exacto por nombre
    MAPEO_ALMACENES = {
        1: "ALMACEN ORIENTE",       # Arcoiris
        2: "ALMACEN CUATRO C...",   # 4 Caminos (Modifica los puntos si en Microsip se llama diferente)
        3: "ALMACEN TRIANA",        # Triana
        4: "ALMACEN ROSITA",        # Rosita
        5: "ALMACEN VINEDOS"        # Viñedos
    }
    
    nombre_almacen_microsip = MAPEO_ALMACENES.get(id_sucursal, None)
    
    if not nombre_almacen_microsip:
        st.warning("⚠️ Esta sucursal no tiene un almacén configurado para cobros.")
        return

    col_f, col_b = st.columns([3, 1])
    with col_f:
        fecha_consulta = st.date_input("📅 Fecha de Cobros", date.today(), key="fecha_cobros_microsip")
    with col_b:
        st.write("")
        st.button("🔄 Actualizar", use_container_width=True, key="btn_refresh_cobros")
    
    try:
        from consultas_microsip import obtener_cobros_microsip
        # Mandamos el nombre real de texto del almacén
        df_cobros = obtener_cobros_microsip(fecha_consulta, nombre_almacen_microsip)
    except Exception as e:
        st.error(f"❌ Error al enlazar con el módulo de cobros: {e}")
        return

    if df_cobros.empty:
        st.info(f"📅 No se encontraron cobros registrados el día {fecha_consulta.strftime('%d/%m/%Y')} en {nombre_almacen_microsip}.")
        return

    df_cobros.columns = [c.upper() for c in df_cobros.columns]
    df_cobros['IMPORTE'] = df_cobros['IMPORTE'].astype(float)
    resumen_cobros = df_cobros.groupby('FORMA_COBRO')['IMPORTE'].sum().reset_index()
    total_cobrado = df_cobros['IMPORTE'].sum()
    
    st.markdown(f"#### **Total Cobrado en Microsip:** ${total_cobrado:,.2f}")
    cols_metodos = st.columns(len(resumen_cobros))
    for i, row in resumen_cobros.iterrows():
        with cols_metodos[i]:
            st.metric(label=f"💰 {row['FORMA_COBRO']}", value=f"${row['IMPORTE']:,.2f}")
            
    st.write("---")
    col_izq, col_der = st.columns([1, 1.2])
    with col_izq:
        st.markdown("##### 📊 Distribución por Métodos")
        df_chart = resumen_cobros.set_index("FORMA_COBRO")
        st.bar_chart(df_chart, color="#2E7D32", use_container_width=True)
    with col_der:
        st.markdown("##### 📋 Transacciones del Turno")
        df_mostrar = df_cobros.copy()
        df_mostrar['IMPORTE'] = df_mostrar['IMPORTE'].map('${:,.2f}'.format)
        st.dataframe(df_mostrar[['FOLIO', 'FORMA_COBRO', 'IMPORTE', 'ALMACEN']], use_container_width=True, hide_index=True)



# =====================================================================
# 2. GENERADOR DE PDF PERSONALIZADO (FPDF Sin errores binarios ni Unicode)
# =====================================================================
class PDF_Reporte(FPDF):
    def header(self):
        self.set_font("Arial", 'B', 15)
        self.cell(0, 10, "HAPPYWOK - REPORTE DE CONTROL DE CAJA Y BARRA", 0, 1, 'C')
        self.ln(3)
    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", 'I', 8)
        self.cell(0, 10, f"Pagina {self.page_no()}", 0, 0, 'C')

def generar_pdf_datos(datos_reporte, datos_efectivo, historial_cocina):
    pdf = PDF_Reporte()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    
    def limpiar(texto):
        if not texto: return ""
        txt_limpio = "".join(c for c in str(texto) if c.isalnum() or c in " $.,:-()/")
        txt_limpio = txt_limpio.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        txt_limpio = txt_limpio.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("Ñ", "N")
        return txt_limpio
    
    # 1. INFORMACIÓN GENERAL
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "1. Informacion General", 0, 1, 'L')
    pdf.set_font("Arial", size=10)
    pdf.cell(95, 6, f"Sucursal: {limpiar(datos_reporte['sucursal'])}", 0, 0)
    pdf.cell(95, 6, f"Fecha Reporte: {limpiar(datos_reporte['fecha'])}", 0, 1)
    pdf.cell(95, 6, f"Fondo Inicial: ${datos_reporte['fondo_inicial']:,.2f}", 0, 0)
    pdf.cell(95, 6, f"Fondo Siguiente Dia: ${datos_reporte['fondo_siguiente']:,.2f}", 0, 1)
    pdf.cell(95, 6, f"Personal de Cocina: {limpiar(datos_reporte['cocineros'])}", 0, 1)
    pdf.ln(4)
    
    # 2. FINANZAS / INGRESOS
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "2. Ingresos y Ventas en Sistema", 0, 1, 'L')
    pdf.set_font("Arial", size=10)
    pdf.cell(63, 6, f"Efectivo Sistema: ${datos_reporte['v_efectivo']:,.2f}", 1, 0)
    pdf.cell(63, 6, f"Tarjetas: ${datos_reporte['v_tarjetas']:,.2f}", 1, 0)
    pdf.cell(64, 6, f"Apps Delivery: ${datos_reporte['v_apps']:,.2f}", 1, 1)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 7, f"VENTA TOTAL BRUTA: ${datos_reporte['v_total']:,.2f}", 0, 1, 'R')
    pdf.ln(4)
    
    # 3. AUDITORÍA DE CAJA Y ARQUEO
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "3. Arqueo y Desglose de Caja", 0, 1, 'L')
    pdf.set_font("Arial", size=10)
    pdf.cell(95, 6, f"Efectivo Esperado: ${datos_reporte['efectivo_esperado']:,.2f}", 0, 0)
    pdf.cell(95, 6, f"Efectivo Fisico Contado: ${datos_reporte['efectivo_contado']:,.2f}", 0, 1)
    
    descuadre = datos_reporte['efectivo_contado'] - datos_reporte['efectivo_esperado']
    pdf.set_font("Arial", 'B', 11)
    if abs(descuadre) < 0.01:
        pdf.cell(0, 7, "ESTATUS: CAJA CUADRADA (OK)", 0, 1, 'L')
    elif descuadre < 0:
        pdf.cell(0, 7, f"ESTATUS: FALTANTE DE -${abs(descuadre):,.2f}", 0, 1, 'L')
    else:
        pdf.cell(0, 7, f"ESTATUS: SOBRANTE DE +${descuadre:,.2f}", 0, 1, 'L')
    
    pdf.set_font("Arial", 'B', 9)
    pdf.ln(2)
    pdf.cell(0, 5, "Detalle de Efectivo en Caja:", 0, 1, 'L')
    pdf.set_font("Arial", size=9)
    
    contador_items = 0
    for denominacion, cantidad in datos_efectivo.items():
        if cantidad > 0:
            valor_facial = float(denominacion.replace("b", "").replace("m", "").replace("05", "0.5"))
            total_denom = cantidad * valor_facial
            tipo_txt = "Billete" if denominacion.startswith("b") else "Moneda"
            pdf.cell(60, 5, f"  - {tipo_txt} de ${valor_facial:,.1f}: {cantidad} pzas", 0, 0)
            pdf.cell(40, 5, f"Subtotal: ${total_denom:,.2f}", 0, 1, 'R')
            contador_items += 1
            
    if contador_items == 0:
        pdf.cell(0, 5, "  (No se desglosaron billetes o monedas en el sistema)", 0, 1)
    pdf.ln(4)
    
    # 4. GASTOS
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "4. Gastos Autorizados del Turno", 0, 1, 'L')
    pdf.set_font("Arial", size=10)
    if datos_reporte['gastos']:
        for g in datos_reporte['gastos']:
            pdf.cell(130, 6, f"- {limpiar(g['concepto'])}", 0, 0)
            pdf.cell(60, 6, f"${g['monto']:,.2f}", 0, 1, 'R')
    else:
        pdf.cell(0, 6, "No se registraron gastos en este turno.", 0, 1)
    pdf.ln(4)
    
    # 5. INVENTARIO
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "5. Arqueo de Inventario", 0, 1, 'L')
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, f"Refrescos Desplazados (Fisico): {datos_reporte['refrescos_vendidos']} pzas", 0, 1)
    pdf.cell(0, 6, f"HappyCombos Restantes para Donacion: {datos_reporte['combos_donacion']} pzas", 0, 1)
    pdf.ln(4)
    
    # 6. PRODUCCIÓN DE COCINA
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "6. Resumen de Produccion (Kilos Enviados a Barra)", 0, 1, 'L')
    pdf.set_font("Arial", size=10)
    if datos_reporte['platillos_resumen']:
        for p in datos_reporte['platillos_resumen']:
            pdf.cell(130, 6, f"  - {limpiar(p['Platillo / Alimento'])}", 0, 0)
            pdf.cell(60, 6, f"{p['Total Enviado Hoy (Kilos)']}", 0, 1, 'R')
    else:
        pdf.cell(0, 6, "No hay movimientos de barra registrados hoy.", 0, 1)
        
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 6, "Historial Cronologico de Envios a Barra:", 0, 1, 'L')
    
    if historial_cocina:
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(35, 5, "Hora Envio", 1, 0, 'C')
        pdf.cell(115, 5, "Platillo / Alimento", 1, 0, 'L')
        pdf.cell(40, 5, "Cant. Enviada", 1, 1, 'C')
        
        pdf.set_font("Arial", size=9)
        for h in historial_cocina:
            pdf.cell(35, 5, f"{h['Hora de Envío']}", 1, 0, 'C')
            pdf.cell(115, 5, f" {limpiar(h['Platillo / Alimento'])}", 1, 0, 'L')
            pdf.cell(40, 5, f"{h['Kilos Enviados']:,.2f} kg", 1, 1, 'C')
    else:
        pdf.set_font("Arial", 'I', 9)
        pdf.cell(0, 5, "  No hay historial de entregas registradas en este turno.", 0, 1)
        
    return bytes(pdf.output(dest='S'))

# Configuración de la página web
st.set_page_config(page_title="HappyWok - Sistema Integral", page_icon="🥡", layout="wide")

if 'lista_gastos' not in st.session_state:
    st.session_state.lista_gastos = []

# =====================================================================
# SISTEMA DE LOGIN
# =====================================================================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'usuario_rol' not in st.session_state:
    st.session_state.usuario_rol = None 
if 'sucursal_asignada' not in st.session_state:
    st.session_state.sucursal_asignada = None
if 'id_sucursal_asignada' not in st.session_state:
    st.session_state.id_sucursal_asignada = None

CREDENCIALES = {
    "arcoiris": {"password": "123", "rol": "Sucursal", "nombre_suc": "Arcoiris", "id_suc": 1},
    "caminos": {"password": "123", "rol": "Sucursal", "nombre_suc": "4 Caminos", "id_suc": 2},
    "triana": {"password": "123", "rol": "Sucursal", "nombre_suc": "Triana", "id_suc": 3},
    "rosita": {"password": "123", "rol": "Sucursal", "nombre_suc": "Rosita", "id_suc": 4},
    "viñedos": {"password": "123", "rol": "Sucursal", "nombre_suc": "Viñedos", "id_suc": 5},
    "admin": {"password": "123", "rol": "Admin", "nombre_suc": "Todas", "id_suc": 0}
}

SUCURSALES_MAP = {info["id_suc"]: info["nombre_suc"] for usr, info in CREDENCIALES.items() if info["id_suc"] > 0}

if not st.session_state.autenticado:
    st.markdown("<h2 style='text-align: center;'>🥡 HappyWok Login</h2>", unsafe_allow_html=True)
    
    with st.form("formulario_login"):
        usuario_input = st.text_input("Usuario / Sucursal", placeholder="Ej: arcoiris, admin").strip().lower()
        password_input = st.text_input("Contraseña", type="password")
        boton_entrar = st.form_submit_button("🔓 Desbloquear Sistema", use_container_width=True)
        
        if boton_entrar:
            if usuario_input in CREDENCIALES and CREDENCIALES[usuario_input]["password"] == password_input:
                info_user = CREDENCIALES[usuario_input]
                st.session_state.autenticado = True
                st.session_state.usuario_rol = info_user["rol"]
                st.session_state.sucursal_asignada = info_user["nombre_suc"]
                st.session_state.id_sucursal_asignada = info_user["id_suc"]
                st.success(f"¡Acceso concedido! Rol: {info_user['rol']}")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas.")
    st.stop() 

# Barra lateral para cerrar sesión
with st.sidebar:
    st.markdown(f"### 👤 Conectado como:\n**{st.session_state.sucursal_asignada}** ({st.session_state.usuario_rol})")
    if st.button("🔒 Cerrar Sesión", type="secondary", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario_rol = None
        st.session_state.sucursal_asignada = None
        st.session_state.id_sucursal_asignada = None
        st.session_state.lista_gastos = []
        st.rerun()


if st.session_state.get('usuario_rol') == "Admin":
    st.title("👑 Panel de Administración Central")
    
    sucursal_seleccionada = st.selectbox(
        "🔍 Selecciona la sucursal que deseas monitorear:",
        options=list(SUCURSALES_MAP.keys()),
        format_func=lambda x: SUCURSALES_MAP[x]
    )
    st.write("---")
    
    # 📑 Las pestañas nativas
    tab_combos, tab_cobros = st.tabs(["🍱 Monitor de Combos (Microsip)", "💳 Auditoría de Cobros / Ingresos"])
    
    with tab_combos:
        # Esta viene de admin_dashboard.py
        renderizar_tablero_combos_admin(sucursal_seleccionada, SUCURSALES_MAP[sucursal_seleccionada])
        
    with tab_cobros:
        # Esta se ejecuta aquí mismo en app.py, ¡adiós ImportError!
        renderizar_tablero_cobros_admin(sucursal_seleccionada, SUCURSALES_MAP[sucursal_seleccionada])
        
    # ❌ SIN st.stop() para que permita cargar el botón del PDF abajo de forma limpia
    
    # 2. Carga limpia y aislada desde la base de datos de los registros de hoy para el PDF de abajo
    reporte_existente_admin = None
    efectivo_existente_admin = None
    inventario_existente_admin = None
    
    try:
        conn_admin = conectar_db()
    
        cursor_admin = conn_admin.cursor(dictionary=True, buffered=True) 
        query_load_rep = "SELECT * FROM reportes_caja WHERE id_sucursal = %s AND fecha = CURDATE()"
        cursor_admin.execute(query_load_rep, (sucursal_seleccionada,))
        reporte_existente_admin = cursor_admin.fetchone()
        
        if reporte_existente_admin:
            id_rep_admin = reporte_existente_admin['id_reporte']
            
            query_load_efe = "SELECT * FROM desglose_efectivo WHERE id_reporte = %s"
            cursor_admin.execute(query_load_efe, (id_rep_admin,))
            efectivo_existente_admin = cursor_admin.fetchone()
            
            query_load_inv = "SELECT * FROM arqueo_inventario WHERE id_reporte = %s"
            cursor_admin.execute(query_load_inv, (id_rep_admin,))
            inventario_existente_admin = cursor_admin.fetchone()
            
        cursor_admin.close()
        conn_admin.close()
    except Exception as e:
        st.error(f"Error al precargar datos de administración: {e}")

    # 3. Renderizar exportación a PDF si existe el reporte del día de hoy
    if reporte_existente_admin:
        st.markdown("---")
        st.header("🖨️ Exportación e Impresión del Reporte")
        
        historial_pdf_actualizado = []
        resumen_pdf_actualizado = []
        gastos_bd_admin = []
        val_cocineros_admin = "Sin registrar"
        
        try:
            conn_pdf = conectar_db()
            cursor_pdf = conn_pdf.cursor(dictionary=True)
            id_rep_real = int(reporte_existente_admin['id_reporte'])
            
            # Totales de Cocina
            query_tot_pdf = """
                SELECT a.nombre_alimento, SUM(m.kilos_calculados) as total_kilos 
                FROM control_cocina_movimientos m
                JOIN alimentos a ON m.id_alimento = a.id_alimento
                WHERE m.id_reporte = %s 
                GROUP BY m.id_alimento, a.nombre_alimento
                ORDER BY total_kilos DESC
            """
            cursor_pdf.execute(query_tot_pdf, (id_rep_real,))
            for r in cursor_pdf.fetchall():
                resumen_pdf_actualizado.append({
                    "Platillo / Alimento": r.get('nombre_alimento', 'Sin nombre'),
                    "Total Enviado Hoy (Kilos)": f"{float(r.get('total_kilos', 0.0)):,.2f} kg"
                })

            # Historial Cronológico
            query_movs_pdf = """
                SELECT a.nombre_alimento, m.kilos_calculados, m.hora_captura 
                FROM control_cocina_movimientos m
                JOIN alimentos a ON m.id_alimento = a.id_alimento
                WHERE m.id_reporte = %s 
                ORDER BY m.id_movimiento DESC
            """
            cursor_pdf.execute(query_movs_pdf, (id_rep_real,))
            for mov in cursor_pdf.fetchall():
                kilos_mov = float(mov.get('kilos_calculados', 0.0))
                nombre_platillo = mov.get('nombre_alimento', 'Sin nombre')
                hora_raw = mov.get('hora_captura')
                cada_hora_formateada = "--:--"
                if hora_raw is not None:
                    str_hora = str(hora_raw).split(".")[0].split(" ")[-1].split()[-1]
                    if ":" in str_hora:
                        try:
                            partes = str_hora.split(":")
                            hh = int(partes[0])
                            mm = int(partes[1])
                            am_pm = "PM" if hh >= 12 else "AM"
                            hh_12 = hh % 12 if hh % 12 != 0 else 12
                            cada_hora_formateada = f"{hh_12:02d}:{mm:02d} {am_pm}"
                        except:
                            cada_hora_formateada = str_hora
                    else:
                        cada_hora_formateada = str_hora

                historial_pdf_actualizado.append({
                    "Hora de Envío": cada_hora_formateada,
                    "Platillo / Alimento": nombre_platillo,
                    "Kilos Enviados": kilos_mov
                })
                
            # Gastos Autorizados
            cursor_pdf.execute("SELECT concepto, monto FROM gastos_autorizados WHERE id_reporte = %s", (id_rep_real,))
            gastos_bd_admin = cursor_pdf.fetchall()
            
            # Personal de cocina
            cursor_pdf.execute("SELECT cocineros FROM control_cocina_encargados WHERE id_reporte = %s", (id_rep_real,))
            enc_bd = cursor_pdf.fetchone()
            if enc_bd:
                val_cocineros_admin = enc_bd['cocineros']
                
            cursor_pdf.close()
            conn_pdf.close()
        except Exception as e_fetch:
            print(f"[DEBUG] Error recargando datos para el PDF en modo Admin: {e_fetch}")

        # Cálculos de los ingresos del reporte
        v_efe = float(reporte_existente_admin['ventas_efectivo_sistema'])
        v_tar = float(reporte_existente_admin['ventas_tarjetas'])
        v_app = float(reporte_existente_admin['ventas_apps'])
        v_tot = v_efe + v_tar + v_app
        f_ini = float(reporte_existente_admin['fondo_inicial'])
        f_sig = float(reporte_existente_admin['fondo_siguiente_dia'])
        tot_gastos_admin = sum(float(x['monto']) for x in gastos_bd_admin)
        
        # Desplazamiento de refrescos e inventario
        ref_inicio_admin = int(inventario_existente_admin['refresco_inicio']) if inventario_existente_admin else 0
        ref_surtido_admin = int(inventario_existente_admin['refresco_surtido']) if inventario_existente_admin else 0
        ref_final_admin = int(inventario_existente_admin['refresco_final']) if inventario_existente_admin else 0
        refrescos_desplazados_admin = (ref_inicio_admin + ref_surtido_admin) - ref_final_admin
        
        com_total_admin = int(inventario_existente_admin['happycombo_total']) if inventario_existente_admin else 0
        com_corte_admin = int(inventario_existente_admin['happycombo_vendidos_corte']) if inventario_existente_admin else 0
        com_despues_admin = int(inventario_existente_admin['happycombo_vendidos_despues']) if inventario_existente_admin else 0
        combos_donacion_admin = com_total_admin - com_corte_admin - com_despues_admin

        paquete_datos_pdf = {
            "sucursal": SUCURSALES_MAP[sucursal_seleccionada], 
            "fecha": str(reporte_existente_admin['fecha']),
            "fondo_inicial": f_ini,
            "fondo_siguiente": f_sig,
            "cocineros": val_cocineros_admin,
            "v_efectivo": v_efe,
            "v_tarjetas": v_tar,
            "v_apps": v_app,
            "v_total": v_tot,
            "efectivo_esperado": (v_efe + f_ini) - tot_gastos_admin,
            "efectivo_contado": float(efectivo_existente_admin['total_efectivo_fisico']) if efectivo_existente_admin else 0.0,
            "gastos": gastos_bd_admin,
            "refrescos_vendidos": refrescos_desplazados_admin if refrescos_desplazados_admin >= 0 else 0, 
            "combos_donacion": combos_donacion_admin if combos_donacion_admin >= 0 else 0,
            "platillos_resumen": resumen_pdf_actualizado
        }
        
        paquete_efectivo_real = {
            "b500": int(efectivo_existente_admin['b500']) if efectivo_existente_admin else 0,
            "b200": int(efectivo_existente_admin['b200']) if efectivo_existente_admin else 0,
            "b100": int(efectivo_existente_admin['b100']) if efectivo_existente_admin else 0,
            "b50": int(efectivo_existente_admin['b50']) if efectivo_existente_admin else 0,
            "b20": int(efectivo_existente_admin['b20']) if efectivo_existente_admin else 0,
            "m10": int(efectivo_existente_admin['m10']) if efectivo_existente_admin else 0,
            "m5": int(efectivo_existente_admin['m5']) if efectivo_existente_admin else 0,
            "m2": int(efectivo_existente_admin['m2']) if efectivo_existente_admin else 0,
            "m1": int(efectivo_existente_admin['m1']) if efectivo_existente_admin else 0,
            "m05": int(float(efectivo_existente_admin['m05'])) if efectivo_existente_admin else 0
        }
        
        try:
            st.download_button(
                label="📥 Generar y Descargar PDF del Turno (Modo Admin)",
                data=generar_pdf_datos(paquete_datos_pdf, paquete_efectivo_real, historial_pdf_actualizado),
                file_name=f"Reporte_{paquete_datos_pdf['sucursal']}_{paquete_datos_pdf['fecha']}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="btn_descarga_pdf_real_admin"
            )
            st.caption("💡 El documento incluye el arqueo de caja con desglose de billetes y la auditoría de cocina línea por línea.")
        except Exception as pdf_err:
            st.error(f"Error al preparar el archivo PDF: {pdf_err}")
    else:
        st.warning("⚠️ No se encontró ningún reporte registrado en la base de datos para esta sucursal el día de hoy.")

    # 🛑 MURO INFRANQUEABLE: Detiene por completo la app para que el Admin no vea el formulario del cajero
    st.stop()


# =====================================================================
# 🏪 VISTA EXCLUSIVA PARA LOS CAJEROS / SUCURSALES (CAPTURA DE DATOS)
# =====================================================================
tab_captura = st.container()

with tab_captura:
    st.title("🥡 Control de Reporte de Caja")
    st.write("Complete los campos según el formato físico del día.")

    st.header("Información General")
    col1, col2 = st.columns(2)

    with col1:
        fecha_reporte = st.date_input("Fecha del Reporte", date.today(), key="fecha_captura_gen")
        st.text_input("Sucursal Activa", value=st.session_state.sucursal_asignada, disabled=True)
        id_sucursal = st.session_state.id_sucursal_asignada

    # Carga de datos existentes desde BD
    reporte_existente = None
    efectivo_existente = None
    inventario_existente = None

    try:
        conn_load = conectar_db()
        cursor_load = conn_load.cursor(dictionary=True, buffered=True) 
        query_load_rep = "SELECT * FROM reportes_caja WHERE id_sucursal = %s AND fecha = %s"
        cursor_load.execute(query_load_rep, (id_sucursal, fecha_reporte))
        reporte_existente = cursor_load.fetchone()
        
        if reporte_existente:
            id_rep = reporte_existente['id_reporte']
            query_load_efe = "SELECT * FROM desglose_efectivo WHERE id_reporte = %s"
            cursor_load.execute(query_load_efe, (id_rep,))
            efectivo_existente = cursor_load.fetchone()
            query_load_inv = "SELECT * FROM arqueo_inventario WHERE id_reporte = %s"
            cursor_load.execute(query_load_inv, (id_rep,))
            inventario_existente = cursor_load.fetchone()
            
        cursor_load.close()
        conn_load.close()
    except Exception as e:
        st.error(f"Error al cargar datos iniciales: {e}")

    val_fondo_inicial = float(reporte_existente['fondo_inicial']) if reporte_existente else 0.0
    val_fondo_siguiente = float(reporte_existente['fondo_siguiente_dia']) if reporte_existente else 0.0

    with col2:
        fondo_inicial = st.number_input("Fondo Inicial ($)", min_value=0.0, step=10.0, value=val_fondo_inicial)
        fondo_siguiente = st.number_input("Fondo Siguiente Día ($)", min_value=0.0, step=10.0, value=val_fondo_siguiente)

    st.divider()

    # Carga de gastos autorizados en memoria
    if reporte_existente and not st.session_state.lista_gastos:
        try:
            conn_init = conectar_db()
            cursor_init = conn_init.cursor()
            query_get_gastos = """
                SELECT g.concepto, g.monto FROM gastos_autorizados g
                JOIN reportes_caja r ON g.id_reporte = r.id_reporte
                WHERE r.id_sucursal = %s AND r.fecha = %s
            """
            cursor_init.execute(query_get_gastos, (id_sucursal, fecha_reporte))
            for g in cursor_init.fetchall():
                st.session_state.lista_gastos.append({"concepto": g[0], "monto": float(g[1])})
            cursor_init.close()
            conn_init.close()
        except:
            pass

    st.header("1. Corte de Caja y Desglose de Efectivo")
    col_ing, col_des = st.columns([1, 1.2])

    val_ventas_efectivo = float(reporte_existente['ventas_efectivo_sistema']) if reporte_existente else 0.0
    val_ventas_tarjetas = float(reporte_existente['ventas_tarjetas']) if reporte_existente else 0.0
    val_ventas_apps     = float(reporte_existente['ventas_apps']) if reporte_existente else 0.0

    with col_ing:
        st.subheader("📊 Ingresos en Sistema")
        ventas_efectivo_sistema = st.number_input("Ventas Efectivo Sistema ($)", min_value=0.0, step=50.0, value=val_ventas_efectivo, key="v_efectivo_sis")
        ventas_tarjetas = st.number_input("Tarjetas ($)", min_value=0.0, step=50.0, value=val_ventas_tarjetas, key="v_tarjetas_sis")
        ventas_apps = st.number_input("Aplicaciones (DiDi/Uber/Rappi) ($)", min_value=0.0, step=50.0, value=val_ventas_apps, key="v_apps_sis")
        
        venta_total_sistema = ventas_efectivo_sistema + ventas_tarjetas + ventas_apps
        st.metric(label="Venta Total Bruta (Sistema)", value=f"${venta_total_sistema:,.2f}")
        
        total_gastos = sum(gasto['monto'] for gasto in st.session_state.lista_gastos)
        efectivo_esperado_en_caja = (ventas_efectivo_sistema + fondo_inicial) - total_gastos

    val_b500 = int(efectivo_existente['b500']) if efectivo_existente else 0
    val_b200 = int(efectivo_existente['b200']) if efectivo_existente else 0
    val_b100 = int(efectivo_existente['b100']) if efectivo_existente else 0
    val_b50  = int(efectivo_existente['b50'])  if efectivo_existente else 0
    val_b20  = int(efectivo_existente['b20'])  if efectivo_existente else 0
    val_m10  = int(efectivo_existente['m10'])  if efectivo_existente else 0
    val_m5   = int(efectivo_existente['m5'])   if efectivo_existente else 0
    val_m2   = int(efectivo_existente['m2'])   if efectivo_existente else 0
    val_m1   = int(efectivo_existente['m1'])   if efectivo_existente else 0
    val_m05  = int(float(efectivo_existente['m05'])) if efectivo_existente else 0

    with col_des:
        st.subheader("💵 Tabla de Billetes y Monedas")
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            b500 = st.number_input("500 X", min_value=0, step=1, value=val_b500, key="b_500")
            b200 = st.number_input("200 X", min_value=0, step=1, value=val_b200, key="b_200")
            b100 = st.number_input("100 X", min_value=0, step=1, value=val_b100, key="b_100")
            b50  = st.number_input("50 X", min_value=0, step=1, value=val_b50, key="b_50")
            b20  = st.number_input("20 X", min_value=0, step=1, value=val_b20, key="b_20")
        with sub_col2:
            m10  = st.number_input("10 X", min_value=0, step=1, value=val_m10, key="m_10")
            m5   = st.number_input("5 X", min_value=0, step=1, value=val_m5, key="m_5")
            m2   = st.number_input("2 X", min_value=0, step=1, value=val_m2, key="m_2")
            m1   = st.number_input("1 X", min_value=0, step=1, value=val_m1, key="m_1")
            m05  = st.number_input(".5 X", min_value=0, step=1, value=val_m05, key="m_05")

        total_efectivo_fisico = (
            (b500 * 500) + (b200 * 200) + (b100 * 100) + (b50 * 50) + (b20 * 20) +
            (m10 * 10) + (m5 * 5) + (m2 * 2) + (m1 * 1) + (m05 * 0.5)
        )
        st.info(f"### **TOTAL EFECTIVO CONTADO:** ${total_efectivo_fisico:,.2f}")

    st.divider()

    # Gastos Autorizados
    st.header("2. Gastos Autorizados del Turno")
    def agregar_gasto_callback():
        concepto = st.session_state.temp_concepto
        monto = st.session_state.temp_monto
        if concepto and monto > 0:
            st.session_state.lista_gastos.append({"concepto": concepto, "monto": monto})
        st.session_state.temp_concepto = ""
        st.session_state.temp_monto = 0.0

    col_g1, col_g2 = st.columns([2, 1])
    with col_g1:
        st.text_input("Concepto del Gasto (Ej: Encendedor, DiDi)", key="temp_concepto")
    with col_g2:
        st.number_input("Monto ($)", min_value=0.0, step=5.0, key="temp_monto")

    st.button("➕ Agregar Gasto", on_click=agregar_gasto_callback)

    if st.session_state.lista_gastos:
        st.subheader("📋 Lista de Gastos Registrados")
        st.dataframe(st.session_state.lista_gastos, width="stretch")
        if st.button("🗑️ Borrar todos los gastos"):
            st.session_state.lista_gastos = []
            st.rerun()
    else:
        st.caption("No hay gastos registrados.")

    st.divider()

    # Arqueo de Inventario
    st.header("3. Arqueo de Inventario del Turno")
    val_ref_inicio = int(inventario_existente['refresco_inicio']) if inventario_existente else 0
    val_ref_surtido = int(inventario_existente['refresco_surtido']) if inventario_existente else 0
    val_ref_final   = int(inventario_existente['refresco_final']) if inventario_existente else 0
    val_combo_total = int(inventario_existente['happycombo_total']) if inventario_existente else 0
    val_combo_corte = int(inventario_existente['happycombo_vendidos_corte']) if inventario_existente else 0
    val_combo_despues = int(inventario_existente['happycombo_vendidos_despues']) if inventario_existente else 0

    st.subheader("🥤 Control de Refrescos")
    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        refresco_inicio = st.number_input("Refresco Inicio", min_value=0, value=val_ref_inicio, key="ref_ini")
    with col_r2:
        refresco_surtido = st.number_input("Refresco Surtido", min_value=0, value=val_ref_surtido, key="ref_sur")
    with col_r3:
        refresco_final = st.number_input("Refresco Final", min_value=0, value=val_ref_final, key="ref_fin")

    total_disponible_refrescos = refresco_inicio + refresco_surtido
    refrescos_vendidos_fisico = total_disponible_refrescos - refresco_final
    st.info(f"🥤 **Suma Disponible:** {total_disponible_refrescos} pzas | 📊 **Desplazadas:** {refrescos_vendidos_fisico} pzas")

    st.markdown("---")
    st.subheader("🍱 Control de HappyCombos (Cierre de Turno)")
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        combo_total = st.number_input("1. Total de Combos Armados", min_value=0, value=val_combo_total, key="com_tot")
    with col_c2:
        combo_vendidos_corte = st.number_input("2. Vendidos EN el Corte", min_value=0, value=val_combo_corte, key="com_v_corte")
    with col_c3:
        combo_vendidos_despues = st.number_input("3. Vendidos DESPUÉS del Corte", min_value=0, value=val_combo_despues, key="com_v_despues")

    combo_restantes_donacion = combo_total - combo_vendidos_corte - combo_vendidos_despues
    st.caption("♻️ Registro de combos finales completado.")

    st.divider()

    # =====================================================================
    # 4. CONTROL DE COCINA (FORMULARIO DEL CAJERO)
    # =====================================================================
    val_cocineros = ""
    if reporte_existente:
        try:
            conn_coc = conectar_db()
            cursor_coc = conn_coc.cursor(dictionary=True)
            query_coc = "SELECT cocineros FROM control_cocina_encargados WHERE id_reporte = %s"
            cursor_coc.execute(query_coc, (reporte_existente['id_reporte'],))
            encargados_bd = cursor_coc.fetchone()
            if encargados_bd: 
                val_cocineros = encargados_bd['cocineros']
            cursor_coc.close()
            conn_coc.close()
        except Exception as e: 
            print(f"[DEBUG] Error al cargar cocineros: {e}")

    cocineros = st.text_input("👨‍🍳 Personal de Cocina", value=val_cocineros, key="input_cocineros", placeholder="Ej: Sin registrar")

    st.markdown("---")
    st.subheader("🚀 Captura Rápida de Envío a Barra")
    
    lista_alimentos = []
    try:
        conn_alm = conectar_db()
        cursor_alm = conn_alm.cursor(dictionary=True)
        cursor_alm.execute("SELECT id_alimento, nombre_alimento FROM alimentos ORDER BY nombre_alimento ASC")
        lista_alimentos = cursor_alm.fetchall()
        cursor_alm.close()
        conn_alm.close()
    except Exception as e:
        st.error(f"Error al cargar catálogo de alimentos: {e}")

    historial_final_mostrar = []
    resumen_totales_platillo = []
    totales_por_alimento = {}
    datos_para_grafica = {"Platillo": [], "Kilos": []}

    if lista_alimentos and reporte_existente:
        try:
            conn_hist = conectar_db()
            cursor_hist = conn_hist.cursor(dictionary=True)
            
            query_tot_ind = """
                SELECT a.nombre_alimento, m.id_alimento, SUM(m.kilos_calculados) as total_kilos 
                FROM control_cocina_movimientos m
                JOIN alimentos a ON m.id_alimento = a.id_alimento
                WHERE m.id_reporte = %s 
                GROUP BY m.id_alimento, a.nombre_alimento
                ORDER BY total_kilos DESC
            """
            cursor_hist.execute(query_tot_ind, (int(reporte_existente['id_reporte']),))
            
            for r in cursor_hist.fetchall(): 
                id_alm = r.get('id_alimento')
                tot_k = float(r.get('total_kilos', 0.0))
                nom_alm = r.get('nombre_alimento', 'Sin nombre')
                
                totales_por_alimento[id_alm] = tot_k
                resumen_totales_platillo.append({
                    "Platillo / Alimento": nom_alm,
                    "Total Enviado Hoy (Kilos)": f"{tot_k:,.2f} kg"
                })
                datos_para_grafica["Platillo"].append(nom_alm)
                datos_para_grafica["Kilos"].append(tot_k)
            
            query_movs = """
                SELECT m.id_movimiento, a.nombre_alimento, m.kilos_calculados, m.hora_captura 
                FROM control_cocina_movimientos m
                JOIN alimentos a ON m.id_alimento = a.id_alimento
                WHERE m.id_reporte = %s 
                ORDER BY m.id_movimiento DESC
            """
            cursor_hist.execute(query_movs, (int(reporte_existente['id_reporte']),))
            
            for mov in cursor_hist.fetchall():
                kilos_mov = float(mov.get('kilos_calculados', 0.0))
                nombre_platillo = mov.get('nombre_alimento', 'Sin nombre')
                hora_raw = mov.get('hora_captura')
                cada_hora_formateada = "--:--"

                if hora_raw is not None:
                    str_hora = str(hora_raw).split(".")[0].split(" ")[-1].split()[-1]
                    if ":" in str_hora:
                        try:
                            partes = str_hora.split(":")
                            hh = int(partes[0])
                            mm = int(partes[1])
                            am_pm = "PM" if hh >= 12 else "AM"
                            hh_12 = hh % 12 if hh % 12 != 0 else 12
                            cada_hora_formateada = f"{hh_12:02d}:{mm:02d} {am_pm}"
                        except:
                            cada_hora_formateada = str_hora
                    else:
                        cada_hora_formateada = str_hora

                historial_final_mostrar.append({
                    "Hora de Envío": cada_hora_formateada,
                    "Platillo / Alimento": nombre_platillo,
                    "Kilos Enviados": kilos_mov
                })
            
            cursor_hist.close()
            conn_hist.close()
        except Exception as err_bd:
            st.error(f"Error cargando historial de cocina: {err_bd}")

        col_al1, col_al2, col_al3 = st.columns([2, 1, 1])
        with col_al1:
            nombres_alm = [a['nombre_alimento'] for a in lista_alimentos]
            alimento_seleccionado = st.selectbox("Selecciona el Platillo", nombres_alm)
            info_alimento = next(item for item in lista_alimentos if item["nombre_alimento"] == alimento_seleccionado)
        with col_al2:
            kilos_envio = st.number_input("Cantidad (Kilos)", min_value=0.25, max_value=20.0, value=1.00, step=0.25)
        with col_al3:
            id_actual = info_alimento['id_alimento']
            st.metric("Total de este Platillo Hoy", f"{totales_por_alimento.get(id_actual, 0.00):,.2f} kg")

        if st.button("📥 Registrar Envío a Barra", type="secondary"):
            try:
                conn_ins = conectar_db()
                cursor_ins = conn_ins.cursor()
                cursor_ins.execute("""
                    INSERT INTO control_cocina_movimientos 
                    (id_reporte, id_alimento, cantidad_bandejas, kilos_calculados, hora_captura) 
                    VALUES (%s, %s, %s, %s, NOW())
                """, (int(reporte_existente['id_reporte']), info_alimento['id_alimento'], kilos_envio, kilos_envio))
                conn_ins.commit()
                cursor_ins.close()
                conn_ins.close()
                st.success(f"¡{kilos_envio} kg de {info_alimento['nombre_alimento']} guardados con éxito!")
                time.sleep(0.4)
                st.rerun()
            except Exception as e: 
                st.error(f"Error al insertar movimiento de cocina: {e}")

        st.markdown("#### 📋 Historial de Entregas Realizadas (Línea por Línea)")
        if historial_final_mostrar:
            df_cocina = pd.DataFrame(historial_final_mostrar)
            st.dataframe(df_cocina, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            col_graf1, col_graf2 = st.columns([1, 1.2])
            with col_graf1:
                st.markdown("#### 📊 Totales Acumulados por Variedad")
                df_resumen_platillos = pd.DataFrame(resumen_totales_platillo)
                st.dataframe(df_resumen_platillos, use_container_width=True, hide_index=True)
            with col_graf2:
                st.markdown("#### 📈 Gráfica de Production del Turno (Kilos)")
                if datos_para_grafica["Platillo"]:
                    df_chart = pd.DataFrame(datos_para_grafica).set_index("Platillo")
                    st.bar_chart(df_chart, color="#FF4B4B", use_container_width=True)
        else:
            st.caption("Aún no se han capturado envíos a barra para este turno de cocina.")

    st.divider()

    # =====================================================================
    # BOTÓN GENERAL GUARDAR (EXCLUSIVO DEL CAJERO)
    # =====================================================================
    st.markdown("### 💾 Finalizar Turno")
    if st.button("💾 GUARDAR / ACTUALIZAR REPORTE", type="primary"):
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            
            if reporte_existente:
                id_reporte_generado = reporte_existente['id_reporte']
                cursor.execute("""
                    UPDATE reportes_caja 
                    SET fondo_inicial=%s, fondo_siguiente_dia=%s, ventas_tarjetas=%s, ventas_apps=%s, ventas_efectivo_sistema=%s 
                    WHERE id_reporte=%s
                """, (fondo_inicial, fondo_siguiente, ventas_tarjetas, ventas_apps, ventas_efectivo_sistema, id_reporte_generado))
                
                cursor.execute("""
                    UPDATE desglose_efectivo 
                    SET b500=%s, b200=%s, b100=%s, b50=%s, b20=%s, m10=%s, m5=%s, m2=%s, m1=%s, m05=%s, total_efectivo_fisico=%s 
                    WHERE id_reporte=%s
                """, (b500, b200, b100, b50, b20, m10, m5, m2, m1, m05, total_efectivo_fisico, id_reporte_generado))
                
                cursor.execute("""
                    UPDATE arqueo_inventario 
                    SET refresco_inicio=%s, refresco_surtido=%s, refresco_final=%s, happycombo_total=%s, happycombo_vendidos_corte=%s, happycombo_vendidos_despues=%s 
                    WHERE id_reporte=%s
                """, (refresco_inicio, refresco_surtido, refresco_final, combo_total, combo_vendidos_corte, combo_vendidos_despues, id_reporte_generado))
                
                cursor.execute("DELETE FROM gastos_autorizados WHERE id_reporte = %s", (id_reporte_generado,))
                for g in st.session_state.lista_gastos:
                    cursor.execute("INSERT INTO gastos_autorizados (id_reporte, concepto, monto) VALUES (%s, %s, %s)", (id_reporte_generado, g['concepto'], g['monto']))
                    
                cursor.execute("SELECT id_reporte FROM control_cocina_encargados WHERE id_reporte = %s", (id_reporte_generado,))
                if cursor.fetchone():
                    cursor.execute("UPDATE control_cocina_encargados SET cocineros=%s WHERE id_reporte=%s", (cocineros, id_reporte_generado))
                else:
                    cursor.execute("INSERT INTO control_cocina_encargados (id_reporte, cocineros) VALUES (%s, %s)", (id_reporte_generado, cocineros))
                
                conn.commit()
                st.success("📝 ¡Reporte existente actualizado con éxito!")
                st.balloons()
            else:
                cursor.execute("""
                    INSERT INTO reportes_caja (id_sucursal, fecha, fondo_inicial, fondo_siguiente_dia, ventas_tarjetas, ventas_apps, ventas_efectivo_sistema) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (id_sucursal, fecha_reporte, fondo_inicial, fondo_siguiente, ventas_tarjetas, ventas_apps, ventas_efectivo_sistema))
                id_reporte_generado = cursor.lastrowid
                
                cursor.execute("""
                    INSERT INTO desglose_efectivo (id_reporte, b500, b200, b100, b50, b20, m10, m5, m2, m1, m05, total_efectivo_fisico) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (id_reporte_generado, b500, b200, b100, b50, b20, m10, m5, m2, m1, m05, total_efectivo_fisico))
                
                cursor.execute("""
                    INSERT INTO arqueo_inventario (id_reporte, refresco_inicio, refresco_surtido, refresco_final, happycombo_total, happycombo_vendidos_corte, happycombo_vendidos_despues) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (id_reporte_generado, refresco_inicio, refresco_surtido, refresco_final, combo_total, combo_vendidos_corte, combo_vendidos_despues))
                
                for g in st.session_state.lista_gastos:
                    cursor.execute("INSERT INTO gastos_autorizados (id_reporte, concepto, monto) VALUES (%s, %s, %s)", (id_reporte_generado, g['concepto'], g['monto']))
                    
                cursor.execute("INSERT INTO control_cocina_encargados (id_reporte, cocineros) VALUES (%s, %s)", (id_reporte_generado, cocineros))
                
                conn.commit()
                st.success("💾 ¡Nuevo reporte de turno guardado con éxito!")
                st.balloons()

            cursor.close()
            conn.close()
            time.sleep(1.2)
            st.rerun()
        except Exception as e:
            st.error(f"Error crítico al guardar en la base de datos: {e}")


