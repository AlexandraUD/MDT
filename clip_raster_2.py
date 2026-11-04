import arcpy
import os
from arcpy.sa import Con, IsNull

print("=" * 70)
print("SCRIPT: Borrar lo DENTRO del Polígono - Mantener Extensión Original")
print("=" * 70)

# ============================================================
# CONFIGURACIÓN
# ============================================================

raster_entrada = r"C:\argenis\LiDAR\17050_ARANZAZU\1_OP\tif\cortado.tif"

capa_vector = r"C:\argenis\LiDAR\17050_ARANZAZU\Afectaciones\Afectaciones_Aranzazu.shp"

output_folder = r"C:\argenis\LiDAR\17050_ARANZAZU\1_OP\tif"

output_filename = "rasterafectac.tif"

output_raster = os.path.join(output_folder, output_filename)

# ============================================================
# PASO 1: VERIFICAR ENTRADAS
# ============================================================
print("\n[1/4] Verificando capas...")

if not arcpy.Exists(raster_entrada):
    print(f"❌ ERROR: No se encontró raster")
    exit(1)

if not arcpy.Exists(capa_vector):
    print(f"❌ ERROR: No se encontró vector")
    exit(1)

print(f"      ✓ Raster encontrado")
print(f"      ✓ Polígono encontrado")

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# ============================================================
# PASO 2: ACTIVAR SPATIAL ANALYST
# ============================================================
print("\n[2/4] Activando herramientas...")

try:
    arcpy.CheckOutExtension("Spatial")
    print(f"      ✓ Spatial Analyst activado")
except:
    print(f"❌ ERROR: Spatial Analyst no disponible")
    exit(1)

# ============================================================
# PASO 3: CREAR MÁSCARA Y BORRAR ZONA DEL POLÍGONO
# ============================================================
print("\n[3/4] Borrando zona DENTRO del polígono...")

try:
    import tempfile
    
    # Obtener resolución del raster original
    raster_original = arcpy.Raster(raster_entrada)
    cell_size = raster_original.meanCellWidth
    
    print(f"      ✓ Resolución: {cell_size}")
    print(f"      ✓ Extensión original: {raster_original.extent}")
    
    # IMPORTANTE: Establecer extensión de análisis a la del raster original
    arcpy.env.extent = raster_original.extent
    arcpy.env.snapRaster = raster_entrada
    
    # Crear raster temporal del polígono
    temp_raster_vector = os.path.join(tempfile.gettempdir(), "temp_poligono_raster.tif")
    
    # Usar FID que está disponible
    arcpy.PolygonToRaster_conversion(
        in_features=capa_vector,
        value_field="FID",
        out_rasterdataset=temp_raster_vector,
        cell_assignment="CELL_CENTER",
        priority_field="NONE",
        cellsize=cell_size
    )
    
    print(f"      ✓ Polígono convertido a raster")
    
    raster_poligono = arcpy.Raster(temp_raster_vector)
    
    # LÓGICA CORRECTA CON EXTENSIÓN MANTENIDA:
    # Con(IsNull(raster_poligono), raster_original, "")
    # - Si NO hay valor en raster_poligono (FUERA del polígono) → mantener raster_original
    # - Si hay valor (DENTRO del polígono) → "" (vacío/BORRAR)
    
    raster_con_hueco = Con(
        IsNull(raster_poligono),    # ¿NO hay valor (FUERA del polígono)?
        raster_original,            # Sí → Mantener original (AFUERA)
        ""                          # No → Poner vacío (BORRAR lo DENTRO)
    )
    
    print(f"      ✓ Máscara aplicada correctamente")
    
    # Guardar con propiedades del original
    if arcpy.Exists(output_raster):
        arcpy.Delete_management(output_raster)
    
    raster_con_hueco.save(output_raster)
    print(f"      ✓ Raster guardado")
    
    # Limpiar ambiente y temporales
    arcpy.env.extent = None
    arcpy.env.snapRaster = None
    
    if arcpy.Exists(temp_raster_vector):
        arcpy.Delete_management(temp_raster_vector)

except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    
    # Limpiar ambiente si hay error
    arcpy.env.extent = None
    arcpy.env.snapRaster = None
    exit(1)

# ============================================================
# PASO 4: RESUMEN
# ============================================================
print("\n[4/4] Completando...")

if arcpy.Exists(output_raster):
    raster_resultado = arcpy.Raster(output_raster)
    print("\n" + "=" * 70)
    print("✅ PROCESO COMPLETADO")
    print("=" * 70)
    
    print(f"\nResultado:")
    print(f"  Archivo: {output_filename}")
    print(f"  Ruta: {output_raster}")
    print(f"  Extensión: {raster_resultado.extent}")
    
    print(f"\nLógica aplicada:")
    print(f"  ✓ BORRA: Todo lo DENTRO del polígono (crea hueco)")
    print(f"  ✓ MANTIENE: Todo lo AFUERA del polígono idéntico")
    print(f"  ✓ EXTENSIÓN: COMPLETA Y ORIGINAL (no reducida)")
    
    print("\n" + "=" * 70)
else:
    print(f"❌ ERROR: El raster no se creó")
    exit(1)

# Liberar extensión
try:
    arcpy.CheckInExtension("Spatial")
except:
    pass
