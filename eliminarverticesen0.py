import arcpy
import os
 
# === PARÁMETROS DE ENTRADA ===
entrada = r"C:\argenis\_MDT\ARAUCA_ARAUCA\30_Arauca_1K_(Arauca)\OP\poli.shp"

salida = r"C:\argenis\_MDT\ARAUCA_ARAUCA\30_Arauca_1K_(Arauca)\OP\poli0.shp"
 
# === CREAR FEATURE CLASS DE SALIDA ===
spatial_ref = arcpy.Describe(entrada).spatialReference
arcpy.CreateFeatureclass_management(
    out_path=os.path.dirname(salida),
    out_name=os.path.basename(salida),
    geometry_type="POLYLINE",
    spatial_reference=spatial_ref,
    has_z="ENABLED"
)
 
# === LISTAR CAMPOS EXISTENTES EN SALIDA PARA EVITAR DUPLICADOS ===
campos_salida_existentes = [f.name for f in arcpy.ListFields(salida)]
 
# === COPIAR CAMPOS DE ATRIBUTOS (EXCEPTO OID y Geometry) ===
for campo in arcpy.ListFields(entrada):
    if campo.type not in ('OID', 'Geometry') and campo.name not in campos_salida_existentes:
        arcpy.AddField_management(
            salida,
            campo.name,
            campo.type,
            field_length=campo.length
        )
 
# === PROCESAR POLILÍNEAS ===
campos = ["SHAPE@"] + [f.name for f in arcpy.ListFields(entrada) if f.type not in ('OID', 'Geometry')]
 
total_polilineas = 0
total_vertices = 0
vertices_procesados = 0
 
with arcpy.da.InsertCursor(salida, campos) as icur:
    with arcpy.da.SearchCursor(entrada, campos) as scur:
        for row in scur:
            total_polilineas += 1
            geom = row[0]
            otras = row[1:]
 
            if geom is None:
                continue
 
            nuevas_partes = []
            for part in geom:
                nueva_linea = []
                for p in part:
                    total_vertices += 1
                    if p and p.Z != 0:
                        nueva_linea.append(arcpy.Point(p.X, p.Y, p.Z))
                        vertices_procesados += 1
                if len(nueva_linea) >= 2:
                    nuevas_partes.append(arcpy.Array(nueva_linea))
 
            if nuevas_partes:
                nueva_geom = arcpy.Polyline(arcpy.Array(nuevas_partes), spatial_ref, has_z=True)
                icur.insertRow([nueva_geom] + list(otras))
 
print(f"✅ Proceso completado")
print(f"  Polilíneas procesadas: {total_polilineas}")
print(f"  Vértices originales: {total_vertices}")
print(f"  Vértices conservados: {vertices_procesados}")
print(f"  Vértices eliminados: {total_vertices - vertices_procesados}")