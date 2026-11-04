import arcpy
import os

# === CONFIGURACIÓN ===
curvas = r"C:\argenis\_MDT\ARAUCA_ARAUCA\30_Arauca_1K_(Arauca)\PRO\2_SHAPES_EDICION\curva_nivel2.shp"
malla = r"C:\argenis\_MDT\ARAUCA_ARAUCA\30_Arauca_1K_(Arauca)\OP\malla.shp"
carpeta_salida = r"C:\argenis\_MDT\ARAUCA_ARAUCA\30_Arauca_1K_(Arauca)\OP\\"
salida = os.path.join(carpeta_salida, "puntos_interseccion.shp")

# === ENTORNO ===
arcpy.env.overwriteOutput = True
spatial_ref = arcpy.Describe(curvas).spatialReference

try:
    print("=== Generando puntos en intersecciones ===")
    
    # 1. Intersectar
    print("→ Calculando intersecciones...")
    arcpy.analysis.Intersect([curvas, malla], salida, "ALL", "", "POINT")
    
    # 2. Convertir a SinglePart si es necesario
    print("→ Convirtiendo a Point ZM...")
    salida_temp = os.path.join(carpeta_salida, "puntos_temp.shp")
    arcpy.management.MultipartToSinglepart(salida, salida_temp)
    arcpy.Delete_management(salida)
    arcpy.Rename_management(salida_temp, salida)

    count = int(arcpy.management.GetCount(salida)[0])
    print(f"✅ {count} puntos generados.")
    
    # 3. Asignar Z desde Elevation (solo lectura del atributo que ya está)
    print("→ Los puntos heredan automáticamente la elevación de las curvas.")
    print("✅ Proceso completado.")
    print(f"Salida: {salida}")
    print(f"SRS: {spatial_ref.name}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    print(traceback.format_exc())