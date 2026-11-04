import arcpy
import os
from collections import defaultdict
import math

# ======================================================
# ENTRADAS
# ======================================================

ruta_curvas = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\PRO\2_SHAPES_EDICION\curva_nivel2.shp"

carpeta_salida = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\OP\\"

ruta_limite = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\LIMITE\LIMITE_BARRANCO_DE_LOBA_1K_13074000.shp"

distancia_paralela = 0.4

# ======================================================
# PARAMETROS DEL ALGORITMO
# ======================================================
num_puntos_muestreo = 8
distancia_rayo = 25 
tolerance_interseccion = 0.01

# ======================================================
# SALIDA
# ======================================================
salida_paralelas = os.path.join(carpeta_salida, "paralelas.shp")
salida_puntos_muestreo = os.path.join(carpeta_salida, "puntosm.shp")
salida_rayos = os.path.join(carpeta_salida, "proyec.shp")

# ======================================================
# CONFIGURACION
# ======================================================
arcpy.env.overwriteOutput = True
spatial_ref = arcpy.Describe(ruta_curvas).spatialReference

print("=" * 70)
print("CREAR PARALELAS")
print("=" * 70)

# ======================================================
# PASO 1: CARGAR CURVAS
# ======================================================
print("\n[1/5] Cargando curvas de nivel...")

curvas_por_elevacion = defaultdict(list)
todas_las_curvas = {}

with arcpy.da.SearchCursor(ruta_curvas, ["FID", "SHAPE@", "Elevation"]) as cursor:
    for fid, geom, elevation in cursor:
        if elevation is None:
            continue
        
        elev_int = int(elevation)
        curva_data = {
            'fid': fid,
            'geom': geom,
            'elevation': elevation,
            'centroid': geom.centroid,
            'extent': geom.extent
        }
        
        curvas_por_elevacion[elev_int].append(curva_data)
        todas_las_curvas[fid] = curva_data

elevaciones_unicas = sorted(curvas_por_elevacion.keys(), reverse=True)
print("Elevaciones encontradas: " + str(elevaciones_unicas[:10]) + "...")
print("Total curvas cargadas: " + str(len(todas_las_curvas)))

# ======================================================
# CARGAR LIMITE
# ======================================================
print("\nCargando geometría de límite...")

geometria_limite = None
with arcpy.da.SearchCursor(ruta_limite, ["SHAPE@"]) as cursor:
    for row in cursor:
        geometria_limite = row[0]
        break

if geometria_limite is None:
    print("ADVERTENCIA: No se pudo cargar la geometría de límite")
else:
    print("Límite cargado correctamente")

# ======================================================
# PASO 2: CREAR FEATURE CLASSES DE SALIDA
# ======================================================
print("\n[2/5] Creando feature classes...")

# Feature class de paralelas
if arcpy.Exists(salida_paralelas):
    arcpy.Delete_management(salida_paralelas)

arcpy.CreateFeatureclass_management(
    out_path=carpeta_salida,
    out_name="paralelas.shp",
    geometry_type="POLYLINE",
    spatial_reference=spatial_ref,
    has_z="ENABLED"
)

arcpy.AddField_management(salida_paralelas, "ELEVACI", "DOUBLE")
arcpy.AddField_management(salida_paralelas, "FID_OR", "LONG")
arcpy.AddField_management(salida_paralelas, "LADO", "TEXT")
arcpy.AddField_management(salida_paralelas, "ELEV_I", "DOUBLE")
arcpy.AddField_management(salida_paralelas, "ELEV_D", "DOUBLE")

# Feature class de puntos de muestreo
if arcpy.Exists(salida_puntos_muestreo):
    arcpy.Delete_management(salida_puntos_muestreo)

arcpy.CreateFeatureclass_management(
    out_path=carpeta_salida,
    out_name="puntosm.shp",
    geometry_type="POINT",
    spatial_reference=spatial_ref,
    has_z="ENABLED"
)

