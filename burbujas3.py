import arcpy
import os

print("=" * 70)
print("SCRIPT: Actualizar Polilineas con Puntos Modificados (Burbujas3)")
print("=" * 70)

# === CONFIGURACIÓN DE ENTRADAS ===

puntos_modificados = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\OP\puntos_modificados.shp"

polilineas_original = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\PRO\2_SHAPES_EDICION\polylinea2.shp"

salida_actualizada = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\OP\polylinea2_actualizada.shp"


tolerancia = 0.01  # distancia máxima para considerar coincidencia (metros)

# === PASO 1: VERIFICAR ARCHIVOS DE ENTRADA ===
print("\n[1/4] Verificando archivos de entrada...")

if not arcpy.Exists(puntos_modificados):
    print(f"❌ ERROR: No se encontró {puntos_modificados}")
    exit(1)

if not arcpy.Exists(polilineas_original):
    print(f"❌ ERROR: No se encontró {polilineas_original}")
    exit(1)

print(f"      ✓ Puntos modificados encontrados")
print(f"      ✓ Polilineas originales encontradas")

# === PASO 2: COPIAR CAPA ORIGINAL PARA EDITAR ===
print("\n[2/4] Copiando capa original para editar...")

if arcpy.Exists(salida_actualizada):
    arcpy.Delete_management(salida_actualizada)

arcpy.CopyFeatures_management(polilineas_original, salida_actualizada)
print(f"      ✓ Copia creada")

# === PASO 3: CARGAR PUNTOS MODIFICADOS ===
print("\n[3/4] Cargando puntos modificados...")

puntos = []
try:
    with arcpy.da.SearchCursor(puntos_modificados, ["SHAPE@XY", "SHAPE@Z"]) as cursor:
        for (x, y), z in cursor:
            puntos.append((x, y, z))
except Exception as e:
    print(f"❌ ERROR al leer puntos: {str(e)}")
    exit(1)

if not puntos:
    print(f"      ⚠️ No se encontraron puntos modificados")
    print(f"      El archivo de salida será igual al original")
else:
    print(f"      ✓ {len(puntos)} puntos modificados cargados")

# === PASO 4: ACTUALIZAR POLILÍNEAS ===
print("\n[4/4] Actualizando polilineas con puntos modificados...")

arcpy.env.outputZFlag = "Enabled"
spatial_ref = arcpy.Describe(salida_actualizada).spatialReference

polilineas_actualizadas = 0
vertices_actualizados = 0
total_polilineas = int(arcpy.GetCount_management(salida_actualizada)[0])

try:
    with arcpy.da.UpdateCursor(salida_actualizada, ["OID@", "SHAPE@"]) as cursor:
        for oid, shape in cursor:
            polilineas_actualizadas += 1
            
            # Mostrar progreso cada 10%
            if polilineas_actualizadas % max(1, total_polilineas // 10) == 0:
                print(f"      Procesadas {polilineas_actualizadas}/{total_polilineas} polilineas...")
            
            try:
                nuevas_partes = []
                
                for parte in shape:
                    nueva_parte = arcpy.Array()
                    
                    for vertice in parte:
                        punto_actualizado = None
                        
                        # Buscar si hay un punto modificado cerca de este vértice
                        for x, y, z in puntos:
                            dx = vertice.X - x
                            dy = vertice.Y - y
                            distancia = (dx**2 + dy**2)**0.5
                            
                            if distancia <= tolerancia:
                                punto_actualizado = arcpy.Point(x, y, z)
                                vertices_actualizados += 1
                                break
                        
                        # Usar el punto actualizado si lo encontró, sino usar el original
                        if punto_actualizado:
                            nueva_parte.add(punto_actualizado)
                        else:
                            nueva_parte.add(vertice)
                    
                    nuevas_partes.append(nueva_parte)
                
                # Crear la nueva geometría y actualizar
                nueva_geom = arcpy.Polyline(arcpy.Array(nuevas_partes), shape.spatialReference, has_z=True)
                cursor.updateRow([oid, nueva_geom])
            
            except Exception as e:
                print(f"      ⚠️ Error procesando polilínea OID {oid}: {str(e)}")
                continue

except Exception as e:
    print(f"❌ ERROR al actualizar polilineas: {str(e)}")
    exit(1)

# === RESUMEN FINAL ===
print("\n" + "=" * 70)
print("✅ PROCESO FINALIZADO CORRECTAMENTE")
print("=" * 70)
print(f"\nPolilineas procesadas: {polilineas_actualizadas}")
print(f"Vertices actualizados: {vertices_actualizados}")
print(f"Puntos aplicados: {len(puntos)}")
print(f"\nArchivo de salida:")
print(f"  → {salida_actualizada}")
print("\n" + "=" * 70)
