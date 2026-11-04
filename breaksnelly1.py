import arcpy
import os

def script_tool(contornos, breaklines, carpeta_salida):
    arcpy.env.overwriteOutput = True

    # Validaciones
    if not arcpy.Exists(contornos):
        raise Exception("❌ La capa de contornos no existe.")
    if not arcpy.Exists(breaklines):
        raise Exception("❌ La capa de breaklines no existe.")
    if not os.path.isdir(carpeta_salida):
        raise Exception(f"❌ La carpeta de salida no existe: {carpeta_salida}")

    # Rutas
    nombre_base = os.path.splitext(os.path.basename(breaklines))[0]
    nombre_salida = f"{nombre_base}_sin_buffer.shp"
    breaklines_salida = os.path.join(carpeta_salida, nombre_salida)
    buffer_temp = os.path.join(carpeta_salida, "tmp_buffer_contornos.shp")

    # 1. Buffer alrededor de contornos
    arcpy.Buffer_analysis(contornos, buffer_temp, "0.6 Meters", dissolve_option="ALL")
    arcpy.AddMessage("✅ Buffer generado.")

    # 2. Erase
    arcpy.Erase_analysis(breaklines, buffer_temp, breaklines_salida)
    arcpy.AddMessage(f"✅ Breaklines modificadas. Salida: {breaklines_salida}")

    # 3. Eliminar buffer
    arcpy.Delete_management(buffer_temp)
    arcpy.AddMessage("✅ Buffer temporal eliminado.")

    # 4. Crear capa temporal
    arcpy.MakeFeatureLayer_management(breaklines_salida, "Breaklines_finales")
    arcpy.AddMessage("✅ Capa 'Breaklines_finales' creada.")

# ==================================================
# 🔁 EJECUCIÓN DUAL: GUI o NOTEBOOK
# ==================================================
if __name__ == "__main__":

    if arcpy.GetArgumentCount() > 0:
        # ▶ EJECUCIÓN DESDE SCRIPT TOOL (INTERFAZ)
        contornos = arcpy.GetParameterAsText(0)
        breaklines = arcpy.GetParameterAsText(1)
        carpeta_salida = arcpy.GetParameterAsText(2)

    else:
        # ▶ EJECUCIÓN DESDE NOTEBOOK / CÓDIGO

        contornos = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\PRO\3_SALIDAS\RASTER_46\Contornos.shp"

        breaklines = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\OP\paralelasrest.shp"

        carpeta_salida = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\OP\\"

    script_tool(contornos, breaklines, carpeta_salida)
