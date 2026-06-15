import streamlit as st
from datetime import date
import pandas as pd

# Importamos las herramientas de tu archivo de Microsip original (Firebird central)
from consultas_microsip import obtener_ventas_cero_microsip

# Diccionario de mapeo exacto basado en tu tabla de MySQL (image_fc9081.png)
MAPEO_ALMACENES = {
    1: "ALMACEN ORIENTE",       # Arcoiris
    2: "ALMACEN CUATRO C...",   # 4 Caminos
    3: "ALMACEN TRIANA",        # Triana
    4: "ALMACEN ROSITA",        # Rosita
    5: "ALMACEN VINEDOS"        # Viñedos
}

def renderizar_tablero_combos_admin(id_sucursal_actual, nombre_sucursal_local):
    """
    Renderiza la sección exclusiva del Administrador para ver el 
    Mix de Ventas de Microsip al momento sin alterar el flujo de caja.
    """
    st.markdown(f"### 📊 Monitoreo de Combos Microsip - Sucursal {nombre_sucursal_local}")
    st.caption("Consulta en tiempo real al servidor central Firebird (Artículos a Precio $0)")
    
    # 1. Obtenemos el nombre del almacén correspondiente en Microsip
    nombre_almacen_microsip = MAPEO_ALMACENES.get(id_sucursal_actual)
    
    if not nombre_almacen_microsip:
        st.warning(f"⚠️ La sucursal '{nombre_sucursal_local}' (ID: {id_sucursal_actual}) no tiene un almacén mapeado.")
        return

    # 2. El administrador puede auditar el día de HOY por defecto, o cambiar la fecha
    col_fecha, col_btn = st.columns([3, 1])
    with col_fecha:
        fecha_auditoria = st.date_input("📅 Fecha de Consulta", date.today(), key="fecha_combos_microsip")
    
    with col_btn:
        st.write("") # Espacio estético
        sub_btn = st.button("🔄 Actualizar", use_container_width=True)

    # 3. Ejecutar la consulta remota
    with st.spinner("🔌 Extrayendo Mix de Ventas desde Microsip central..."):
        df_combos = obtener_ventas_cero_microsip(fecha_auditoria, nombre_almacen_microsip)
    
    # 4. Despliegue de la Información
    if not df_combos.empty:
        # Calculamos métricas rápidas para el corte ejecutivo del Admin
        total_articulos_desplazados = df_combos["UNIDADES"].sum()
        platillo_mas_vendido = df_combos.iloc[0]["ARTICULO"]
        cant_mas_vendido = df_combos.iloc[0]["UNIDADES"]
        
        # Tarjetas de KPI formativas
        metric_col1, metric_col2 = st.columns(2)
        with metric_col1:
            st.metric(label="🥡 Total Componentes Servidos (Cocina)", value=f"{int(total_articulos_desplazados)} pzas")
        with metric_col2:
            st.metric(label="🔥 Componente Más Solicitado", value=platillo_mas_vendido, delta=f"{int(cant_mas_vendido)} pzas")
        
        st.write("---")
        
        # Formateamos la tabla para que sea visualmente impecable
        df_visual = df_combos.copy()
        df_visual["UNIDADES"] = df_visual["UNIDADES"].astype(int) # Quitamos los decimales .00000 tontos de Firebird
        df_visual.columns = ["PRODUCTO (COMBO)", "CANTIDAD DISPARADA", "LÍNEA MICROSIP"]
        
        # Pintamos la tabla nativa de Streamlit expandida y estilizada
        st.dataframe(
            df_visual,
            use_container_width=True,
            hide_index=True
        )
        
    else:
        st.info(f"ℹ️ No se detectan componentes de combos vendidos a $0 el día {fecha_auditoria.strftime('%d/%m/%Y')} en {nombre_almacen_microsip}.")
