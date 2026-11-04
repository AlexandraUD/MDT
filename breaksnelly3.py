import arcpy
import os
import traceback

# === CONFIGURACIÓN DE ENTRADAS ===

breaks = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\OP\breaks_filtrado_singlepart.shp"

polilineas = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\PRO\2_SHAPES_EDICION\polylinea2.shp"

contornos = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\PRO\3_SALIDAS\RASTER_10\Contornos.shp"

# === CONFIGURACIÓN DE SALIDAS ===
salida_dir = os.path.dirname(breaks)
inter_poli = os.path.join(salida_dir, "interseccion_polilineas.shp")
buffer_poli = os.path.join(salida_dir, "buffer_intersecciones_polilineas.shp")
buffer_cont = os.path.join(salida_dir, "buffer_contornos.shp")
breaks_sin_polilineas = os.path.join(salida_dir, "breaks_sin_polilineas.shp")
breaks_sin_contornos = os.path.join(salida_dir, "breaks_sin_contornos.shp")
breaks_final = os.path.join(salida_dir, "breaks_final_singlepart.shp")
breaks_final_filtrado = os.path.join(salida_dir, "breaks_final_filtrado.shp")

# === CONFIGURACIÓN DE ENTORNO ===
arcpy.env.overwriteOutput = True

try:
    print("=== INICIANDO PROCESO DE CORTE DE BREAKS ===")

    # === 1. Intersección Breaks - Polilíneas ===
    print("→ Calculando intersecciones con polilíneas...")
    arcpy.analysis.Intersect([breaks, polilineas], inter_poli, "ALL", "", "POINT")

    # === 2. Generar Buffer de 0.5 m alrededor de intersecciones con polilíneas ===
    print("→ Generando buffer en intersecciones con polilíneas...")
    arcpy.analysis.Buffer(inter_poli, buffer_poli, "0.5 Meters", dissolve_option="ALL")#MODIFICAR AQUI EL TAMAÑO DEL BUFFER EN LAS INTERSECCIONES CON LAS POLILINEAS

    # === 3. Hacer Erase de los Breaks en zonas de intersección con polilíneas ===
    print("→ Aplicando Erase de los Breaks en zonas de cruce con polilíneas...")
    arcpy.analysis.Erase(breaks, buffer_poli, breaks_sin_polilineas)

    # === 4. Generar Buffer de 2 m alrededor de toda la capa de contornos ===
    print("→ Generando buffer alrededor de los contornos completos...")
    arcpy.analysis.Buffer(contornos, buffer_cont, "2 Meters", dissolve_option="ALL") #MODIFICAR AQUI EL TAMAÑO DEL BUFFER DE LOS CONTORNOS

    # === 5. Hacer Erase de los Breaks en zonas dentro del buffer de contornos ===
    print("→ Aplicando Erase de los Breaks en zonas cercanas a los contornos...")
    arcpy.analysis.Erase(breaks_sin_polilineas, buffer_cont, breaks_sin_contornos)

    # === 6. Convertir salida a SinglePart ===
    print("→ Convirtiendo a single part...")
    arcpy.management.MultipartToSinglepart(breaks_sin_contornos, breaks_final)

    # === 7. Filtrar por intersección con la capa Breaks original ===
    print("→ Filtrando por intersección con la capa original de Breaks...")
    arcpy.management.MakeFeatureLayer(breaks_final, "breaks_final_lyr")
    arcpy.management.MakeFeatureLayer(breaks, "breaks_in_lyr")

    arcpy.management.SelectLayerByLocation(
        "breaks_final_lyr",
        overlap_type="INTERSECT",
        select_features="breaks_in_lyr",
        selection_type="NEW_SELECTION"
    )

    arcpy.management.CopyFeatures("breaks_final_lyr", breaks_final_filtrado)

    # === 8. Agregar capa final al mapa activo ===
    # print("→ Agregando capa final al mapa de ArcGIS Pro...")
    # aprx = arcpy.mp.ArcGISProject("CURRENT")
    # m = aprx.activeMap
    # m.addDataFromPath(breaks_final_filtrado)

    print("✅ Proceso completado correctamente.")
    print(f"Capa resultante: {breaks_final_filtrado}")

except Exception as e:
    print("❌ Error durante el proceso:")
    print(traceback.format_exc())
