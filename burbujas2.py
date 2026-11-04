import arcpy
import os
import math

print("=" * 70)
print("SCRIPT: Interpolacion Lineal de Z (Burbujas2)")
print("=" * 70)

# === CONFIGURACIÓN ===

curvas = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\PRO\2_SHAPES_EDICION\curva_nivel2.shp"

polilineas = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\OP\polilineas_filtradas.shp"

salida = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\OP\polilineas_corregidas.shp"

salida_puntos = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\OP\puntos_modificados.shp"

tolerancia = 0.01  # Tolerancia en metros para considerar intersección con curva

# === PASO 1: CACHE DE CURVAS DE NIVEL ===
print("\n[1/5] Cargando curvas de nivel...")
arcpy.env.outputZFlag = "Enabled"

curvas_geom = []
contador_curvas = 0

with arcpy.da.SearchCursor(curvas, ["SHAPE@"]) as cursor:
    for row in cursor:
        curvas_geom.append(row[0])
        contador_curvas += 1

print(f"      ✓ {contador_curvas} curvas de nivel cargadas en memoria")

# === PASO 2: COPIAR CAPA ORIGINAL A LA DE SALIDA ===
print("\n[2/5] Copiando capa de polilineas...")

if arcpy.Exists(salida):
    arcpy.Delete_management(salida)

arcpy.CopyFeatures_management(polilineas, salida)
total_polilineas = int(arcpy.GetCount_management(salida)[0])
print(f"      ✓ {total_polilineas} polilineas copiadas")

# === PASO 3: LISTA DE PUNTOS MODIFICADOS ===
print("\n[3/5] Procesando polilineas e interpolando Z...")

puntos_modificados = []
polilineas_procesadas = 0
vertices_interpolados = 0

# === PROCESAR POLILÍNEAS UNA A UNA ===
with arcpy.da.UpdateCursor(salida, ["OID@", "SHAPE@"]) as cursor:
    for oid, shape in cursor:
        polilineas_procesadas += 1
        
        # Mostrar progreso cada 10%
        if polilineas_procesadas % max(1, total_polilineas // 10) == 0:
            print(f"      Procesadas {polilineas_procesadas}/{total_polilineas} polilineas...")
        
        nuevas_partes = []
        
        try:
            for parte in shape:
                vertices = [arcpy.Point(v.X, v.Y, v.Z) for v in parte]
                puntos_validos = []
                
                # === IDENTIFICAR VÉRTICES CON Z ENTERA Y SOBRE CURVA ===
                for i, pt in enumerate(vertices):
                    try:
                        if pt.Z is None:
                            continue
                        
                        z_val = float(pt.Z)
                        
                        # Verificar si Z es entero
                        if not z_val == int(z_val):
                            continue
                        
                        punto_geom = arcpy.PointGeometry(pt, shape.spatialReference)
                        
                        # Verificar si está sobre una curva
                        for curva in curvas_geom:
                            distancia = curva.distanceTo(punto_geom)
                            if distancia <= tolerancia:
                                puntos_validos.append((i, pt))
                                break
                    except:
                        continue
                
                nuevos_vertices = list(vertices)
                
                # === INTERPOLAR ENTRE RANGOS VÁLIDOS ===
                if len(puntos_validos) >= 2:
                    for j in range(len(puntos_validos) - 1):
                        idx1, pt1 = puntos_validos[j]
                        idx2, pt2 = puntos_validos[j + 1]
                        z1, z2 = float(pt1.Z), float(pt2.Z)
                        
                        # Evitar división por 0
                        if abs(z2 - z1) < 0.01:
                            continue
                        
                        try:
                            # Obtener medidas sobre la línea
                            medida1 = shape.measureOnLine(pt1, True)
                            medida2 = shape.measureOnLine(pt2, True)
                            dist_total = abs(medida2 - medida1)
                            
                            if dist_total < 0.001:
                                continue
                            
                            # Interpolar cada vértice entre idx1 e idx2
                            for k in range(idx1 + 1, idx2):
                                p = vertices[k]
                                min_z, max_z = min(z1, z2), max(z1, z2)
                                
                                # Si Z es entera o está fuera del rango, se interpola
                                z_p = float(p.Z) if p.Z is not None else 0
                                
                                if z_p == int(z_p) or not (min_z <= z_p <= max_z):
                                    try:
                                        # Interpolación lineal usando distancias sobre la línea
                                        medida_actual = shape.measureOnLine(p, True)
                                        dist_actual = abs(medida_actual - medida1)
                                        
                                        t = dist_actual / dist_total if dist_total != 0 else 0.5
                                        nueva_z = z1 + t * (z2 - z1)
                                        
                                        nuevos_vertices[k] = arcpy.Point(p.X, p.Y, nueva_z)
                                        puntos_modificados.append(arcpy.Point(p.X, p.Y, nueva_z))
                                        vertices_interpolados += 1
                                    except:
                                        continue
                        except:
                            continue
                
                nuevas_partes.append(arcpy.Array(nuevos_vertices))
            
            # Actualizar la geometría
            nueva_geom = arcpy.Polyline(arcpy.Array(nuevas_partes), shape.spatialReference, has_z=True)
            cursor.updateRow([oid, nueva_geom])
        
        except Exception as e:
            print(f"      ⚠️ Error procesando polilínea OID {oid}: {str(e)}")
            continue

print(f"      ✓ {polilineas_procesadas} polilineas procesadas")
print(f"      ✓ {vertices_interpolados} vertices interpolados")

# === PASO 4: CREAR SHAPE DE PUNTOS MODIFICADOS ===
print("\n[4/5] Creando shapefile de puntos modificados...")

if puntos_modificados:
    sr = arcpy.Describe(salida).spatialReference
    
    # Eliminar si existe
    if arcpy.Exists(salida_puntos):
        arcpy.Delete_management(salida_puntos)
    
    # Crear feature class
    arcpy.CreateFeatureclass_management(
        os.path.dirname(salida_puntos),
        os.path.basename(salida_puntos),
        "POINT",
        spatial_reference=sr,
        has_z="ENABLED"
    )
    
    # Añadir campo para visualizar valor Z
    arcpy.AddField_management(salida_puntos, "Z", "DOUBLE")
    
    # Insertar puntos
    puntos_insertados = 0
    with arcpy.da.InsertCursor(salida_puntos, ["SHAPE@", "Z"]) as insert:
        for pt in puntos_modificados:
            try:
                geom = arcpy.PointGeometry(arcpy.Point(pt.X, pt.Y, pt.Z), sr, has_z=True)
                insert.insertRow([geom, pt.Z])
                puntos_insertados += 1
            except:
                continue
    
    print(f"      ✓ {puntos_insertados} puntos modificados exportados")
else:
    print(f"      ℹ️ No se modificaron vértices (sin interpolación necesaria)")

# === PASO 5: RESUMEN FINAL ===
print("\n[5/5] Limpieza y resumen...")

print("\n" + "=" * 70)
print("✅ PROCESO FINALIZADO CORRECTAMENTE")
print("=" * 70)
print(f"\nPolilineas procesadas: {polilineas_procesadas}")
print(f"Vertices interpolados: {vertices_interpolados}")
print(f"Puntos modificados: {len(puntos_modificados)}")
print(f"\nArchivos generados:")
print(f"  → Polilineas corregidas: {salida}")
if puntos_modificados:
    print(f"  → Puntos modificados: {salida_puntos}")
print("\n" + "=" * 70)
