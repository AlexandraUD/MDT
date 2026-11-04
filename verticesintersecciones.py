import arcpy
import os

def script_tool(carpeta):
    """
    Script que coloca vértices en las intersecciones de polilineas con curvas de nivel.
    Los vértices toman el valor Z de la curva de nivel.
    """
    
    # Construir rutas
    capaA = os.path.join(carpeta, "curva_nivel2.shp")
    capaB = os.path.join(carpeta, "polylinea2.shp")
    
    # Verificar que existan las capas
    if not arcpy.Exists(capaA):
        arcpy.AddError(f"No se encontró la capa: {capaA}")
        raise arcpy.ExecuteError
    
    if not arcpy.Exists(capaB):
        arcpy.AddError(f"No se encontró la capa: {capaB}")
        raise arcpy.ExecuteError
    
    # Habilitar output con Z
    arcpy.env.outputZFlag = "Enabled"
    
    # Obtener referencia espacial
    spatial_ref = arcpy.Describe(capaA).spatialReference
    
    # Crear intersecciones
    intersecciones = os.path.join(carpeta, "intersecciones.shp")
    arcpy.analysis.Intersect([capaA, capaB], intersecciones, output_type="POINT")
    
    # === Registro ===
    total_intersecciones = int(arcpy.GetCount_management(intersecciones)[0])
    vertices_insertados = 0
    polilineas_omitidas = 0
    puntos_con_z = []
    
    # Extraer puntos 3D de las intersecciones
    with arcpy.da.SearchCursor(intersecciones, ["SHAPE@XY"]) as cursor_pts:
        for row in cursor_pts:
            x, y = row[0]
            punto = arcpy.Point(x, y)
            for row_linea in arcpy.da.SearchCursor(capaA, ["SHAPE@"]):
                linea = row_linea[0]
                distancia = linea.queryPointAndDistance(arcpy.PointGeometry(punto, spatial_ref))[1]
                if distancia is not None:
                    m = linea.measureOnLine(punto)
                    if m is not None:
                        punto3d = linea.positionAlongLine(m, use_percentage=False).centroid
                        puntos_con_z.append(punto3d)
                        break
    
    # Crear shapefile de puntos de salida
    puntos_salida = os.path.join(carpeta, "puntos_generados.shp")
    arcpy.management.MultipartToSinglepart(intersecciones, puntos_salida)
    
    # Copiar capa original
    capa_salida = os.path.join(carpeta, "polylinea2_editada.shp")
    arcpy.CopyFeatures_management(capaB, capa_salida)
    
    # Insertar vértices en las polilineas
    with arcpy.da.SearchCursor(puntos_salida, ["SHAPE@XY", "SHAPE@Z"]) as puntos:
        for (x, y), z in puntos:
            punto_geom = arcpy.PointGeometry(arcpy.Point(x, y, z), spatial_ref)
            with arcpy.da.UpdateCursor(capa_salida, ["OID@", "SHAPE@"]) as lineas:
                for oid, linea in lineas:
                    try:
                        if linea is None or linea.pointCount < 2:
                            raise ValueError("Geometría vacía o con menos de 2 vértices.")
                        
                        if not linea.contains(punto_geom) and linea.distanceTo(punto_geom) > 0.01:
                            continue
                        
                        nuevas_partes = []
                        insertado = False
                        
                        for parte in linea:
                            if len(parte) < 2:
                                raise ValueError("Parte con menos de 2 vértices.")
                            
                            nueva_parte = arcpy.Array()
                            for i in range(len(parte) - 1):
                                p1, p2 = parte[i], parte[i + 1]
                                nueva_parte.add(p1)
                                
                                segmento = arcpy.Polyline(arcpy.Array([p1, p2]), linea.spatialReference, has_z=True)
                                if segmento.distanceTo(punto_geom) < 0.01 and not insertado:
                                    nueva_parte.add(arcpy.Point(x, y, z))
                                    insertado = True
                                    vertices_insertados += 1
                            
                            nueva_parte.add(parte[-1])
                            nuevas_partes.append(nueva_parte)
                        
                        nueva_geom = arcpy.Polyline(arcpy.Array(nuevas_partes), linea.spatialReference, has_z=True)
                        lineas.updateRow([oid, nueva_geom])
                        break  # solo insertar una vez por punto
                        
                    except Exception as e:
                        arcpy.AddWarning(f"Polilínea OID {oid} omitida: {e}")
                        polilineas_omitidas += 1
                        continue
    
    # === LIMPIEZA ===
    arcpy.management.Delete(intersecciones)
    arcpy.management.Delete(puntos_salida)
    
    # === REEMPLAZAR Capa original con editada ===
    for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg", ".sbx", ".sbn"]:
        orig = os.path.splitext(capaB)[0] + ext
        if arcpy.Exists(orig):
            arcpy.management.Delete(orig)
    
    for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg", ".sbx", ".sbn"]:
        edit = os.path.splitext(capa_salida)[0] + ext
        nuevo = os.path.splitext(capaB)[0] + ext
        if arcpy.Exists(edit):
            arcpy.Rename_management(edit, nuevo)
    
    # === LOG FINAL ===
    arcpy.AddMessage("Proceso completado.")
    arcpy.AddMessage(f"Intersecciones totales: {total_intersecciones}")
    arcpy.AddMessage(f"Vertices insertados: {vertices_insertados}")
    arcpy.AddMessage(f"Polilineas omitidas: {polilineas_omitidas}")


if __name__ == "__main__":
    # Para ejecutar desde Anaconda Prompt, proporciona la carpeta donde están los shapefiles
    # Ejemplo: python vertices_en_intersecciones.py C:\ruta\a\carpeta
    
    import sys
    
    if len(sys.argv) > 1:
        carpeta = sys.argv[1]
    else:
        # Si no se proporciona carpeta, usa esta por defecto:

        carpeta = r"C:\argenis\_MDT\ARAUCA_ARAUCA\30_Arauca_1K_(Arauca)\PRO\2_SHAPES_EDICION"
    
    print(f"Procesando carpeta: {carpeta}")
    script_tool(carpeta)
    print("Listo!")
