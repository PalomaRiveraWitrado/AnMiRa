import firebird.driver as fdb
import pandas as pd

def obtener_ventas_cero_microsip(fecha_buscar, nombre_almacen):
    """
    Trae los artículos con precio 0 (componentes de combos/mix de ventas)
    filtrados por fecha y por el almacén mapeado en MySQL.
    """
    # Formato de fecha requerido por Microsip
    fecha_str = fecha_buscar.strftime('%m/%d/%Y')
    
    try:
        # Conexión con el formato directo que ya nos funcionó
        connection = fdb.connect(
            database="26.140.142.179/3050:c:\\Microsip datos\\COCINA ADORADA.fdb",
            user="SYSDBA",
            password="12069624"
        )
        cursor = connection.cursor()
        
        # Tu consulta exacta optimizada con filtros dinámicos
        query = """
            SELECT 
                A.nombre AS ARTICULO, 
                SUM(D.unidades) AS UNIDADES
            FROM DOCTOS_PV V
            INNER JOIN DOCTOS_PV_DET D ON (V.docto_pv_id = D.docto_pv_id)
            INNER JOIN ARTICULOS A ON (D.articulo_id = A.articulo_id)
            INNER JOIN ALMACENES AL ON (AL.almacen_id = V.almacen_id)
            WHERE V.fecha = ?
            AND AL.nombre = ?
            AND V.tipo_docto = 'V'
            AND D.precio_unitario = 0
            GROUP BY A.nombre
        """
        
        cursor.execute(query, (fecha_str, nombre_almacen))
        columnas = [col[0] for col in cursor.description]
        datos = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return pd.DataFrame(datos, columns=columnas)
        
    except Exception as e:
        # Retorna un DataFrame vacío para que la app no se caiga si falla el servidor remoto
        print(f"⚠️ Error al consultar Microsip: {e}")
        return pd.DataFrame()