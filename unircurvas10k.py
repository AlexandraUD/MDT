import geopandas as gpd
import pandas as pd
from shapely.ops import linemerge
from shapely.geometry import MultiLineString
import numpy as np

def unir_curvas_rapido(input_shp, output_shp, rango_z=0.1, tolerancia_espacial=0.01):
    """
    Une curvas de nivel fragmentadas de forma eficiente.
    Adaptado para ESCALA 1:10000 (equidistancia 100m)
    
    Parameters:
    - input_shp: ruta del shapefile de entrada
    - output_shp: ruta del shapefile de salida
    - rango_z: tolerancia para agrupar elevaciones (metros) - 0.1 para 1:10000
    - tolerancia_espacial: distancia máxima entre extremos para unir (metros)
    """
    
    # ============================================================
    # 1. LECTURA Y LIMPIEZA DE DATOS
    # ============================================================
    print("📂 Leyendo shapefile...")
    gdf = gpd.read_file(input_shp)
    
    # Contar registros antes de filtrar
    total_original = len(gdf)
    
    # Filtrar geometrías nulas o vacías
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
    
    # Reportar cuántas se eliminaron
    eliminadas = total_original - len(gdf)
    print(f"   Registros totales: {total_original}")
    print(f"   Registros válidos: {len(gdf)}")
    if eliminadas > 0:
        print(f"   ⚠️ Registros sin geometría eliminados: {eliminadas}")
    
    # ============================================================
    # 2. VALIDACIÓN DE CAMPO ELEVATION
    # ============================================================
    if 'Elevation' not in gdf.columns:
        raise ValueError(f"La capa debe tener campo 'Elevation'. Campos disponibles: {list(gdf.columns)}")
    
    # ============================================================
    # 3. CONVERSIÓN DE SISTEMA DE COORDENADAS
    # ============================================================
    if gdf.crs.is_geographic:
        print("⚠️ Convirtiendo a proyectadas para cálculos precisos...")
        gdf = gdf.to_crs(gdf.estimate_utm_crs())
    
    # ============================================================
    # 4. AGRUPACIÓN POR ELEVACIÓN
    # ============================================================
    print("🔢 Agrupando por elevación...")
    print(f"   Escala: 1:10000 (equidistancia 100m)")
    print(f"   rango_z: {rango_z}")
    
    gdf['elev_grupo'] = np.round(gdf['Elevation'] / rango_z) * rango_z
    
    # Lista para almacenar las curvas procesadas
    resultados = []
    
    # ============================================================
    # 5. PROCESAMIENTO POR GRUPO DE ELEVACIÓN
    # ============================================================
    grupos = gdf.groupby('elev_grupo')
    total_grupos = len(grupos)
    
    for idx, (elevacion, grupo) in enumerate(grupos, 1):
        print(f"⚙️ Procesando elevación {elevacion:.2f}m ({idx}/{total_grupos})...")
        
        # ============================================================
        # 5.1. DESCOMPOSICIÓN DE GEOMETRÍAS MULTIPARTE
        # ============================================================
        lineas = []
        
        for geom in grupo.geometry:
            if geom is None or geom.is_empty:
                continue
            
            if geom.geom_type == 'LineString':
                lineas.append(geom)
            
            elif geom.geom_type == 'MultiLineString':
                lineas.extend(list(geom.geoms))
        
        if not lineas:
            continue
        
        # ============================================================
        # 5.2. UNIÓN DE LÍNEAS CONECTADAS
        # ============================================================
        lineas_unidas = linemerge(lineas)
        
        # ============================================================
        # 5.3. NORMALIZACIÓN DEL RESULTADO
        # ============================================================
        if lineas_unidas.geom_type == 'LineString':
            lineas_unidas = [lineas_unidas]
        
        elif lineas_unidas.geom_type == 'MultiLineString':
            lineas_unidas = list(lineas_unidas.geoms)
        
        else:
            lineas_unidas = lineas
        
        # ============================================================
        # 5.4. ALMACENAR RESULTADOS
        # ============================================================
        for linea in lineas_unidas:
            if linea and not linea.is_empty:
                resultados.append({
                    'geometry': linea,
                    'Elevation': elevacion
                })
    
    # ============================================================
    # 6. CREACIÓN DEL GEODATAFRAME DE SALIDA
    # ============================================================
    print("💾 Creando shapefile final...")
    
    gdf_resultado = gpd.GeoDataFrame(resultados, crs=gdf.crs)
    
    # ============================================================
    # 7. AÑADIR COORDENADAS Z (ELEVACIÓN)
    # ============================================================
    def add_z_coords(geom, z_value):
        """Convierte una línea 2D (X,Y) en 3D (X,Y,Z)"""
        if geom.geom_type == 'LineString':
            return type(geom)([(c[0], c[1], z_value) for c in geom.coords])
        return geom
    
    gdf_resultado['geometry'] = gdf_resultado.apply(
        lambda row: add_z_coords(row.geometry, row.Elevation), 
        axis=1
    )
    
    # ============================================================
    # 8. GUARDAR SHAPEFILE
    # ============================================================
    gdf_resultado.to_file(output_shp)
    
    # ============================================================
    # 9. REPORTE FINAL
    # ============================================================
    print(f"✅ Proceso terminado!")
    print(f"   Curvas originales: {len(gdf)}")
    print(f"   Curvas unidas: {len(gdf_resultado)}")
    print(f"   Reducción: {len(gdf) - len(gdf_resultado)} curvas ({((len(gdf) - len(gdf_resultado)) / len(gdf) * 100):.1f}%)")
    print(f"   Salida: {output_shp}")
    
    return gdf_resultado


# ============================================================
# EJECUCIÓN DEL SCRIPT
# ============================================================
if __name__ == "__main__":
    
    # Rutas de archivos
    input_shp = r"C:\argenis\_MDT\CURVAS\curva_nivel.shp"
    output_shp = r"C:\argenis\_MDT\CURVAS\curvas_unidas.shp"
    
    # Ejecutar la función
    unir_curvas_rapido(
        input_shp=input_shp,
        output_shp=output_shp,
        rango_z=0.1,               # ← CAMBIO: 0.1 para escala 1:10000 (100m)
        tolerancia_espacial=0.01
    )
