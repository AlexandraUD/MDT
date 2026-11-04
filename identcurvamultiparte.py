import arcpy
import os

# === ENTRADAS ===

ruta_polilineas = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\PRO\2_SHAPES_EDICION\curva_nivel2.shp"

carpeta_salida = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\OP\\"

# === SALIDA ===
salida_puntos = os.path.join(carpeta_salida, "Multiparte_Separaciones.shp")

try:
    arcpy.env.overwriteOutput = True

    # Crear feature class de salida
    sr = arcpy.Describe(ruta_polilineas).spatialReference
    arcpy.CreateFeatureclass_management(
        out_path=os.path.dirname(salida_puntos),
        out_name=os.path.basename(salida_puntos),
        geometry_type="POINT",
        spatial_reference=sr,
        has_z="ENABLED"
    )

    # Agregar campos
    arcpy.AddField_management(salida_puntos, "ID_LINEA", "LONG")
    arcpy.AddField_management(salida_puntos, "NUM_PARTE", "SHORT")

    # Revisar cada polilínea
    with arcpy.da.SearchCursor(ruta_polilineas, ["OID@", "SHAPE@"]) as cursor_in, \
         arcpy.da.InsertCursor(salida_puntos, ["SHAPE@", "ID_LINEA", "NUM_PARTE"]) as cursor_out:
        for oid, geom in cursor_in:
            if geom.partCount <= 1:
                continue  # No es multiparte

            for i, part in enumerate(geom):
                if len(part) == 0:
                    continue
                # Obtener primer punto de la parte
                punto = arcpy.PointGeometry(part[0], sr)
                cursor_out.insertRow((punto, oid, i + 1))

    print("✅ Proceso completado correctamente. Separaciones de multipartes guardadas en:", salida_puntos)

except Exception as e:
    print("❌ Error durante el proceso:", e)