arcpy.AddField_management(salida_puntos_muestreo, "FID_CUR", "LONG")
arcpy.AddField_management(salida_puntos_muestreo, "ELEVACI", "DOUBLE")
arcpy.AddField_management(salida_puntos_muestreo, "NUM_M", "LONG")
arcpy.AddField_management(salida_puntos_muestreo, "DEC_I", "TEXT")
arcpy.AddField_management(salida_puntos_muestreo, "DEC_D", "TEXT")

# Feature class de rayos (para depuración, opcional)
if arcpy.Exists(salida_rayos):
    arcpy.Delete_management(salida_rayos)

arcpy.CreateFeatureclass_management(
    out_path=carpeta_salida,
    out_name="proyec.shp",
    geometry_type="POLYLINE",
    spatial_reference=spatial_ref
)

arcpy.AddField_management(salida_rayos, "FID_CUR", "LONG")
arcpy.AddField_management(salida_rayos, "NUM_M", "LONG")
arcpy.AddField_management(salida_rayos, "DIR", "TEXT")

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
# FUNCION: Obtener puntos de muestreo estratégico
# ======================================================
def obtener_puntos_muestreo(puntos, num_puntos):
    """Retorna exactamente num_puntos distribuidos uniformemente"""
    
    if len(puntos) < 2:
        return []
    
    if len(puntos) <= num_puntos:
        return puntos
    
    puntos_muestreo = []
    for i in range(num_puntos):
        idx = int(i * (len(puntos) - 1) / (num_puntos - 1))
        puntos_muestreo.append(puntos[idx])
    
    return puntos_muestreo

# ======================================================
# FUNCION: Calcular normal en punto de muestreo
# ======================================================
def calcular_normal_en_punto(puntos, punto_muestreo, radio=20):
    """
    Calcula la normal (perpendicular) en un punto usando
    la dirección general del tramo alrededor de ese punto
    """
    
    puntos_cercanos = []
    
    for p in puntos:
        dx = p[0] - punto_muestreo[0]
        dy = p[1] - punto_muestreo[1]
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist <= radio:
            puntos_cercanos.append(p)
    
    if len(puntos_cercanos) < 2:
        puntos_cercanos = sorted(
            puntos,
            key=lambda p: (p[0] - punto_muestreo[0])**2 + (p[1] - punto_muestreo[1])**2
        )[:3]
    
    if len(puntos_cercanos) < 2:
        return None
    
    # Calcular vector tangente promediado
    vx_total = 0.0
    vy_total = 0.0
    
    for i in range(len(puntos_cercanos) - 1):
        p1 = puntos_cercanos[i]
        p2 = puntos_cercanos[i + 1]
        vx = p2[0] - p1[0]
        vy = p2[1] - p1[1]
        
        magnitud = math.sqrt(vx*vx + vy*vy)
        if magnitud > 1e-10:
            vx_total += vx / magnitud
            vy_total += vy / magnitud
    
    magnitud = math.sqrt(vx_total*vx_total + vy_total*vy_total)
    if magnitud < 1e-10:
        return None
    
    vx_total /= magnitud
    vy_total /= magnitud
    
    # Normales (perpendiculares)
    normal_izq = (-vy_total, vx_total)
    normal_der = (vy_total, -vx_total)
    
    return (normal_izq, normal_der)

# ======================================================
# FUNCION: Crear rayo y buscar intersecciones
# ======================================================
def crear_rayo_y_buscar(punto_muestreo, normal, distancia_rayo, spatial_ref):
    """
    Crea una línea de rayo de 40m en dirección normal.
    Retorna la geometría de la línea del rayo.
    """
    
    rayo_x = normal[0]
    rayo_y = normal[1]
    
    mag = math.sqrt(rayo_x*rayo_x + rayo_y*rayo_y)
    if mag < 1e-10:
        return None
    
    rayo_x /= mag
    rayo_y /= mag
    
    # Punto final del rayo
    x_final = punto_muestreo[0] + rayo_x * distancia_rayo
    y_final = punto_muestreo[1] + rayo_y * distancia_rayo
    z_muestreo = punto_muestreo[2]
    
    # Crear polyline del rayo
    array_rayo = arcpy.Array()
    array_rayo.add(arcpy.Point(punto_muestreo[0], punto_muestreo[1], z_muestreo))
    array_rayo.add(arcpy.Point(x_final, y_final, z_muestreo))
    
    rayo_geom = arcpy.Polyline(array_rayo, spatial_ref, has_z=False)
    
    return rayo_geom

