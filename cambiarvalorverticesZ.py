import arcpy
import os

# === PARÁMETROS DE ENTRADA ===

entrada = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\OP\paralelas.shp"

carpeta_salida = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\OP\\"

salida = os.path.join(carpeta_salida, "paralelasrest.shp")

valor_a_restar = 0.01  

# === PROCESO ===
arcpy.env.overwriteOutput = True

# Obtener el tipo de geometría
desc = arcpy.Describe(entrada)
spatial_ref = desc.spatialReference

# Crear archivo de salida
arcpy.CreateFeatureclass_management(
    out_path=carpeta_salida,
    out_name="paralelasrest.shp",
    geometry_type="POLYLINE",
    spatial_reference=spatial_ref,
    has_m="DISABLED",
    has_z="ENABLED"
)

# Copiar campos
campos = [f.name for f in arcpy.ListFields(entrada) if f.type not in ('OID', 'Geometry')]
for campo in campos:
    field_type = [f.type for f in arcpy.ListFields(entrada) if f.name == campo][0]
    arcpy.AddField_management(salida, campo, field_type)

# Editar geometría y copiar atributos
with arcpy.da.SearchCursor(entrada, ['SHAPE@'] + campos) as cursor_in:
    with arcpy.da.InsertCursor(salida, ['SHAPE@'] + campos) as cursor_out:
        for row in cursor_in:
            linea = row[0]
            partes_modificadas = []
            
            for parte in linea:
                puntos_mod = []
                for p in parte:
                    nueva_z = p.Z - valor_a_restar
                    nuevo_punto = arcpy.Point(p.X, p.Y, nueva_z)
                    puntos_mod.append(nuevo_punto)
                partes_modificadas.append(arcpy.Polyline(arcpy.Array(puntos_mod), spatial_ref, True))
            
            nueva_geom = partes_modificadas[0]
            
            # Modificar el valor de ELEVACI si existe
            fila_mod = list(row[1:])
            if 'ELEVACI' in campos:
                idx_elevaci = campos.index('ELEVACI')
                fila_mod[idx_elevaci] = fila_mod[idx_elevaci] - valor_a_restar
            
            cursor_out.insertRow([nueva_geom] + fila_mod)

print("✅ Proceso completado. Archivo guardado en:", salida)