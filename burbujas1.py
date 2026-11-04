import arcpy
from collections import defaultdict
import sys

# ============================================================
# CONFIGURACION
# ============================================================
arcpy.env.outputZFlag = "Enabled"

# Entradas

capaA = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\PRO\2_SHAPES_EDICION\curva_nivel2.shp"

capaB = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\PRO\2_SHAPES_EDICION\polylinea2.shp"

espacio_trabajo = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\OP\\"

spatial_ref = arcpy.Describe(capaA).spatialReference

print("=" * 70)
print("SCRIPT: Seleccionar polilineas que tocan 2+ curvas de nivel")
print("=" * 70)

# ============================================================
# PASO 1: Crear puntos de intersección
# ============================================================
print("\n[1/5] Creando puntos de intersección...")
intersecciones = espacio_trabajo + "intersecciones.shp"

# Eliminar si existe
if arcpy.Exists(intersecciones):
    arcpy.Delete_management(intersecciones)

arcpy.analysis.Intersect([capaA, capaB], intersecciones, output_type="POINT")
total_intersecciones = int(arcpy.GetCount_management(intersecciones)[0])
print(f"      ✓ {total_intersecciones} puntos de intersección encontrados")

# ============================================================
# PASO 2: Interpolar altura Z desde capaA
# ============================================================
print("\n[2/5] Interpolando valores Z desde curvas de nivel...")
puntos_con_z = []
contador = 0

with arcpy.da.SearchCursor(intersecciones, ["SHAPE@XY"]) as cursor_pts:
    for row in cursor_pts:
        contador += 1
        if contador % max(1, total_intersecciones // 10) == 0:
            print(f"      Procesados {contador}/{total_intersecciones} puntos...")
        
        x, y = row[0]
        punto = arcpy.Point(x, y)
        
        for row_linea in arcpy.da.SearchCursor(capaA, ["SHAPE@"]):
            linea = row_linea[0]
            try:
                distancia = linea.queryPointAndDistance(arcpy.PointGeometry(punto, spatial_ref))[1]
                if distancia is not None:
                    m = linea.measureOnLine(punto)
                    if m is not None:
                        punto3d = linea.positionAlongLine(m, use_percentage=False).centroid
                        puntos_con_z.append((x, y, punto3d.Z))
                        break
            except:
                continue

print(f"      ✓ {len(puntos_con_z)} puntos con Z interpolado")

# ============================================================
# PASO 3: Convertir a singlepart
# ============================================================
print("\n[3/5] Convirtiendo a singlepart...")
puntos_salida = espacio_trabajo + "puntos_generados.shp"

if arcpy.Exists(puntos_salida):
    arcpy.Delete_management(puntos_salida)

arcpy.management.MultipartToSinglepart(intersecciones, puntos_salida)
print(f"      ✓ Puntos en singlepart creados")

# ============================================================
# PASO 4: Insertar vértices Z
# ============================================================
print("\n[4/5] Insertando vértices en polilineas...")
capa_salida = espacio_trabajo + "Polilineas_editadas.shp"

if arcpy.Exists(capa_salida):
    arcpy.Delete_management(capa_salida)

arcpy.CopyFeatures_management(capaB, capa_salida)

z_por_fid = defaultdict(set)
vertices_insertados = 0
puntos_procesados = 0
total_puntos = len(puntos_con_z)

with arcpy.da.SearchCursor(puntos_salida, ["SHAPE@XY", "SHAPE@Z"]) as puntos:
    for (x, y), z in puntos:
        puntos_procesados += 1
        if puntos_procesados % max(1, total_puntos // 10) == 0:
            print(f"      Procesados {puntos_procesados}/{total_puntos} puntos...")
        
        punto_geom = arcpy.PointGeometry(arcpy.Point(x, y, z), spatial_ref)
        
        with arcpy.da.UpdateCursor(capa_salida, ["OID@", "SHAPE@"]) as lineas:
            for oid, linea in lineas:
                try:
                    # Verificar si el punto está cerca de la línea
                    if linea is None:
                        continue
                    
                    distancia = linea.distanceTo(punto_geom)
                    if distancia > 0.01:
                        continue
                    
                    nuevas_partes = []
                    insertado = False
                    
                    for parte in linea:
                        if len(parte) < 2:
                            continue
                        
                        nueva_parte = arcpy.Array()
                        
                        for i in range(len(parte) - 1):
                            p1, p2 = parte[i], parte[i + 1]
                            nueva_parte.add(p1)
                            
                            # Crear segmento y comparar distancia
                            try:
                                segmento = arcpy.Polyline(arcpy.Array([p1, p2]), linea.spatialReference, has_z=True)
                                seg_distancia = segmento.distanceTo(punto_geom)
                                
                                if seg_distancia < 0.01 and not insertado:
                                    nueva_parte.add(arcpy.Point(x, y, z))
                                    z_por_fid[oid].add(round(z, 2))
                                    insertado = True
                                    vertices_insertados += 1
                            except:
                                pass
                        
                        nueva_parte.add(parte[-1])
                        nuevas_partes.append(nueva_parte)
                    
                    if insertado:
                        nueva_linea = arcpy.Polyline(arcpy.Array(nuevas_partes), linea.spatialReference, has_z=True)
                        lineas.updateRow([oid, nueva_linea])
                        break
                
                except Exception as e:
                    continue

print(f"      ✓ {vertices_insertados} vértices insertados")

# ============================================================
# PASO 5: Filtrar polilineas con 2+ valores Z distintos
# ============================================================
print("\n[5/5] Filtrando polilineas con 2 o más Z diferentes...")

fids_validos = [fid for fid, zs in z_por_fid.items() if len(zs) >= 2]
print(f"      ✓ {len(fids_validos)} polilineas con 2+ Z diferentes encontradas")

if fids_validos:
    arcpy.MakeFeatureLayer_management(capa_salida, "filtradas_lyr")
    where = f"FID IN ({','.join(map(str, fids_validos))})"
    arcpy.SelectLayerByAttribute_management("filtradas_lyr", "NEW_SELECTION", where)
    capa_filtrada = espacio_trabajo + "polilineas_filtradas.shp"
    
    if arcpy.Exists(capa_filtrada):
        arcpy.Delete_management(capa_filtrada)
    
    arcpy.CopyFeatures_management("filtradas_lyr", capa_filtrada)
    arcpy.Delete_management("filtradas_lyr")
    
    print(f"\n      ✓ Exportadas {len(fids_validos)} polilineas a:")
    print(f"        {capa_filtrada}")
else:
    print("\n      ⚠️ No se encontraron polilineas con 2 o más Z diferentes.")

# ============================================================
# LIMPIEZA
# ============================================================
print("\n[LIMPIEZA] Eliminando temporales...")
arcpy.Delete_management(intersecciones)

# ============================================================
# RESUMEN FINAL
# ============================================================
print("\n" + "=" * 70)
print("✅ PROCESO COMPLETADO CORRECTAMENTE")
print("=" * 70)
print(f"Intersecciones encontradas: {total_intersecciones}")
print(f"Puntos con Z interpolado: {len(puntos_con_z)}")
print(f"Vertices insertados: {vertices_insertados}")
print(f"Polilineas con 2+ Z: {len(fids_validos)}")
print("=" * 70)
