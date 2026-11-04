import rasterio
from rasterio.features import shapes, rasterize
import geopandas as gpd
from shapely.geometry import shape
import numpy as np

# Rutas
raster_path = r'C:\argenis\LiDAR\15632_SABOYÁ\1_OP\tif\cortado.tif'

limite_path = r'C:\argenis\LiDAR\15632_SABOYÁ\LIMITE_BUFFER\15632_Saboya_Limite_Buffer5m.shp'

output_path = r'C:\argenis\LiDAR\15632_SABOYÁ\1_OP\tif\Huecos.shp'

# 1. Leer datos
limite_gdf = gpd.read_file(limite_path)
limite_geom = limite_gdf.geometry.values

with rasterio.open(raster_path) as src:
    data = src.read(1)
    transform = src.transform
    nodata = src.nodata
    crs = src.crs
    
    # 2. Rasterizar el límite con la misma resolución
    limite_raster = rasterize(
        [(geom, 1) for geom in limite_geom],
        out_shape=data.shape,
        transform=transform,
        fill=0,
        dtype=np.uint8
    )
    
    # 3. Identificar huecos: NoData dentro del límite
    if nodata is not None:
        mask_nodata = data == nodata
    else:
        mask_nodata = np.isnan(data)
    
    # Huecos = NoData AND dentro del límite
    huecos = (mask_nodata) & (limite_raster == 1)
    
    # 4. Convertir a polígonos
    shapes_gen = shapes(
        huecos.astype(np.uint8),
        mask=huecos,
        transform=transform
    )
    
    geometries = [shape(geom) for geom, value in shapes_gen if value == 1]
    
    if geometries:
        huecos_gdf = gpd.GeoDataFrame(
            {'geometry': geometries},
            crs=crs
        )
        
        # 5. Intersectar con el límite para usar su geometría suave
        limite_union = limite_gdf.geometry.unary_union
        huecos_gdf['geometry'] = huecos_gdf.geometry.intersection(limite_union)
        
        # Remover geometrías vacías si las hay
        huecos_gdf = huecos_gdf[huecos_gdf.geometry.is_empty == False]
        
        huecos_gdf.to_file(output_path)
        print(f"✓ {len(geometries)} polígonos de huecos creados")
        print(f"✓ Guardado en: {output_path}")
    else:
        print("No hay huecos dentro del límite")