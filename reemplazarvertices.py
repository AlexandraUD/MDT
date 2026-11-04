import arcpy
import os

# === ENTRADAS ===
puntos_path = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\OP\puntosf1.shp"
poli_path = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\OP\poli2.shp"
carpeta_salida = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\OP"
salida_path = os.path.join(carpeta_salida, "poliact.shp")

# === PASO 1: CARGAR PUNTOS ===
puntos_dict = {}
with arcpy.da.SearchCursor(puntos_path, ["SHAPE@"]) as cursor:
    for row in cursor:
        punto = row[0]
        x = round(punto.firstPoint.X, 6)
        y = round(punto.firstPoint.Y, 6)
        z = punto.firstPoint.Z
        xy_key = (x, y)
        puntos_dict[xy_key] = z

print("Puntos cargados: " + str(len(puntos_dict)))

# === PASO 2: COPIAR Y ACTUALIZAR ===
if arcpy.Exists(salida_path):
    arcpy.Delete_management(salida_path)

arcpy.CopyFeatures_management(poli_path, salida_path)

# === PASO 3: ACTUALIZAR Z ===
spatial_ref = arcpy.Describe(poli_path).spatialReference
vertices_actualizados = 0

with arcpy.da.UpdateCursor(salida_path, ["SHAPE@"]) as cursor:
    for row in cursor:
        geom = row[0]
        nuevas_partes = arcpy.Array()
        
        for parte in geom:
            nueva_parte = arcpy.Array()
            for punto in parte:
                xy_key = (round(punto.X, 6), round(punto.Y, 6))
                
                if xy_key in puntos_dict:
                    z_nuevo = puntos_dict[xy_key]
                    nueva_parte.add(arcpy.Point(punto.X, punto.Y, z_nuevo))
                    vertices_actualizados += 1
                else:
                    nueva_parte.add(arcpy.Point(punto.X, punto.Y, punto.Z))
            
            nuevas_partes.add(nueva_parte)
        
        nueva_geom = arcpy.Polyline(nuevas_partes, spatial_ref, True, True)
        row[0] = nueva_geom
        cursor.updateRow(row)

print("Vertices actualizados: " + str(vertices_actualizados))
print("Guardado: " + salida_path)