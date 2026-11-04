import arcpy
import os
from collections import defaultdict

# ======================================================
# === ENTRADAS (RUTAS) =================================
# ======================================================

polilineas_A = r"C:\argenis\_MDT\SOCRRO_SANT\21_Socorro_1K_(Santander)\OP\cuerpoagua.shp"

polilineas_B = r"C:\argenis\_MDT\SOCRRO_SANT\21_Socorro_1K_(Santander)\PROS\3_SALIDAS\RASTER_250\Contornos.shp"

# Carpeta de salida
carpeta_salida = r"C:\argenis\_MDT\SOCRRO_SANT\21_Socorro_1K_(Santander)\OP"

# Archivos de salida
intersecciones_all = os.path.join(carpeta_salida, "intersecciones_3D.shp")
salida_multiples = os.path.join(carpeta_salida, "intersecciones_multiples.shp")

# ======================================================
# === CONFIGURACIÓN ====================================
# ======================================================

arcpy.env.overwriteOutput = True

# ======================================================
# === SCRIPT 1: CREAR INTERSECCIONES 3D ===============
# ======================================================

print("=" * 60)
print("PASO 1: Calculando intersecciones 3D...")
print("=" * 60)

# Crear feature class de salida (tipo POINT, 3D)
folder, name = os.path.split(intersecciones_all)
arcpy.management.CreateFeatureclass(
    folder,
    name,
    "POINT",
    spatial_reference=polilineas_A,
    has_z="ENABLED"
)

# Agregar campos de identificación
arcpy.management.AddField(intersecciones_all, "ID_A", "LONG")
arcpy.management.AddField(intersecciones_all, "ID_B", "LONG")

# Cargar todas las geometrías de B
geom_B = [(row[0], row[1]) for row in arcpy.da.SearchCursor(polilineas_B, ["OID@", "SHAPE@"])]

# Insert cursor para salida
with arcpy.da.InsertCursor(intersecciones_all, ["SHAPE@", "ID_A", "ID_B"]) as icur:

    # Recorrer polilíneas de A
    for oidA, geomA in arcpy.da.SearchCursor(polilineas_A, ["OID@", "SHAPE@"]):

        for oidB, geomB in geom_B:

            # Obtener intersección como punto (dimensión 0)
            inter = geomA.intersect(geomB, 1)

            # ===========================
            # VALIDAR INTERSECCIÓN VACÍA
            # ===========================
            is_empty = False

            # Caso 1: Si tiene la función isEmpty()
            if hasattr(inter, "isEmpty"):
                is_empty = inter.isEmpty
            else:
                # Caso 2: Si es Point o Multipoint: revisar pointCount
                if inter.pointCount == 0:
                    is_empty = True

            if is_empty:
                continue

            # ===========================
            # PROCESAR PUNTOS
            # ===========================
            if inter.type == "multipoint":
                for pt in inter:
                    icur.insertRow([pt, oidA, oidB])
            else:
                icur.insertRow([inter, oidA, oidB])

count_all = int(arcpy.GetCount_management(intersecciones_all).getOutput(0))
print(f"✔ Intersecciones creadas: {count_all} puntos")
print(f"📁 Archivo: {intersecciones_all}\n")

# ======================================================
# === SCRIPT 2: FILTRAR INTERSECCIONES MÚLTIPLES ======
# ======================================================

print("=" * 60)
print("PASO 2: Filtrando intersecciones múltiples...")
print("=" * 60)

# Verificar existencia
if not arcpy.Exists(intersecciones_all):
    raise FileNotFoundError("❌ No se encontró la capa de intersecciones base.")

# === 1. Leer campos y detectar ID_A y ID_B ===
campos = [f.name for f in arcpy.ListFields(intersecciones_all)]

id_a = next((f for f in campos if f.lower() == "id_a"), None)
id_b = next((f for f in campos if f.lower() == "id_b"), None)

if not id_a or not id_b:
    raise ValueError("❌ No se encontraron los campos ID_A y ID_B en la capa de entrada.")

# === 2. Contar ocurrencias de cada combinación contorno–polilínea ===
conteo = defaultdict(int)
with arcpy.da.SearchCursor(intersecciones_all, [id_a, id_b]) as cursor:
    for fidA, fidB in cursor:
        conteo[(fidA, fidB)] += 1

# === 3. Crear shapefile de salida con los mismos atributos ===
spatial_ref = arcpy.Describe(intersecciones_all).spatialReference
if arcpy.Exists(salida_multiples):
    arcpy.Delete_management(salida_multiples)

arcpy.management.CreateFeatureclass(
    out_path=os.path.dirname(salida_multiples),
    out_name=os.path.basename(salida_multiples),
    geometry_type="POINT",
    has_m="ENABLED",
    has_z="ENABLED",
    spatial_reference=spatial_ref
)

# Copiar los mismos campos de ID_A y ID_B
arcpy.management.AddField(salida_multiples, "ID_A", "LONG")
arcpy.management.AddField(salida_multiples, "ID_B", "LONG")

# === 4. Insertar solo las combinaciones que aparecen más de una vez ===
with arcpy.da.SearchCursor(intersecciones_all, [id_a, id_b, "SHAPE@"]) as scursor, \
     arcpy.da.InsertCursor(salida_multiples, ["ID_A", "ID_B", "SHAPE@"]) as icursor:

    for fidA, fidB, shape in scursor:
        if conteo[(fidA, fidB)] > 1:
            icursor.insertRow((fidA, fidB, shape))

# === 5. Verificación ===
count_multiples = int(arcpy.GetCount_management(salida_multiples).getOutput(0))
print(f"✔ Intersecciones múltiples filtradas: {count_multiples} puntos")
print(f"📁 Archivo: {salida_multiples}\n")

# ======================================================
# === RESUMEN FINAL ====================================
# ======================================================

print("=" * 60)
print("✅ PROCESO COMPLETADO EXITOSAMENTE")
print("=" * 60)
print(f"📊 Total intersecciones: {count_all}")
print(f"🎯 Intersecciones múltiples: {count_multiples}")
print(f"📁 Carpeta de salida: {carpeta_salida}")
print("=" * 60)