# ======================================================
# FUNCION: Encontrar vértice más cercano en curva tocada
# ======================================================
def encontrar_vertice_cercano(punto_origen, geom_curva_tocada):
    """
    Busca el vértice más cercano de la curva tocada al punto de origen.
    Retorna (distancia, punto_más_cercano)
    """
    
    puntos_curva = extraer_puntos(geom_curva_tocada)
    
    min_dist = float('inf')
    punto_cercano = None
    
    for p in puntos_curva:
        dx = p[0] - punto_origen[0]
        dy = p[1] - punto_origen[1]
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist < min_dist:
            min_dist = dist
            punto_cercano = p
    
    return (min_dist, punto_cercano)

# ======================================================
# FUNCION: Crear offset paralelo
# ======================================================
def crear_offset_paralelo(geom, distancia_offset, lado="derecha"):
    """
    Crea una paralela a una línea desplazada.
    lado: "izquierda" o "derecha"
    """
    try:
        puntos_originales = extraer_puntos(geom)
        
        if len(puntos_originales) < 2:
            return None
        
        puntos_offset = []
        
        for i in range(len(puntos_originales)):
            punto_actual = puntos_originales[i]
            
            # Calcular vector tangente
            if i == 0:
                p_siguiente = puntos_originales[i + 1]
                vx = p_siguiente[0] - punto_actual[0]
                vy = p_siguiente[1] - punto_actual[1]
            elif i == len(puntos_originales) - 1:
                p_anterior = puntos_originales[i - 1]
                vx = punto_actual[0] - p_anterior[0]
                vy = punto_actual[1] - p_anterior[1]
            else:
                p_anterior = puntos_originales[i - 1]
                p_siguiente = puntos_originales[i + 1]
                vx1 = punto_actual[0] - p_anterior[0]
                vy1 = punto_actual[1] - p_anterior[1]
                vx2 = p_siguiente[0] - punto_actual[0]
                vy2 = p_siguiente[1] - punto_actual[1]
                vx = (vx1 + vx2) / 2.0
                vy = (vy1 + vy2) / 2.0
            
            # Normalizar
            magnitud = math.sqrt(vx**2 + vy**2)
            if magnitud > 0:
                vx = vx / magnitud
                vy = vy / magnitud
            else:
                vx = 1.0
                vy = 0.0
            
            # Perpendicular
            if lado.lower() == "izquierda":
                perp_x = vy
                perp_y = -vx
            else:  # derecha
                perp_x = -vy
                perp_y = vx
            
            # Aplicar offset
            x_offset = punto_actual[0] + perp_x * distancia_offset
            y_offset = punto_actual[1] + perp_y * distancia_offset
            z_offset = punto_actual[2]
            
            puntos_offset.append((x_offset, y_offset, z_offset))
        
        # Crear polyline
        array_puntos = arcpy.Array()
        for p in puntos_offset:
            array_puntos.add(arcpy.Point(p[0], p[1], p[2]))
        
        polyline_offset = arcpy.Polyline(array_puntos, spatial_ref, has_z=True)
        return polyline_offset
        
    except Exception as e:
        print("Error en crear_offset_paralelo: " + str(e))
        return None

# ======================================================
# PASO 3: PROCESAR CADA CURVA
# ======================================================
print("\n[3/5] Procesando curvas y evaluando direcciones...")

# Crear capa temporal para las curvas (para SelectLayerByLocation)
arcpy.MakeFeatureLayer_management(ruta_curvas, "curvas_layer")

