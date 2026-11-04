import geopandas as gpd
from shapely.geometry import LineString, MultiLineString
import os

ruta_drenajes = r"C:\argenis\_MDT\SOCRRO_SANT\21_Socorro_1K_(Santander)\OP\drenajed.shp"
carpeta_salida = r"C:\argenis\_MDT\SOCRRO_SANT\21_Socorro_1K_(Santander)\OP"

drenajes = gpd.read_file(ruta_drenajes)

def ajustar_z(coords):
    coords_nuevas = []
    for c in coords:
        z = c[2] if len(c) > 2 else 0
        z_decimal = z % 1
        
        if abs(z_decimal - 0.85) < 1e-6:
            z_ajustado = z + 0.05
        elif abs(z_decimal - 0.8) < 1e-6:
            z_ajustado = z + 0.1
        elif abs(z_decimal - 0.75) < 1e-6:
            z_ajustado = z + 0.10
        elif abs(z_decimal - 0.7) < 1e-6:
            z_ajustado = z + 0.15
        elif abs(z_decimal - 0.1) < 1e-6:
            z_ajustado = z - 0.06
        elif abs(z_decimal - 0.15) < 1e-6:
            z_ajustado = z - 0.11
        elif abs(z_decimal - 0.12) < 1e-6:
            z_ajustado = z - 0.07
        else:
            z_ajustado = z
        
        coords_nuevas.append((c[0], c[1], z_ajustado))
    return coords_nuevas

drenajes_ajustados = []

for idx, row in drenajes.iterrows():
    geom = row.geometry
    if geom is None or geom.is_empty:
        drenajes_ajustados.append(geom)
        continue
    
    if isinstance(geom, MultiLineString):
        partes = list(geom.geoms)
    else:
        partes = [geom]
    
    partes_nuevas = []
    for parte in partes:
        coords = list(parte.coords)
        coords_ajustadas = ajustar_z(coords)
        partes_nuevas.append(LineString(coords_ajustadas))
    
    if len(partes_nuevas) == 1:
        drenajes_ajustados.append(partes_nuevas[0])
    else:
        drenajes_ajustados.append(MultiLineString(partes_nuevas))

drenajes["geometry"] = drenajes_ajustados
drenajes.to_file(os.path.join(carpeta_salida, "05_drenajes_z_ajustadas.shp"))

print("✅ Z ajustadas")
print(f"Salida: {os.path.join(carpeta_salida, '05_drenajes_z_ajustadas.shp')}")