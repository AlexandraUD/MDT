import geopandas as gpd
from shapely.geometry import LineString, MultiLineString, Point
import os

# ======================================================
# ENTRADAS
# ======================================================

ruta_drenajes = r"C:\argenis\_MDT\PAPAYAL_BOLIVAR\24_Papayal_1K_(Bolívar)\OP\2_SHAPES_EDICION\polylinea2.shp"

ruta_curvas = r"C:\argenis\_MDT\PAPAYAL_BOLIVAR\24_Papayal_1K_(Bolívar)\OP\2_SHAPES_EDICION\curva_nivel2.shp"

carpeta_salida = r"C:\argenis\_MDT\PAPAYAL_BOLIVAR\24_Papayal_1K_(Bolívar)\OP"

# ======================================================
# LEER ARCHIVOS
# ======================================================

print("=" * 70)
print("PASOS 1, 2, 3, 4 - MODIFICAR DRENAJES")
print("=" * 70)

drenajes = gpd.read_file(ruta_drenajes)
curvas = gpd.read_file(ruta_curvas)

# Asegurar mismo CRS
if drenajes.crs != curvas.crs:
    curvas = curvas.to_crs(drenajes.crs)

# ======================================================
# PASO 1: GENERAR PUNTOS DE INTERSECCION
# ======================================================
print("\n[PASO 1/4] Generando puntos de intersección...")

intersecciones_list = []
for _, dren in drenajes.iterrows():
    for _, curv in curvas.iterrows():
        if dren.geometry.intersects(curv.geometry):
            inter = dren.geometry.intersection(curv.geometry)
            if not inter.is_empty:
                if inter.geom_type == "Point":
                    intersecciones_list.append(inter)
                elif inter.geom_type == "MultiPoint":
                    intersecciones_list.extend(list(inter.geoms))

print(f"✅ {len(intersecciones_list)} puntos de intersección generados.")

# Guardar intersecciones
if len(intersecciones_list) > 0:
    gdf_intersecciones = gpd.GeoDataFrame(
        {"geometry": intersecciones_list},
        crs=drenajes.crs
    )
    intersecciones_shp = os.path.join(carpeta_salida, "01_intersecciones.shp")
    gdf_intersecciones.to_file(intersecciones_shp)
    print(f"   Guardado en: {intersecciones_shp}")

# ======================================================
# PASO 2: GENERAR BUFFER DE 1m
# ======================================================
print("\n[PASO 2/4] Generando buffer de 1m alrededor de intersecciones...")

buffer_1m_list = [punto.buffer(1.0) for punto in intersecciones_list]

gdf_buffer_1m = gpd.GeoDataFrame(
    {"geometry": buffer_1m_list},
    crs=drenajes.crs
)
buffer_1m_shp = os.path.join(carpeta_salida, "02_buffer_1m.shp")
gdf_buffer_1m.to_file(buffer_1m_shp)
print(f"✅ Buffer de 1m generado.")
print(f"   Guardado en: {buffer_1m_shp}")

buffer_union_1m = gdf_buffer_1m.unary_union

# ======================================================
# PASO 3: ELIMINAR VERTICES DENTRO DEL BUFFER DE 1m
# ======================================================
print("\n[PASO 3/4] Eliminando vértices dentro del buffer de 1m...")

vertices_eliminados_total = 0
drenajes_paso3 = []

for idx, row in drenajes.iterrows():
    geom = row.geometry
    
    if geom is None or geom.is_empty or not geom.is_valid:
        drenajes_paso3.append(geom)
        continue
    
    partes = list(geom.geoms) if isinstance(geom, MultiLineString) else [geom]
    nuevas_partes = []
    
    for parte in partes:
        if len(parte.coords) < 2:
            continue
        
        coords = list(parte.coords)
        coords_finales = []
        
        for coord in coords:
            punto = Point(coord[0], coord[1])
            
            # ¿Es intersección? (tolerancia 0.01m)
            es_interseccion = False
            for inter_punto in intersecciones_list:
                if punto.distance(inter_punto) < 0.01:
                    es_interseccion = True
                    break
            
            if es_interseccion:
                coords_finales.append(coord)
            else:
                if buffer_union_1m.contains(punto):
                    vertices_eliminados_total += 1
                else:
                    coords_finales.append(coord)
        
        if len(coords_finales) >= 2:
            nuevas_partes.append(LineString(coords_finales))
    
    if len(nuevas_partes) == 1:
        drenajes_paso3.append(nuevas_partes[0])
    elif len(nuevas_partes) > 1:
        drenajes_paso3.append(MultiLineString(nuevas_partes))
    else:
        drenajes_paso3.append(None)

drenajes["geometry"] = drenajes_paso3
drenajes_validos = drenajes[drenajes.geometry.notna()].copy()

print(f"✅ {vertices_eliminados_total} vértices eliminados.")

# ======================================================
# PASO 4: GENERAR BUFFER DE 0.3m
# ======================================================
print("\n[PASO 4/4] Generando buffer de 0.3m alrededor de intersecciones...")

buffer_03m_list = [punto.buffer(0.3) for punto in intersecciones_list]

gdf_buffer_03m = gpd.GeoDataFrame(
    {"geometry": buffer_03m_list},
    crs=drenajes.crs
)
buffer_03m_shp = os.path.join(carpeta_salida, "04_buffer_0.3m.shp")
gdf_buffer_03m.to_file(buffer_03m_shp)
print(f"✅ Buffer de 0.3m generado.")
print(f"   Guardado en: {buffer_03m_shp}")

# Guardar drenajes procesados
drenajes_paso4_shp = os.path.join(carpeta_salida, "03_drenajes_sin_vertices_buffer.shp")
drenajes_validos.to_file(drenajes_paso4_shp)
print(f"   Drenajes guardados en: {drenajes_paso4_shp}")

# ======================================================
# RESUMEN
# ======================================================
print("\n" + "=" * 70)
print("RESUMEN FINAL")
print("=" * 70)
print(f"[1] Puntos de intersección: {len(intersecciones_list)}")
print(f"[2] Buffer de 1m generado")
print(f"[3] Vértices eliminados: {vertices_eliminados_total}")
print(f"    Drenajes después del paso 3: {len(drenajes_validos)}")
print(f"[4] Buffer de 0.3m generado")
print("\nArchivos generados:")
print(f"  01_intersecciones.shp")
print(f"  02_buffer_1m.shp")
print(f"  03_drenajes_sin_vertices_buffer.shp")
print(f"  04_buffer_0.3m.shp")
print("=" * 70)
print("\n✅ Pasos 1-4 completados.")