curvas_procesadas = 0
curvas_sin_decision = 0
paralelas_creadas = 0

icur_muestreo = arcpy.da.InsertCursor(salida_puntos_muestreo, 
                                       ["SHAPE@", "FID_CUR", "ELEVACI", "NUM_M", 
                                        "DEC_I", "DEC_D"])
icur_rayos = arcpy.da.InsertCursor(salida_rayos, 
                                    ["SHAPE@", "FID_CUR", "NUM_M", "DIR"])
icur_paralelas = arcpy.da.InsertCursor(salida_paralelas, 
                                        ["SHAPE@", "ELEVACI", "FID_OR", "LADO", 
                                         "ELEV_I", "ELEV_D"])

for fid_actual, curva_actual in todas_las_curvas.items():
    
    geom_actual = curva_actual['geom']
    elev_actual = curva_actual['elevation']
    puntos_actual = extraer_puntos(geom_actual)
    
    if len(puntos_actual) < 2:
        continue
    
    # Obtener 3 puntos de muestreo
    puntos_muestreo = obtener_puntos_muestreo(puntos_actual, num_puntos_muestreo)
    
    if len(puntos_muestreo) == 0:
        continue
    
    # Decisiones por lado (izquierda/derecha)
    decision_lado_izq = None  # "baja" o "sube"
    decision_lado_der = None
    
    elev_vecina_izq = None
    elev_vecina_der = None
    
    # Procesar cada punto de muestreo
    for idx_m, punto_m in enumerate(puntos_muestreo):
        
        # Verificar que está dentro del límite
        punto_geom = arcpy.Point(punto_m[0], punto_m[1], punto_m[2])
        
        if geometria_limite and not punto_geom.within(geometria_limite):
            continue
        
        # Insertar punto de muestreo
        icur_muestreo.insertRow([punto_geom, fid_actual, elev_actual, idx_m + 1, "", ""])
        
        # Calcular normales
        normales = calcular_normal_en_punto(puntos_actual, punto_m, radio=20)
        
        if not normales:
            continue
        
        normal_izq, normal_der = normales
        
        # ============ RAYCAST IZQUIERDA ============
        rayo_izq = crear_rayo_y_buscar(punto_m, normal_izq, distancia_rayo, spatial_ref)
        
        if rayo_izq:
            icur_rayos.insertRow([rayo_izq, fid_actual, idx_m + 1, "IZQ"])
            
            # SelectLayerByLocation: encontrar curvas que cruza el rayo
            arcpy.SelectLayerByLocation_management(
                "curvas_layer",
                "INTERSECT",
                rayo_izq,
                search_distance="",
                selection_type="NEW_SELECTION"
            )
            
            # Procesar las curvas seleccionadas
            with arcpy.da.SearchCursor("curvas_layer", ["FID", "SHAPE@", "Elevation"]) as cursor:
                for fid_tocada, geom_tocada, elev_tocada in cursor:
                    
                    if fid_tocada == fid_actual:
                        continue  # Ignorar self-intersection
                    
                    # Encontrar vértice más cercano
                    dist_cercano, punto_cercano = encontrar_vertice_cercano(punto_m, geom_tocada)
                    
                    if punto_cercano:
                        elev_tocada_int = int(elev_tocada)
                        elev_actual_int = int(elev_actual)
                        
                        if elev_tocada_int < elev_actual_int:
                            decision_lado_izq = "baja"
                            elev_vecina_izq = elev_tocada
                        else:
                            decision_lado_izq = "sube"
                            elev_vecina_izq = elev_tocada
                        
                        break  # Solo toma la primera (más cercana)
        
        # ============ RAYCAST DERECHA ============
        rayo_der = crear_rayo_y_buscar(punto_m, normal_der, distancia_rayo, spatial_ref)
        
        if rayo_der:
            icur_rayos.insertRow([rayo_der, fid_actual, idx_m + 1, "DER"])
            
            # SelectLayerByLocation: encontrar curvas que cruza el rayo
            arcpy.SelectLayerByLocation_management(
                "curvas_layer",
                "INTERSECT",
                rayo_der,
                search_distance="",
                selection_type="NEW_SELECTION"
            )
            
            # Procesar las curvas seleccionadas
            with arcpy.da.SearchCursor("curvas_layer", ["FID", "SHAPE@", "Elevation"]) as cursor:
                for fid_tocada, geom_tocada, elev_tocada in cursor:
                    
                    if fid_tocada == fid_actual:
                        continue  # Ignorar self-intersection
                    
                    # Encontrar vértice más cercano
                    dist_cercano, punto_cercano = encontrar_vertice_cercano(punto_m, geom_tocada)
                    
                    if punto_cercano:
                        elev_tocada_int = int(elev_tocada)
                        elev_actual_int = int(elev_actual)
                        
                        if elev_tocada_int < elev_actual_int:
                            decision_lado_der = "baja"
                            elev_vecina_der = elev_tocada
                        else:
                            decision_lado_der = "sube"
                            elev_vecina_der = elev_tocada
                        
                        break  # Solo toma la primera (más cercana)
    
    # ============ DECIDIR LADO FINAL ============
    # Comparar las decisiones de los 3 puntos de muestreo
    
    if decision_lado_izq is None and decision_lado_der is None:
        curvas_sin_decision += 1
        continue
    
    if decision_lado_izq == "baja" or decision_lado_der == "baja":
        # Si al menos un lado baja, la paralela va hacia donde baja
        if decision_lado_izq == "baja" and decision_lado_der != "baja":
            lado_final = "derecha"
        elif decision_lado_der == "baja" and decision_lado_izq != "baja":
            lado_final = "izquierda"
        else:
            # Ambos bajan: no hacer nada
            curvas_sin_decision += 1
            continue
    else:
        # Ambos suben: no hacer nada
        curvas_sin_decision += 1
        continue
    
    # ============ CREAR PARALELA ============
    try:
        polyline_paralela = crear_offset_paralelo(geom_actual, distancia_paralela, lado_final)
        
        if polyline_paralela is not None:
            icur_paralelas.insertRow([
                polyline_paralela, 
                elev_actual, 
                fid_actual, 
                lado_final,
                elev_vecina_izq if elev_vecina_izq else -9999,
                elev_vecina_der if elev_vecina_der else -9999
            ])
            paralelas_creadas += 1
    
    except Exception as e:
        if curvas_procesadas <= 10:
            print("  Advertencia en FID " + str(fid_actual) + ": " + str(e))
    
    curvas_procesadas += 1
    
    if curvas_procesadas % 100 == 0:
        print("  Procesadas " + str(curvas_procesadas) + " curvas...")

