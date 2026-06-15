import firebird.driver as fdb
import pandas as pd

def obtener_ventas_cero_microsip(fecha_buscar, nombre_almacen_microsip):
    """
    Consulta Microsip y regresa los artículos a precio $0 agrupados y sumados
    para el reporte gerencial de auditoría de combos. (FUNCIONANDO AL 100%)
    """
    fecha_str = fecha_buscar.strftime('%m/%d/%Y')
    
    try:
        connection = fdb.connect(
            database="26.140.142.179/3050:c:\\Microsip datos\\COCINA ADORADA.fdb",
            user="SYSDBA",
            password="12069624"
        )
        cursor = connection.cursor()
        
        query = """
            SELECT 
                A.nombre AS ARTICULO,
                SUM(D.unidades) AS UNIDADES,
                L.nombre AS LINEA
            FROM DOCTOS_PV V
            INNER JOIN DOCTOS_PV_DET D ON (V.docto_pv_id = D.docto_pv_id)
            INNER JOIN ARTICULOS A ON (D.articulo_id = A.articulo_id)
            INNER JOIN LINEAS_ARTICULOS L ON (L.linea_articulo_id = A.linea_articulo_id)
            INNER JOIN ALMACENES AL ON (AL.almacen_id = V.almacen_id)
            WHERE V.fecha = ?
            AND AL.nombre = ?
            AND V.tipo_docto = 'V'
            AND D.precio_unitario = 0
            GROUP BY A.nombre, L.nombre
            ORDER BY SUM(D.unidades) DESC
        """
        
        cursor.execute(query, (fecha_str, nombre_almacen_microsip))
        columnas = [col[0] for col in cursor.description]
        datos = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return pd.DataFrame(datos, columns=columnas)

    except Exception as e:
        print(f"⚠️ Error Combos: {e}")
        return pd.DataFrame()


def obtener_cobros_microsip(fecha_buscar, nombre_almacen_microsip):
    """
    Consulta Microsip y regresa los cobros en vivo filtrados por el NOMBRE del almacén
    para evitar errores de IDs numéricos que no coinciden con MySQL.
    """
    fecha_str = fecha_buscar.strftime('%m/%d/%Y')
    df = pd.DataFrame()
    
    query_cobros = """
        SELECT 
            V.folio AS "Folio",
            V.fecha AS "Fecha",
            F.nombre AS "Forma_Cobro",
            C.importe AS "Importe",
            AL.nombre AS "Almacen"
        FROM DOCTOS_PV V
        INNER JOIN DOCTOS_PV_COBROS C ON (C.docto_pv_id = V.docto_pv_id)
        INNER JOIN FORMAS_COBRO F ON (F.forma_cobro_id = C.forma_cobro_id)
        INNER JOIN ALMACENES AL ON (AL.almacen_id = V.almacen_id)
        WHERE V.fecha = ?
          AND AL.nombre = ?
          AND V.tipo_docto = 'V'
          AND V.estatus = 'N'
    """
    try:
        connection = fdb.connect(
            database="26.140.142.179/3050:c:\\Microsip datos\\COCINA ADORADA.fdb",
            user="SYSDBA",
            password="12069624"
        )
        cursor = connection.cursor()
        cursor.execute(query_cobros, (fecha_str, nombre_almacen_microsip))
        
        columnas = [desc[0] for desc in cursor.description]
        filas = cursor.fetchall()
        
        if filas:
            df = pd.DataFrame(filas, columns=columnas)
            
        cursor.close()
        connection.close()
    except Exception as e:
        print(f"⚠️ Error crítico interno en query de cobros Microsip: {e}")
        
    return df