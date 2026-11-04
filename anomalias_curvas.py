import arcpy
import os
from collections import Counter

print("=" * 70)
print("SCRIPT: Detectar Anomalias en Curvas de Nivel")
print("=" * 70)

# === CONFIGURACIÓN DE ENTRADAS ===
curvas = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\OP\curvas_unidas.shp"

carpeta_salida = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\OP\\"

# Crear carpeta si no existe
if not os.path.exists(carpeta_salida):
    os.makedirs(carpeta_salida)
    print(f"\n📁 Carpeta creada: {carpeta_salida}")

# === DEFINIR SALIDAS ===
salida_polilineas = os.path.join(carpeta_salida, "curvas_anomalas.shp")
salida_puntos = os.path.join(carpeta_salida, "vertices_atipicos.shp")

# === ELIMINAR ARCHIVOS ANTERIORES SI EXISTEN ===
print("\n[1/4] Limpiando archivos anteriores...")
for shp in [salida_polilineas, salida_puntos]:
    if arcpy.Exists(shp):
        arcpy.Delete_management(shp)
        print(f"      ✓ Eliminado: {os.path.basename(shp)}")

# === CREAR SHAPEFILE DE PUNTOS (3D) ===
print("\n[2/4] Creando shapefiles de salida...")
spatial_ref = arcpy.Describe(curvas).spatialReference
arcpy.env.outputZFlag = "Enabled"

arcpy.CreateFeatureclass_management(
    carpeta_salida, "vertices_atipicos.shp", "POINT", 
    spatial_reference=spatial_ref, has_z="ENABLED"
)
arcpy.AddField_management(salida_puntos, "Z_ref", "DOUBLE")
arcpy.AddField_management(salida_puntos, "Z_real", "DOUBLE")
arcpy.AddField_management(salida_puntos, "ParentFID", "LONG")
print(f"      ✓ Shapefile de puntos creado")

# === CREAR SHAPEFILE DE POLILINEAS (3D) ===
arcpy.CreateFeatureclass_management(
    carpeta_salida, "curvas_anomalas.shp", "POLYLINE", 
    spatial_reference=spatial_ref, has_z="ENABLED"
)
arcpy.AddField_management(salida_polilineas, "Z_ref", "DOUBLE")
arcpy.AddField_management(salida_polilineas, "NumErr", "LONG")
print(f"      ✓ Shapefile de polilineas creado")

# === INSERT CURSORS DE SALIDA ===
icurve = arcpy.da.InsertCursor(salida_polilineas, ["SHAPE@", "Z_ref", "NumErr"])
ipoint = arcpy.da.InsertCursor(salida_puntos, ["SHAPE@", "Z_ref", "Z_real", "ParentFID"])

# === REVISAR GEOMETRÍAS ===
print("\n[3/4] Analizando curvas de nivel...")

total_curvas = int(arcpy.GetCount_management(curvas)[0])
curvas_con_anomalias = 0
vertices_atipicos_totales = 0

with arcpy.da.SearchCursor(curvas, ["OID@", "SHAPE@"]) as cursor:
    for idx, (oid, shape) in enumerate(cursor, 1):
        # Mostrar progreso cada 10%
        if idx % max(1, total_curvas // 10) == 0:
            print(f"      Procesadas {idx}/{total_curvas} curvas...")
        
        if not shape:
            continue
        
        # === EXTRAER TODOS LOS Z DE LA POLILÍNEA ===
        z_values = []
        puntos_geom = []
        
        for part in shape:
            for pnt in part:
                if pnt and pnt.Z is not None:
                    z_values.append(round(pnt.Z, 3))
                    puntos_geom.append(pnt)
        
        if not z_values:
            continue
        
        # === CALCULAR Z MAYORITARIA COMO REFERENCIA ===
        z_ref = Counter(z_values).most_common(1)[0][0]
        
        # === DETECTAR ATÍPICOS ===
        anomalos = []
        for pnt, z in zip(puntos_geom, z_values):
            if z != z_ref:
                anomalos.append((pnt, z))
        
        # === SI HAY VÉRTICES ANÓMALOS -> EXPORTAR ===
        if anomalos:
            curvas_con_anomalias += 1
            vertices_atipicos_totales += len(anomalos)
            
            icurve.insertRow((shape, z_ref, len(anomalos)))
            
            for pnt, zreal in anomalos:
                punto3D = arcpy.Point(pnt.X, pnt.Y, pnt.Z)
                point_geom = arcpy.PointGeometry(punto3D, spatial_ref, has_z=True)
                ipoint.insertRow((point_geom, z_ref, zreal, oid))

# === CERRAR CURSORES ===
del icurve, ipoint

# === RESUMEN FINAL ===
print("\n[4/4] Generando reporte...")

print("\n" + "=" * 70)
print("✅ PROCESO COMPLETADO")
print("=" * 70)
print(f"\nCurvas de nivel analizadas: {total_curvas}")
print(f"Curvas con anomalias: {curvas_con_anomalias}")
print(f"Vertices atípicos encontrados: {vertices_atipicos_totales}")

if curvas_con_anomalias > 0:
    print(f"\n⚠️ SE ENCONTRARON ERRORES:")
    print(f"   - {curvas_con_anomalias} curvas tienen vértices con Z inconsistentes")
    print(f"   - {vertices_atipicos_totales} vértices tienen valores Z fuera del rango")
else:
    print(f"\n✓ No se encontraron anomalias")

print(f"\nArchivos de salida:")
print(f"  → Curvas anomalas: {salida_polilineas}")
print(f"  → Vertices atípicos: {salida_puntos}")

print(f"\nAbrir en ArcGIS Pro:")
print(f"  1. Carga curvas_anomalas.shp (muestra las curvas con errores)")
print(f"  2. Carga vertices_atipicos.shp (muestra los vértices problemáticos)")
print(f"  3. Cada punto muestra:")
print(f"     - Z_ref: El valor de Z correcto (mayoritario)")
print(f"     - Z_real: El valor incorrecto que tiene")
print(f"     - ParentFID: ID de la curva que contiene el error")

print("\n" + "=" * 70)