del icur_muestreo
del icur_rayos
del icur_paralelas

print("Curvas procesadas: " + str(curvas_procesadas))
print("Curvas sin decisión clara: " + str(curvas_sin_decision))
print("Paralelas creadas: " + str(paralelas_creadas))

# ======================================================
# PASO 5: RESUMEN FINAL
# ======================================================
print("\n[5/5] Proceso completado.")

total_curvas = len(todas_las_curvas)
print("\n" + "=" * 70)
print("RESUMEN FINAL")
print("=" * 70)
print("Total curvas en entrada: " + str(total_curvas))
print("Curvas procesadas: " + str(curvas_procesadas))
print("Paralelas creadas: " + str(paralelas_creadas))
print("Curvas sin decisión: " + str(curvas_sin_decision))
print("\nParametros usados:")
print("  Puntos de muestreo por curva: " + str(num_puntos_muestreo))
print("  Distancia de proyección (raycast): " + str(distancia_rayo) + " m")
print("  Distancia de offset paralela: " + str(distancia_paralela) + " m")
print("\nArchivos generados:")
print("  Paralelas: " + salida_paralelas)
print("  Puntos de muestreo: " + salida_puntos_muestreo)
print("  Rayos de proyección (depuración): " + salida_rayos)
print("=" * 70)

print("\nScript finalizado exitosamente.")