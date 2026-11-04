import arcpy
import os

# === ENTRADAS ===
shp1 = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\OP\puntos3d_corregidos.shp"
shp2 = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\OP\poli2_Puntos.shp"
carpeta_salida = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\OP"
salida_final = os.path.join(carpeta_salida, "puntos3dfinal.shp")

def comparar_alturas():
    try:
        arcpy.env.overwriteOutput = True
        
        # Leer alturas de poli2_Puntos (referencia)
        alturas_ref = {}
        with arcpy.da.SearchCursor(shp2, ["SHAPE@XY", "SHAPE@Z"]) as cursor:
            for row in cursor:
                x, y = row[0]
                z = row[1]
                if z is not None:
                    alturas_ref[(x, y)] = int(z)  # Valor entero
        
        print(f"Puntos de referencia cargados: {len(alturas_ref)}")
        
        # Comparar con puntos3d_corregidos e identificar puntos a eliminar
        oid_borrar = []
        puntos_conservar = 0
        
        with arcpy.da.SearchCursor(shp1, ["OID@", "SHAPE@XY", "SHAPE@Z"]) as cursor:
            for row in cursor:
                oid, (x, y), z = row
                if z is not None:
                    z_entero = int(z)
                    
                    # Buscar si existe punto en la misma posición X,Y en shp2
                    if (x, y) in alturas_ref:
                        z_ref_entero = alturas_ref[(x, y)]
                        
                        # Si los valores enteros son IGUALES, marcar para borrar
                        if z_entero == z_ref_entero:
                            oid_borrar.append(oid)
                        else:
                            # Si son DIFERENTES, conservar
                            puntos_conservar += 1
                            print(f"  Conservado: ({x:.2f}, {y:.2f}) | Z={z:.2f} (ref={z_ref_entero})")
                    else:
                        # Si no existe en shp2, conservar el punto
                        puntos_conservar += 1
        
        print(f"\nPuntos a conservar: {puntos_conservar}")
        print(f"Puntos a eliminar: {len(oid_borrar)}")
        
        # Crear shapefile de salida con copia de puntos3d_corregidos
        if arcpy.Exists(salida_final):
            arcpy.Delete_management(salida_final)
        
        arcpy.CopyFeatures_management(shp1, salida_final)
        
        # Eliminar los puntos que tienen valores enteros iguales
        if oid_borrar:
            with arcpy.da.UpdateCursor(salida_final, ["OID@"]) as cursor:
                for row in cursor:
                    oid = row[0]
                    if oid in oid_borrar:
                        cursor.deleteRow()
            print(f"✅ Puntos eliminados (valores enteros iguales): {len(oid_borrar)}")
        
        print(f"\n✅ Capa final guardada en: {salida_final}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    comparar_alturas()