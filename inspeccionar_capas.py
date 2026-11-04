import arcpy

capaA = r"C:\argenis\_MDT\SOGAMOSO\PRO\2_SHAPES_EDICION\curva_nivel2.shp"
capaB = r"C:\argenis\_MDT\SOGAMOSO\PRO\2_SHAPES_EDICION\polylinea2.shp"

def inspeccionar(capa, nombre):
    desc = arcpy.Describe(capa)
    print(f"\n=== {nombre} ({capa}) ===")
    print(f"Tipo de geometría: {desc.shapeType}")
    print(f"Tiene Z: {desc.hasZ}")
    print(f"Tiene M: {desc.hasM}")
    print(f"Sistema de referencia: {desc.spatialReference.name}")
    print(f"Total de features: {arcpy.GetCount_management(capa)[0]}")
    print("Campos:")
    for f in arcpy.ListFields(capa):
        print(f"  - {f.name} ({f.type})")

inspeccionar(capaA, "capaA - curva_nivel2")
inspeccionar(capaB, "capaB - polylinea2")

# Intersect de prueba en memoria para ver qué nombres de campo FID_ genera
scratch = r"memory\intersect_test"
if arcpy.Exists(scratch):
    arcpy.management.Delete(scratch)

arcpy.analysis.Intersect([capaA, capaB], scratch, output_type="POINT")

print(f"\n=== Campos generados por Intersect ({scratch}) ===")
for f in arcpy.ListFields(scratch):
    print(f"  - {f.name} ({f.type})")

arcpy.management.Delete(scratch)