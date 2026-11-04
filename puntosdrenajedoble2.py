import geopandas as gpd
from shapely.geometry import LineString, MultiLineString, Point
import os
import math

ruta_intersecciones = r"C:\argenis\_MDT\SOCRRO_SANT\21_Socorro_1K_(Santander)\OP\01_intersecciones.shp"
ruta_drenajes = r"C:\argenis\_MDT\SOCRRO_SANT\21_Socorro_1K_(Santander)\OP\03_drenajes_sin_vertices_buffer.shp"
ruta_buffer_03m = r"C:\argenis\_MDT\SOCRRO_SANT\21_Socorro_1K_(Santander)\OP\04_buffer_0.3m.shp"
ruta_curvas = r"C:\argenis\_MDT\SOCRRO_SANT\21_Socorro_1K_(Santander)\PROS\2_SHAPES_EDICION\curva_nivel2.shp"
carpeta_salida = r"C:\argenis\_MDT\SOCRRO_SANT\21_Socorro_1K_(Santander)\OP"

print("=" * 70)
print("PASO 5 - INSERTAR VERTICES EN INTERSECCIONES")
print("=" * 70)

intersecciones = gpd.read_file(ruta_intersecciones)
drenajes = gpd.read_file(ruta_drenajes)
buffers_03m = gpd.read_file(ruta_buffer_03m)
curvas = gpd.read_file(ruta_curvas)

if drenajes.crs != intersecciones.crs:
    intersecciones = intersecciones.to_crs(drenajes.crs)
if drenajes.crs != buffers_03m.crs:
    buffers_03m = buffers_03m.to_crs(drenajes.crs)
if drenajes.crs != curvas.crs:
    curvas = curvas.to_crs(drenajes.crs)

print(f"\n✅ Archivos cargados: {len(intersecciones)}, {len(drenajes)}, {len(buffers_03m)}, {len(curvas)}")

def calcular_z_vertices(punto_inter, puntos_cruces, drenaje_geom, curvas_gdf, distancia_rayo=20):
    coords_drenaje = list(drenaje_geom.coords)
    z_base = punto_inter.z if hasattr(punto_inter, 'z') else 0

    if len(coords_drenaje) < 2 or len(puntos_cruces) != 2:
        return None, None

    # Punto más cercano
    idx = min(range(len(coords_drenaje)), 
              key=lambda i: (coords_drenaje[i][0] - punto_inter.x)**2 + 
                           (coords_drenaje[i][1] - punto_inter.y)**2)
    punto_m = coords_drenaje[idx]

    # Vector tangente
    if idx == 0:
        vx = coords_drenaje[1][0] - punto_m[0]
        vy = coords_drenaje[1][1] - punto_m[1]
    elif idx == len(coords_drenaje) - 1:
        vx = punto_m[0] - coords_drenaje[-2][0]
        vy = punto_m[1] - coords_drenaje[-2][1]
    else:
        vx = coords_drenaje[idx + 1][0] - coords_drenaje[idx - 1][0]
        vy = coords_drenaje[idx + 1][1] - coords_drenaje[idx - 1][1]

    mag = math.sqrt(vx**2 + vy**2)
    if mag < 1e-10:
        return None, None
    vx /= mag
    vy /= mag

    normal_izq = (-vy, vx)
    normal_der = (vy, -vx)

    # Raycast
    def raycast_z(direccion):
        x_fin = punto_m[0] + direccion[0] * distancia_rayo
        y_fin = punto_m[1] + direccion[1] * distancia_rayo
        rayo = LineString([(punto_m[0], punto_m[1]), (x_fin, y_fin)])
        for _, curva in curvas_gdf.iterrows():
            if rayo.intersects(curva.geometry):
                try:
                    coords_curva = list(curva.geometry.coords)
                    return float(coords_curva[0][2]) if len(coords_curva[0]) > 2 else None
                except:
                    return None
        return None

    z_izq = raycast_z(normal_izq)
    z_der = raycast_z(normal_der)

    # Detectar cuál lado baja
    baja_izq = z_izq is not None and z_izq < z_base
    baja_der = z_der is not None and z_der < z_base

    if not baja_izq and not baja_der:
        return None, None  # No detectó bajada en ningún lado

    # Si solo uno baja, ese es el lado izquierdo
    if baja_izq and not baja_der:
        normal_baja = normal_izq
    elif baja_der and not baja_izq:
        normal_baja = normal_der
    else:  # Ambos bajan
        if (z_base - z_izq) >= (z_base - z_der):
            normal_baja = normal_izq
        else:
            normal_baja = normal_der

    # Clasificar puntos
    p0, p1 = puntos_cruces[0], puntos_cruces[1]
    proj_0 = (p0.x - punto_inter.x) * normal_baja[0] + (p0.y - punto_inter.y) * normal_baja[1]
    proj_1 = (p1.x - punto_inter.x) * normal_baja[0] + (p1.y - punto_inter.y) * normal_baja[1]

    if proj_0 > proj_1:
        z_p0 = z_base - 0.15
        z_p1 = z_base + 0.10
    else:
        z_p0 = z_base + 0.10
        z_p1 = z_base - 0.15

    return z_p0, z_p1

