import arcpy
import os

print("=" * 70)
print("SCRIPT: Corregir Atributo Elevation en Curvas de Nivel")
print("=" * 70)

# ============================================================
# CONFIGURACIÓN - EDITA ESTAS RUTAS SEGÚN TUS DATOS
# ============================================================

# RUTA DE ENTRADA: Shapefile original (NO se modifica)
input_shp = r"C:\argenis\_MDT\PROVIDENCIA\11_Providencia_1K_(San_Andrés)\PROCESO2\2_SHAPES_EDICION\curva_nivel2.shp"

# CARPETA DE SALIDA: Donde se guardará el shapefile corregido
output_folder = r"C:\argenis\_MDT\PROVIDENCIA\11_Providencia_1K_(San_Andrés)\OP"

# Nombre del archivo de salida
output_filename = "curva_nivel2_elevation_corregida.shp"
output_shp = os.path.join(output_folder, output_filename)

# ============================================================
# PASO 1: VERIFICAR ENTRADA
# ============================================================
print("\n[1/4] Verificando shapefile de entrada...")

if not arcpy.Exists(input_shp):
    print(f"❌ ERROR: No se encontró {input_shp}")
    exit(1)

print(f"      ✓ Shapefile encontrado")

# Verificar que existe el campo 'Elevation'
campos = [f.name for f in arcpy.ListFields(input_shp)]
if 'Elevation' not in campos:
    print(f"❌ ERROR: El campo 'Elevation' no existe")
    print(f"   Campos disponibles: {campos}")
    exit(1)

print(f"      ✓ Campo 'Elevation' encontrado")

# ============================================================
# PASO 2: COPIAR SHAPEFILE
# ============================================================
print("\n[2/4] Copiando shapefile a carpeta de salida...")

# Crear carpeta si no existe
if not os.path.exists(output_folder):
    os.makedirs(output_folder)
    print(f"      ✓ Carpeta creada: {output_folder}")

# Eliminar si ya existe
if arcpy.Exists(output_shp):
    arcpy.Delete_management(output_shp)

# Copiar el shapefile
arcpy.CopyFeatures_management(input_shp, output_shp)
print(f"      ✓ Copia creada: {output_filename}")

# ============================================================
# PASO 3: CORREGIR VALORES DE ELEVATION
# ============================================================
print("\n[3/4] Corrigiendo valores de Elevation...")

total_registros = int(arcpy.GetCount_management(output_shp)[0])
registros_modificados = 0
valores_originales = []
valores_corregidos = []

with arcpy.da.UpdateCursor(output_shp, ["OID@", "Elevation"]) as cursor:
    for oid, elevation in cursor:
        # Mostrar progreso cada 10%
        if oid % max(1, total_registros // 10) == 0:
            print(f"      Procesados {oid}/{total_registros} registros...")
        
        if elevation is None:
            continue
        
        # Guardar valor original para reporte
        valor_original = elevation
        
        # REDONDEAR AL ENTERO MÁS CERCANO
        # - 17.0000000153 → 17
        # - 134.999999985 → 135
        # - 24.5 → 24 o 25 (redondeo estándar)
        valor_redondeado = round(elevation)
        
        # Si cambió, actualizar
        if valor_original != valor_redondeado:
            cursor.updateRow([oid, valor_redondeado])
            registros_modificados += 1
            valores_originales.append(valor_original)
            valores_corregidos.append(valor_redondeado)

print(f"      ✓ Procesados {total_registros} registros")

# ============================================================
# PASO 4: RESUMEN Y REPORTE
# ============================================================
print("\n[4/4] Generando reporte...")

print("\n" + "=" * 70)
print("✅ PROCESO COMPLETADO CORRECTAMENTE")
print("=" * 70)

print(f"\nShapefile de entrada (original - NO modificado):")
print(f"  {input_shp}")

print(f"\nShapefile de salida (con Elevation corregido):")
print(f"  {output_shp}")

print(f"\nEstadísticas:")
print(f"  Total de registros: {total_registros}")
print(f"  Registros modificados: {registros_modificados}")

if registros_modificados > 0:
    print(f"\nEjemplos de correcciones realizadas:")
    # Mostrar algunos ejemplos (máximo 10)
    for i in range(min(10, len(valores_originales))):
        print(f"  {valores_originales[i]:.10f} → {valores_corregidos[i]}")
    if len(valores_originales) > 10:
        print(f"  ... y {len(valores_originales) - 10} más")
else:
    print(f"\nℹ️ No se realizaron modificaciones (los valores ya eran correctos)")

print("\n" + "=" * 70)
print("NOTAS:")
print("=" * 70)
print("""
REGLA DE REDONDEO APLICADA:
  - Valores por ENCIMA del entero → Se bajan (134.9999... → 135)
  - Valores por DEBAJO del entero → Se suben (17.0000... → 17)
  - Exactos al entero → No cambian (24.0 → 24)
  - Decimales .5 → Redondeo estándar (24.5 → 24 o 25)

ARCHIVO ORIGINAL:
  - Se conserva intacto
  - NO se modifica

CÓMO USAR EN OTROS DATOS:
  1. Abre este script
  2. Modifica estas rutas:
     - input_shp = tu shapefile de entrada
     - output_folder = carpeta donde guardar el resultado
  3. Guarda y ejecuta
""")
print("=" * 70)
