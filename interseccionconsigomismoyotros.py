import arcpy
import os

# === ENTRADAS ===

ruta_polilineas = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\PRO\2_SHAPES_EDICION\curva_nivel2.shp"

carpeta_salida = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\OP\\"

salida_intersect = os.path.join(carpeta_salida, "Intersecciones_Curvas.shp")

salida_final = os.path.join(carpeta_salida, "Intersecciones_Curvas_Unicas.shp")

def generar_intersecciones():
    try:
        arcpy.env.overwriteOutput = True
        if not os.path.exists(carpeta_salida):
            os.makedirs(carpeta_salida)

        # Temporal de intersección en la carpeta de salida
        intersect_temp = os.path.join(carpeta_salida, "temp_intersect.shp")

        # Paso 1: Intersectar la capa consigo misma
        if arcpy.Exists(intersect_temp):
            arcpy.Delete_management(intersect_temp)

        arcpy.Intersect_analysis(
            in_features=[ruta_polilineas, ruta_polilineas],
            out_feature_class=intersect_temp,
            join_attributes="ALL",
            cluster_tolerance="",
            output_type="POINT"
        )

        # Paso 2: Guardar el resultado base
        if arcpy.Exists(salida_intersect):
            arcpy.Delete_management(salida_intersect)

        arcpy.CopyFeatures_management(intersect_temp, salida_intersect)
        print(f"✅ Intersecciones generadas correctamente en: {salida_intersect}")

        # Paso 3: Eliminar duplicados (puntos en la misma coordenada)
        print("🔍 Eliminando puntos duplicados...")
        if arcpy.Exists(salida_final):
            arcpy.Delete_management(salida_final)
        arcpy.DeleteIdentical_management(salida_intersect, ["Shape"])
        arcpy.CopyFeatures_management(salida_intersect, salida_final)
        print(f"✅ Intersecciones únicas guardadas en: {salida_final}")

        # Paso 4: Eliminar el temporal
        arcpy.Delete_management(intersect_temp)

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    generar_intersecciones()