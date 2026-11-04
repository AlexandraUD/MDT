import arcpy
import math
import os

# === ENTRADAS ===

puntos_3d = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\OP\poli2_Puntos.shp"  # Puntos 3D

tin_path  = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\T\3_SALIDAS\RASTER_8\TIN"                                # Dataset TIN

salida    = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\OP\puntos3d_corregidos.shp"            # Salida final

# === RUTA PARA TEMPORALES (misma carpeta que salida) ===
carpeta_salida = os.path.dirname(salida)
interp_out = os.path.join(carpeta_salida, "interp_points.shp")
tmp_salida = os.path.join(carpeta_salida, "tmp_corregidos.shp")

# Eliminar temporales previos si existen
for temp in [interp_out, tmp_salida, salida]:
    if arcpy.Exists(temp):
        arcpy.management.Delete(temp)

# 1) Interpolar todos los puntos sobre el TIN
arcpy.ddd.InterpolateShape(tin_path, puntos_3d, interp_out)

# 2) Copiar la salida como nueva capa editable
arcpy.management.CopyFeatures(interp_out, salida)

# 3) Asegurar campos para resultado
if "Z_CORR" not in [f.name for f in arcpy.ListFields(salida)]:
    arcpy.management.AddField(salida, "Z_CORR", "DOUBLE")
if "CORREGIDO" not in [f.name for f in arcpy.ListFields(salida)]:
    arcpy.management.AddField(salida, "CORREGIDO", "TEXT", field_length=2)

# 4) Crear diccionario con Elevation original
elevation_original = {}
with arcpy.da.SearchCursor(puntos_3d, ["OID@", "Elevation"]) as sc:
    for oid, elev in sc:
        elevation_original[oid] = elev

# 5) Comparar y corregir solo con Elevation
ids_corregidos = set()
with arcpy.da.UpdateCursor(
    salida, ["OID@", "SHAPE@XY", "SHAPE@Z", "Elevation", "Z_CORR", "CORREGIDO", "SHAPE@"]
) as cursor:
    for oid, (x, y), z_tin, elev_inicial, z_corr, corregido, shape in cursor:
        if elev_inicial is None:
            continue

        corregir = False
        z_final = elev_inicial  # Por defecto deja igual

        # Caso 1: Elevation era entero
        if float(elev_inicial).is_integer():
            z_final = z_tin
            corregir = True

        # Caso 2: Elevation era decimal
        else:
            entero_tin = int(math.floor(z_tin))
            if not (entero_tin <= elev_inicial < entero_tin + 1):
                z_final = z_tin
                corregir = True

        if corregir:
            ids_corregidos.add(oid)
            cursor.updateRow((oid, (x, y), z_final, elev_inicial, z_final, "SI", arcpy.Point(x, y, z_final)))
        else:
            cursor.updateRow((oid, (x, y), elev_inicial, elev_inicial, elev_inicial, "NO", arcpy.Point(x, y, elev_inicial)))

# 6) Filtrar para dejar solo los corregidos
arcpy.management.MakeFeatureLayer(salida, "tmp_layer", "CORREGIDO = 'SI'")
arcpy.management.CopyFeatures("tmp_layer", tmp_salida)

# Reemplazar salida con los corregidos
arcpy.management.Delete(salida)
arcpy.management.Rename(tmp_salida, salida)

print("✅ Puntos corregidos guardados en:", salida)
print(f"ℹ️ Total de puntos corregidos: {len(ids_corregidos)}")
print("⚠️ En la salida solo están los puntos que realmente fueron modificados.")


