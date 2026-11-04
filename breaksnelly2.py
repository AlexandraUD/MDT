import arcpy
import os
import traceback

# === CONFIGURACIÓN DE ENTRADAS ===

polilinea = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\OP\paralelasrest_sin_buffer.shp"

breaks = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\OP\paralelasrest.shp" #Estas son las paralelas de abajo completas

carpeta_salida = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\OP\\"

# === CONFIGURACIÓN DE SALIDAS ===
centroides = os.path.join(carpeta_salida, "centroides_polilinea.shp")
interseccion = os.path.join(carpeta_salida, "interseccion_centroides_breaks.shp")
buffer_interseccion = os.path.join(carpeta_salida, "buffer_interseccion_50m.shp")
breaks_filtrado_temp = os.path.join(carpeta_salida, "breaks_filtrado_temp.shp")
breaks_filtrado_final = os.path.join(carpeta_salida, "breaks_filtrado_singlepart.shp")

# === CONFIGURACIÓN DEL ENTORNO ===
arcpy.env.overwriteOutput = True
arcpy.env.addOutputsToMap = False

try:
    print("=== 1️⃣ Calculando centroides de las polilíneas ===")
    arcpy.management.FeatureToPoint(polilinea, centroides, "INSIDE")
    count_cent = int(arcpy.management.GetCount(centroides)[0])
    if count_cent == 0:
        raise Exception("❌ No se generaron centroides a partir de la capa de polilíneas.")
    print(f"✅ {count_cent} centroides generados correctamente.")

    print("=== 2️⃣ Intersectando centroides con breaks ===")
    arcpy.analysis.Intersect([centroides, breaks], interseccion, "ALL", "", "POINT")
    count_int = int(arcpy.management.GetCount(interseccion)[0])
    if count_int == 0:
        raise Exception("❌ No se encontraron intersecciones entre centroides y breaks.")
    print(f"✅ {count_int} intersecciones generadas correctamente.")

    print("=== 3️⃣ Generando buffer de 0.5 metros alrededor de los puntos de intersección ===")
    arcpy.analysis.Buffer(interseccion, buffer_interseccion, "0.5 Meters", dissolve_option="ALL") 
    print("✅ Buffer generado correctamente.")

    print("=== 4️⃣ Recortando breaks dentro del buffer ===")
    arcpy.analysis.Clip(breaks, buffer_interseccion, breaks_filtrado_temp)
    count_filtrado = int(arcpy.management.GetCount(breaks_filtrado_temp)[0])
    print(f"✅ Capa temporal 'breaks_filtrado_temp' generada con {count_filtrado} entidades dentro del buffer.")

    print("=== 5️⃣ Convirtiendo capa final a entidades singlepart ===")
    arcpy.management.MultipartToSinglepart(breaks_filtrado_temp, breaks_filtrado_final)
    count_single = int(arcpy.management.GetCount(breaks_filtrado_final)[0])
    print(f"✅ Capa final 'breaks_filtrado_singlepart' creada con {count_single} entidades individuales.")

    # print("=== 6️⃣ Cargando capa final al mapa activo ===")
    # aprx = arcpy.mp.ArcGISProject("CURRENT")
    # mapa_activo = aprx.activeMap
    # mapa_activo.addDataFromPath(breaks_filtrado_final)
    # print("✅ Capa 'breaks_filtrado_singlepart' agregada correctamente al mapa.")

    print("=== ✅ Proceso completado exitosamente sin modificar la capa original de breaks ===")

except Exception as e:
    print("⚠️ Error durante la ejecución del script:")
    print(traceback.format_exc())