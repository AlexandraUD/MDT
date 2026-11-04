import geopandas as gpd
from shapely.geometry import Point, LineString, MultiLineString
import os

# === ENTRADAS ===

ruta_polilineas = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\PRO\2_SHAPES_EDICION\polylinea2.shp"

ruta_curvas = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\PRO\2_SHAPES_EDICION\curva_nivel2.shp"

carpeta_salida = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\OP\\"

print("=" * 70)
print("ELIMINAR VÉRTICES EN BUFFERS DE INTERSECCIONES")
print("PRESERVANDO TODOS LOS VÉRTICES DE INTERSECCIONES")
print("=" * 70)

# === LEER ARCHIVOS ===
print("\n[0/5] Cargando archivos...")
polilineas = gpd.read_file(ruta_polilineas)
curvas = gpd.read_file(ruta_curvas)

polilineas = polilineas[polilineas.geometry.notna()].copy()
curvas = curvas[curvas.geometry.notna()].copy()

if polilineas.crs != curvas.crs:
    curvas = curvas.to_crs(polilineas.crs)

print(f"✅ {len(polilineas)} polilíneas, {len(curvas)} curvas")

# === PASO 1: ENCONTRAR INTERSECCIONES ===
print("\n[1/5] Encontrando intersecciones...")
intersecciones = []

for _, poli in polilineas.iterrows():
    for _, curva in curvas.iterrows():
        if poli.geometry.intersects(curva.geometry):
            inter = poli.geometry.intersection(curva.geometry)
            if not inter.is_empty:
                if inter.geom_type == "Point":
                    intersecciones.append(inter)
                elif inter.geom_type == "MultiPoint":
                    intersecciones.extend(list(inter.geoms))

print(f"✅ {len(intersecciones)} intersecciones encontradas")

gdf_inter = gpd.GeoDataFrame({"geometry": intersecciones}, crs=polilineas.crs)
inter_shp = os.path.join(carpeta_salida, "intersecciones.shp")
gdf_inter.to_file(inter_shp)

# === PASO 2: CREAR BUFFER PARA CADA INTERSECCIÓN ===

print("\n[2/5] Creando buffers individuales por intersección...")
buffers_individuales = [punto.buffer(0.1) for punto in intersecciones]
gdf_buffer = gpd.GeoDataFrame({"geometry": buffers_individuales}, crs=polilineas.crs)
buffer_shp = os.path.join(carpeta_salida, "buffer_0.1.shp")
gdf_buffer.to_file(buffer_shp)
print(f"✅ {len(buffers_individuales)} buffers generados")

# === PASO 3: ELIMINAR VÉRTICES DENTRO DE BUFFERS (EXCEPTO INTERSECCIONES) ===
print("\n[3/5] Eliminando vértices dentro de buffers...")
vertices_eliminados = 0
polilineas_finales = []

# Tolerancia para considerar que un vértice está "cerca" de una intersección
tolerancia_intersection = 0.001  # 1mm - ajusta según necesario

for idx, row in polilineas.iterrows():
    geom = row.geometry
    if geom is None or geom.is_empty:
        polilineas_finales.append(geom)
        continue
    
    partes = list(geom.geoms) if isinstance(geom, MultiLineString) else [geom]
    nuevas_partes = []
    
    for parte in partes:
        coords = list(parte.coords)
        coords_finales = []
        
        for coord in coords:
            punto = Point(coord[0], coord[1])
            
            # Verificar si está dentro de algún buffer de intersección
            dentro_buffer = False
            for buffer_geom in buffers_individuales:
                if buffer_geom.contains(punto):
                    dentro_buffer = True
                    break
            
            if dentro_buffer:
                # Está en buffer: verificar si está CERCA de una intersección
                cerca_de_interseccion = False
                for inter in intersecciones:
                    if punto.distance(inter) < tolerancia_intersection:
                        cerca_de_interseccion = True
                        break
                
                # Si está cerca de intersección, CONSERVAR; si no, ELIMINAR
                if cerca_de_interseccion:
                    coords_finales.append(coord)
                else:
                    vertices_eliminados += 1
            else:
                # NO está en buffer, conservar
                coords_finales.append(coord)
        
        # Crear línea solo si quedan 2 o más coordenadas
        if len(coords_finales) >= 2:
            nuevas_partes.append(LineString(coords_finales))
    
    # Guardar la geometría final
    if len(nuevas_partes) == 1:
        polilineas_finales.append(nuevas_partes[0])
    elif len(nuevas_partes) > 1:
        polilineas_finales.append(MultiLineString(nuevas_partes))
    else:
        polilineas_finales.append(None)
    
    if (idx + 1) % 100 == 0:
        print(f"   Procesadas {idx + 1} polilíneas...")

polilineas["geometry"] = polilineas_finales
polilineas_resultado = polilineas[polilineas.geometry.notna()].copy()

poly_sin_shp = os.path.join(carpeta_salida, "polysin.shp")
polilineas_resultado.to_file(poly_sin_shp)

# === RESUMEN ===
print("\n" + "=" * 70)
print("RESUMEN")
print("=" * 70)
print(f"Intersecciones encontradas: {len(intersecciones)}")
print(f"Buffers de 0.1 creados: {len(buffers_individuales)}")
print(f"Vértices eliminados: {vertices_eliminados}")
print(f"Polilíneas resultantes: {len(polilineas_resultado)}")
print(f"\nArchivos generados:")
print(f"  {inter_shp}")
print(f"  {buffer_shp}")
print(f"  {poly_sin_shp}")
print("=" * 70)
print("✅ Proceso completado")