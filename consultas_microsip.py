import firebird.driver as fdb
import pandas as pd

def obtener_ventas_cero_microsip(fecha, almacen):
    """
    1. MONITOREO DE COMBOS (Filtra por nombre de almacén de texto)
    """
    df = pd.DataFrame()
    try:
        connection = fdb.connect(
            database="26.140.142.179/3050:c:\\Microsip datos\\COCINA ADORADA.fdb",
            user="SYSDBA",
            password="12069624"
        )
        cursor = connection.cursor()
        
        # 📑 ¡AQUÍ PEGA TU SELECT REAL DE COMBOS DE MICROSIP!
        # Reemplaza este query de ejemplo por el SELECT exacto de combos que usabas antes
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
        
        cursor.execute(query_combos, (fecha, almacen))
        columnas = [desc[0] for desc in cursor.description]
        filas = cursor.fetchall()
        if filas:
            df = pd.DataFrame(filas, columns=columnas)
            
        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Error en combos: {e}")
    return df


def obtener_cobros_microsip(fecha_consulta, nombre_almacen):
    """
    2. AUDITORÍA DE COBROS (Corregido para usar nombre de almacén por texto)
    """
    df = pd.DataFrame()
    query_cobros = """
        SELECT 
            v.folio AS "Folio",
            v.fecha AS "Fecha",
            f.nombre AS "Forma_Cobro",
            c.importe AS "Importe",
            al.nombre AS "Almacen"
        FROM doctos_pv v
        INNER JOIN doctos_pv_cobros c ON (c.docto_pv_id = v.docto_pv_id)
        INNER JOIN formas_cobro f ON (f.forma_cobro_id = c.forma_cobro_id)
        INNER JOIN almacenes al ON (al.almacen_id = v.almacen_id)
        WHERE v.fecha = ?
          AND al.nombre = ?
          AND v.tipo_docto = 'V'
    """
    try:
        connection = fdb.connect(
            database="26.140.142.179/3050:c:\\Microsip datos\\COCINA ADORADA.fdb",
            user="SYSDBA",
            password="12069624"
        )
        cursor = connection.cursor()
        cursor.execute(query_cobros, (fecha_consulta, nombre_almacen))
        
        columnas = [desc[0] for desc in cursor.description]
        filas = cursor.fetchall()
        if filas:
            df = pd.DataFrame(filas, columns=columnas)
            
        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Error interno en query de cobros: {e}")
    return df