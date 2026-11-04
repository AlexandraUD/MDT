import arcpy
import os

# === ENTRADA ===

ruta_polilineas = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\OP\poli2.shp"

# === SALIDA ===

carpeta_salida = os.path.dirname(ruta_polilineas)

nombre_salida = os.path.splitext(os.path.basename(ruta_polilineas))[0] + "_Puntos.shp"

ruta_salida = os.path.join(carpeta_salida, nombre_salida)


nombre_outliers = os.path.splitext(os.path.basename(ruta_polilineas))[0] + "_Outliers.shp"
ruta_outliers = os.path.join(carpeta_salida, nombre_outliers)

# === ELIMINAR SI EXISTE ===
if arcpy.Exists(ruta_salida):
    arcpy.Delete_management(ruta_salida)
if arcpy.Exists(ruta_outliers):
    arcpy.Delete_management(ruta_outliers)

# === CREAR FEATURE CLASS ===
spatial_ref = arcpy.Describe(ruta_polilineas).spatialReference
arcpy.CreateFeatureclass_management(
    out_path=carpeta_salida,
    out_name=os.path.basename(nombre_salida),
    geometry_type="POINT",
    spatial_reference=spatial_ref,
    has_z="ENABLED"
)

arcpy.CreateFeatureclass_management(
    out_path=carpeta_salida,
    out_name=os.path.basename(nombre_outliers),
    geometry_type="POINT",
    spatial_reference=spatial_ref,
    has_z="ENABLED"
)

# === COPIAR TODOS LOS CAMPOS ===
for campo in arcpy.ListFields(ruta_polilineas):
    if campo.type not in ('OID', 'Geometry'):
        arcpy.AddField_management(ruta_salida, campo.name, campo.type, field_length=campo.length)
        arcpy.AddField_management(ruta_outliers, campo.name, campo.type, field_length=campo.length)

arcpy.AddField_management(ruta_outliers, "Z_Valor", "DOUBLE")
arcpy.AddField_management(ruta_outliers, "X_Coord", "DOUBLE")
arcpy.AddField_management(ruta_outliers, "Y_Coord", "DOUBLE")

# === CAMPOS PARA LECTURA Y ESCRITURA ===
campos_entrada = ["SHAPE@"] + [f.name for f in arcpy.ListFields(ruta_polilineas) if f.type not in ('OID', 'Geometry')]
campos_salida = ["SHAPE@"] + [f.name for f in arcpy.ListFields(ruta_polilineas) if f.type not in ('OID', 'Geometry')]
campos_outliers = campos_salida + ["Z_Valor", "X_Coord", "Y_Coord"]

# === EXTRAER VÉRTICES CON VALIDACIÓN ===
puntos_validos = 0
puntos_outliers = 0

with arcpy.da.SearchCursor(ruta_polilineas, campos_entrada) as scur, \
     arcpy.da.InsertCursor(ruta_salida, campos_salida) as icur, \
     arcpy.da.InsertCursor(ruta_outliers, campos_outliers) as icur_out:
    
    for row in scur:
        geom = row[0]
        atributos = row[1:]
        
        if geom is None:
            continue
        
        for part in geom:
            for pnt in part:
                if pnt:
                    z_val = pnt.Z if pnt.Z is not None else 0
                    
                    if 0 <= z_val <= 500:
                        punto_geom = arcpy.Point(pnt.X, pnt.Y, z_val)
                        icur.insertRow([punto_geom] + list(atributos))
                        puntos_validos += 1
                    else:
                        punto_geom = arcpy.Point(pnt.X, pnt.Y, z_val)
                        icur_out.insertRow([punto_geom] + list(atributos) + [z_val, pnt.X, pnt.Y])
                        puntos_outliers += 1

print(f"✅ Puntos válidos (0-500): {puntos_validos}")
print(f"   Guardados en: {ruta_salida}")
print(f"\n⚠️ Puntos outliers: {puntos_outliers}")
print(f"   Guardados en: {ruta_outliers}")