import rasterio
from rasterio.mask import mask
import geopandas as gpd
import numpy as np

# Rutas
shp_path = r"C:\argenis\_MDT\ARAUCA_ARAUCA\30_Arauca_1K_(Arauca)\LIMITE\LIMITE_ARAUCA_1K_81001000.shp"
raster_path = r"C:\argenis\_MDT\ARAUCA_ARAUCA\30_Arauca_1K_(Arauca)\PRO\3_SALIDAS\RASTER_107\MDT_Escala.tif"
output_path = r"C:\argenis\_MDT\ARAUCA_ARAUCA\30_Arauca_1K_(Arauca)\OP\areas_no_cubiertas.shp"

# Leer datos
gdf = gpd.read_file(shp_path)
poligono = gdf.geometry.unary_union

with rasterio.open(raster_path) as src:
    nodata = src.nodata
    crs_raster = src.crs
    geoms = [poligono]
    
    # Recortar raster
    recortado, transform = mask(src, geoms, crop=True)
    banda = recortado[0]

# Identificar píxeles sin dato
if nodata is not None:
    sin_dato = (banda == nodata)
else:
    sin_dato = np.isnan(banda)

pixeles_sin_dato = sin_dato.sum()
pixeles_totales = banda.size
pct_sin_dato = 100 * pixeles_sin_dato / pixeles_totales

print(f"Píxeles sin dato: {pixeles_sin_dato}")
print(f"Píxeles totales: {pixeles_totales}")
print(f"Porcentaje sin dato: {pct_sin_dato:.4f}%")

# Solo si hay REALMENTE más del 1% sin dato (no ruido de borde)
if pct_sin_dato > 1.0:
    print("⚠️ Hay cobertura incompleta. Vectorizando huecos...")
    from rasterio.features import shapes
    from shapely.geometry import shape
    
    polys = []
    for geom, val in shapes(sin_dato.astype(np.uint8), transform=transform):
        if val == 1:
            polys.append(shape(geom))
    
    if polys:
        huecos = gpd.GeoSeries(polys).unary_union
        huecos_dentro = huecos.intersection(poligono)
        
        if not huecos_dentro.is_empty:
            gdf_out = gpd.GeoDataFrame(geometry=[huecos_dentro], crs=str(crs_raster))
            gdf_out.to_file(output_path)
            print(f"✅ Guardado: {output_path}")
else:
    print("✅ Raster cubre totalmente el polígono (sin huecos significativos)")