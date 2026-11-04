import arcpy
import os

# === RUTAS ===

RUTA_CAPA_A = r"C:\argenis\_MDT\SOGAMOSO\PRO\2_SHAPES_EDICION\curva_nivel2.shp"

RUTA_CAPA_B = r"C:\argenis\_MDT\SOGAMOSO\PRO\2_SHAPES_EDICION\polylinea2.shp"

RUTA_SALIDA = r"C:\argenis\_MDT\SOGAMOSO\OP\polylinea2_editada.shp"


def script_tool(capaA, capaB, capa_salida):
    if not arcpy.Exists(capaA):
        arcpy.AddError(f"No se encontró la capa: {capaA}")
        raise arcpy.ExecuteError
    if not arcpy.Exists(capaB):
        arcpy.AddError(f"No se encontró la capa: {capaB}")
        raise arcpy.ExecuteError

    arcpy.env.outputZFlag = "Enabled"
    spatial_ref = arcpy.Describe(capaA).spatialReference

    intersecciones = "memory\\intersecciones"
    puntos_generados = "memory\\puntos_generados"

    if arcpy.Exists(intersecciones):
        arcpy.management.Delete(intersecciones)
    if arcpy.Exists(puntos_generados):
        arcpy.management.Delete(puntos_generados)

    arcpy.analysis.Intersect([capaA, capaB], intersecciones, output_type="POINT")

    # Descomponer multipuntos (dos curvas pueden cruzar la misma polilínea más de una vez)
    arcpy.management.MultipartToSinglepart(intersecciones, puntos_generados)

    total_intersecciones = int(arcpy.GetCount_management(puntos_generados)[0])

    # Campos FID_ que Intersect asigna a cada capa de entrada (se conservan tras MultipartToSinglepart)
    campos_fid = [f.name for f in arcpy.ListFields(puntos_generados) if f.name.upper().startswith("FID_")]
    if len(campos_fid) < 2:
        arcpy.AddError(
            "No se identificaron los campos FID_ generados por Intersect. "
            "Revisa arcpy.ListFields(puntos_generados)."
        )
        raise arcpy.ExecuteError
    campo_fid_a, campo_fid_b = campos_fid[0], campos_fid[1]

    # Precargar geometrías de capaA una sola vez (evita reabrir cursores por cada punto)
    curvas_por_oid = {oid: geom for oid, geom in arcpy.da.SearchCursor(capaA, ["OID@", "SHAPE@"])}

    # Z de cada punto usando directamente la curva que lo generó (FID_a) — sin buscar entre todas
    puntos_por_linea_b = {}
    with arcpy.da.SearchCursor(puntos_generados, ["SHAPE@XY", campo_fid_a, campo_fid_b]) as cursor_pts:
        for (x, y), oid_a, oid_b in cursor_pts:
            linea = curvas_por_oid.get(oid_a)
            if linea is None:
                continue
            punto = arcpy.Point(x, y)
            m = linea.measureOnLine(punto)
            if m is None:
                continue
            punto3d = linea.positionAlongLine(m, use_percentage=False).centroid
            puntos_por_linea_b.setdefault(oid_b, []).append((punto3d.X, punto3d.Y, punto3d.Z))

    if arcpy.Exists(capa_salida):
        arcpy.management.Delete(capa_salida)
    arcpy.CopyFeatures_management(capaB, capa_salida)

    vertices_insertados = 0
    polilineas_omitidas = 0

    # Un único UpdateCursor sobre capaB; cada línea solo revisa SUS puntos, no los 40000
    with arcpy.da.UpdateCursor(capa_salida, ["OID@", "SHAPE@"]) as lineas:
        for oid, linea in lineas:
            puntos = puntos_por_linea_b.get(oid)
            if not puntos:
                continue
            try:
                if linea is None or linea.pointCount < 2:
                    raise ValueError("Geometría vacía o con menos de 2 vértices.")

                nuevas_partes = []
                for parte in linea:
                    if len(parte) < 2:
                        raise ValueError("Parte con menos de 2 vértices.")
                    nueva_parte = arcpy.Array()
                    pendientes = list(puntos)
                    for i in range(len(parte) - 1):
                        p1, p2 = parte[i], parte[i + 1]
                        nueva_parte.add(p1)
                        segmento = arcpy.Polyline(arcpy.Array([p1, p2]), linea.spatialReference, has_z=True)
                        restantes = []
                        for (px, py, pz) in pendientes:
                            punto_geom = arcpy.PointGeometry(arcpy.Point(px, py, pz), spatial_ref)
                            if segmento.distanceTo(punto_geom) < 0.01:
                                nueva_parte.add(arcpy.Point(px, py, pz))
                                vertices_insertados += 1
                            else:
                                restantes.append((px, py, pz))
                        pendientes = restantes
                    nueva_parte.add(parte[-1])
                    nuevas_partes.append(nueva_parte)

                nueva_geom = arcpy.Polyline(arcpy.Array(nuevas_partes), linea.spatialReference, has_z=True)
                lineas.updateRow([oid, nueva_geom])
            except Exception as e:
                arcpy.AddWarning(f"⚠️ Polilínea OID {oid} omitida: {e}")
                polilineas_omitidas += 1
                continue

    arcpy.management.Delete(intersecciones)
    arcpy.management.Delete(puntos_generados)

    arcpy.AddMessage("✅ Proceso completado.")
    arcpy.AddMessage(f" Intersecciones totales: {total_intersecciones}")
    arcpy.AddMessage(f"➕ Vértices insertados: {vertices_insertados}")
    arcpy.AddMessage(f" Polilíneas omitidas por errores: {polilineas_omitidas}")


if __name__ == "__main__":
    script_tool(RUTA_CAPA_A, RUTA_CAPA_B, RUTA_SALIDA)