import arcpy
import os
import math

# ======================================================
# ENTRADAS
# ======================================================

ruta_paralelas = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\OP\paralelas.shp"

carpeta_salida = r"C:\argenis\_MDT\SARDINATA_NSAN\31_Sardinata_1K_(Norte_de_Santader)\OP\\"

# ======================================================
# CONFIGURACION
# ======================================================
arcpy.env.overwriteOutput = True
spatial_ref = arcpy.Describe(ruta_paralelas).spatialReference

print("=" * 70)
print("DETECTAR MUST NOT SELF INTERSECT")
print("=" * 70)

# ======================================================
# FUNCION: Extraer puntos de geometría
# ======================================================
def extraer_puntos(geom):
    """Extrae todos los puntos de una polyline"""
    puntos = []
    
    for i in range(geom.partCount):
        parte = geom.getPart(i)
        for punto in parte:
            if punto:
                x = punto.X
                y = punto.Y
                z = punto.Z if hasattr(punto, 'Z') and punto.Z is not None else 0.0
                puntos.append((x, y, z))
    
    return puntos

# ======================================================
# FUNCION: Calcular intersección entre dos segmentos 2D
# ======================================================
def interseccion_segmentos(p1, p2, p3, p4):
    """
    Calcula si dos segmentos se intersectan y retorna el punto de intersección.
    Segmento 1: p1 -> p2
    Segmento 2: p3 -> p4
    
    Retorna (True, punto_intersección) o (False, None)
    """
    
    x1, y1 = p1[0], p1[1]
    x2, y2 = p2[0], p2[1]
    x3, y3 = p3[0], p3[1]
    x4, y4 = p4[0], p4[1]
    
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    
    # Segmentos paralelos
    if abs(denom) < 1e-10:
        return (False, None)
    
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
    
    # Verificar si la intersección está dentro de ambos segmentos
    if 0 < t < 1 and 0 < u < 1:
        # Calcular punto de intersección
        x_inter = x1 + t * (x2 - x1)
        y_inter = y1 + t * (y2 - y1)
        z_inter = p1[2]  # Usar Z del primer punto
        
        return (True, (x_inter, y_inter, z_inter))
    
    return (False, None)

# ======================================================
# CREAR FEATURE CLASS DE SALIDA
# ======================================================
print("\nCreando feature class de puntos de self intersect...")

salida_puntos_intersect = os.path.join(carpeta_salida, "puntos_self_intersect.shp")

if arcpy.Exists(salida_puntos_intersect):
    arcpy.Delete_management(salida_puntos_intersect)

arcpy.CreateFeatureclass_management(
    out_path=carpeta_salida,
    out_name="puntos_self_intersect.shp",
    geometry_type="POINT",
    spatial_reference=spatial_ref,
    has_z="ENABLED"
)

arcpy.AddField_management(salida_puntos_intersect, "FID_PAR", "LONG")
arcpy.AddField_management(salida_puntos_intersect, "Elevation", "DOUBLE")

# ======================================================
# LEER PARALELAS Y DETECTAR SELF INTERSECT
# ======================================================
print("\nLeyendo paralelas y detectando self intersections...")

icur_intersect = arcpy.da.InsertCursor(salida_puntos_intersect, 
                                        ["SHAPE@", "FID_PAR", "Elevation"])

paralelas_totales = 0
paralelas_con_intersect = 0
puntos_intersect_totales = 0

with arcpy.da.SearchCursor(ruta_paralelas, ["OID@", "SHAPE@", "Elevation"]) as cursor:
    for oid, geom_paralela, Elevationon in cursor:
        
        paralelas_totales += 1
        
        try:
            # Extraer puntos de la paralela
            puntos = extraer_puntos(geom_paralela)
            
            if len(puntos) < 4:  # Necesita al menos 4 puntos para que haya self intersect
                continue
            
            # Crear segmentos
            segmentos = []
            for i in range(len(puntos) - 1):
                segmentos.append((i, puntos[i], puntos[i + 1]))
            
            # Detectar intersecciones entre segmentos no adyacentes
            intersecciones_encontradas = []
            
            for i in range(len(segmentos)):
                for j in range(i + 2, len(segmentos)):  # i+2 para saltarse adyacentes
                    seg1_idx, seg1_p1, seg1_p2 = segmentos[i]
                    seg2_idx, seg2_p1, seg2_p2 = segmentos[j]
                    
                    # Calcular intersección
                    hay_intersect, punto_intersect = interseccion_segmentos(seg1_p1, seg1_p2, 
                                                                             seg2_p1, seg2_p2)
                    
                    if hay_intersect:
                        intersecciones_encontradas.append(punto_intersect)
            
            # Si se encontraron intersecciones, guardar los puntos
            if len(intersecciones_encontradas) > 0:
                paralelas_con_intersect += 1
                
                # Insertar puntos de intersección para esta paralela
                for punto_inter in intersecciones_encontradas:
                    punto_geom = arcpy.Point(punto_inter[0], punto_inter[1], punto_inter[2])
                    icur_intersect.insertRow([punto_geom, oid, Elevationon])
                    puntos_intersect_totales += 1
        
        except Exception as e:
            print("  Error procesando paralela OID " + str(oid) + ": " + str(e))
            continue
        
        if paralelas_totales % 100 == 0:
            print("  Procesadas " + str(paralelas_totales) + " paralelas...")

del icur_intersect

# ======================================================
# RESUMEN FINAL
# ======================================================
print("\n" + "=" * 70)
print("RESUMEN FINAL")
print("=" * 70)
print("Total paralelas verificadas: " + str(paralelas_totales))
print("Paralelas con SELF INTERSECT: " + str(paralelas_con_intersect))
print("Puntos de intersección encontrados: " + str(puntos_intersect_totales))
print("\nArchivo generado:")
print("  " + salida_puntos_intersect)
print("=" * 70)

print("\nVerificación completada.")