print("\n[PASO 5] Insertando vértices...")
vertices_insertados = 0
drenajes_finales = []

for idx, row_dren in drenajes.iterrows():
    geom_drenaje = row_dren.geometry
    if geom_drenaje is None or geom_drenaje.is_empty:
        drenajes_finales.append(geom_drenaje)
        continue

    partes = list(geom_drenaje.geoms) if isinstance(geom_drenaje, MultiLineString) else [geom_drenaje]
    nuevas_partes = []

    for parte in partes:
        coords_con_nuevos = list(parte.coords)

        for inter_idx, (_, row_inter) in enumerate(intersecciones.iterrows()):
            punto_inter = row_inter.geometry
            buffer_03m = buffers_03m.iloc[inter_idx].geometry
            inter_geom = parte.intersection(buffer_03m.boundary)

            if not inter_geom.is_empty:
                if inter_geom.geom_type == "Point":
                    puntos_cruces = [inter_geom]
                elif inter_geom.geom_type == "MultiPoint":
                    puntos_cruces = list(inter_geom.geoms)
                else:
                    puntos_cruces = []

                if len(puntos_cruces) == 2:
                    z_p0, z_p1 = calcular_z_vertices(punto_inter, puntos_cruces, parte, curvas)
                    if z_p0 is not None and z_p1 is not None:
                        coords_con_nuevos.append((puntos_cruces[0].x, puntos_cruces[0].y, z_p0))
                        coords_con_nuevos.append((puntos_cruces[1].x, puntos_cruces[1].y, z_p1))
                        vertices_insertados += 2

        if len(coords_con_nuevos) > len(parte.coords):
            coords_ordenados = sorted(coords_con_nuevos, key=lambda c: parte.project(Point(c[0], c[1])))
            coords_unicos = []
            vistos = {}
            for c in coords_ordenados:
                clave = (round(c[0], 6), round(c[1], 6))
                if clave not in vistos:
                    vistos[clave] = set()
                z_redondeado = round(c[2], 4)
                if z_redondeado not in vistos[clave]:
                    coords_unicos.append(c)
                    vistos[clave].add(z_redondeado)
            if len(coords_unicos) >= 2:
                nuevas_partes.append(LineString(coords_unicos))
            else:
                nuevas_partes.append(parte)
        else:
            nuevas_partes.append(parte)

    if len(nuevas_partes) == 1:
        drenajes_finales.append(nuevas_partes[0])
    elif len(nuevas_partes) > 1:
        drenajes_finales.append(MultiLineString(nuevas_partes))
    else:
        drenajes_finales.append(None)

drenajes["geometry"] = drenajes_finales
drenajes_resultado = drenajes[drenajes.geometry.notna()].copy()
drenajes_final_shp = os.path.join(carpeta_salida, "05_drenajes_con_vertices_insertados.shp")
drenajes_resultado.to_file(drenajes_final_shp)

print(f"✅ {vertices_insertados} vértices insertados.")
print(f"Archivo: {drenajes_final_shp}\n✅ Paso 5 completado.")