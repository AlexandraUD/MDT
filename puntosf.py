import arcpy
import os

# === ENTRADAS ===
shp_entrada = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\OP\puntos3dfinal.shp"
carpeta_salida = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\OP"
salida_final = os.path.join(carpeta_salida, "puntosf.shp")

def filtrar_puntos():
    try:
        arcpy.env.overwriteOutput = True
        
        # Copiar la capa de entrada
        if arcpy.Exists(salida_final):
            arcpy.Delete_management(salida_final)
        
        arcpy.CopyFeatures_management(shp_entrada, salida_final)
        
        # Lista de OIDs a eliminar
        oid_eliminar = []
        contador_conservar = 0
        contador_eliminar = 0
        
        # Leer puntos y evaluar condiciones
        with arcpy.da.SearchCursor(shp_entrada, ["OID@", "SHAPE@Z"]) as cursor:
            for row in cursor:
                oid, z = row
                
                if z is not None:
                    # Obtener parte decimal
                    parte_decimal = round(z % 1, 2)
                    
                    # Evaluar condiciones de eliminación
                    if parte_decimal == 0.0:
                        # Elevación entera
                        oid_eliminar.append(oid)
                        contador_eliminar += 1
                    elif parte_decimal < 0.15:
                        # Decimal < 0.15
                        oid_eliminar.append(oid)
                        contador_eliminar += 1
                    elif parte_decimal > 0.87:
                        # Decimal > 0.87
                        oid_eliminar.append(oid)
                        contador_eliminar += 1
                    else:
                        # Conservar
                        contador_conservar += 1
        
        print(f"Puntos a conservar: {contador_conservar}")
        print(f"Puntos a eliminar: {contador_eliminar}")
        
        # Eliminar puntos
        if oid_eliminar:
            with arcpy.da.UpdateCursor(salida_final, ["OID@"]) as cursor:
                for row in cursor:
                    if row[0] in oid_eliminar:
                        cursor.deleteRow()
        
        print(f"\n✅ Capa guardada: {salida_final}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    filtrar_puntos()