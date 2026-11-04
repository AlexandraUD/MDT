import geopandas as gpd
import pandas as pd
from shapely.ops import linemerge
from shapely.geometry import MultiLineString
import numpy as np

def unir_curvas_rapido(input_shp, output_shp, rango_z=0.01, tolerancia_espacial=0.01):
    """
    Une curvas de nivel fragmentadas de forma eficiente.
    
    Parameters:
    - input_shp: ruta del shapefile de entrada
    - output_shp: ruta del shapefile de salida
    - rango_z: tolerancia para agrupar elevaciones (metros)
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
    # - gdf.geometry.notna() → Elimina filas donde geometry = None
    # - ~gdf.geometry.is_empty → Elimina geometrías vacías (EMPTY)
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
    # Verificar que existe el campo 'Elevation' en la tabla de atributos
    if 'Elevation' not in gdf.columns:
        raise ValueError(f"La capa debe tener campo 'Elevation'. Campos disponibles: {list(gdf.columns)}")
    
    # ============================================================
    # 3. CONVERSIÓN DE SISTEMA DE COORDENADAS
    # ============================================================
    # Si está en coordenadas geográficas (lat/lon), convertir a proyectadas (metros)
    # Esto es necesario para que las operaciones espaciales sean precisas
    if gdf.crs.is_geographic:
        print("⚠️ Convirtiendo a proyectadas para cálculos precisos...")
        gdf = gdf.to_crs(gdf.estimate_utm_crs())  # Estima la zona UTM apropiada
    
    # ============================================================
    # 4. AGRUPACIÓN POR ELEVACIÓN
    # ============================================================
    print("🔢 Agrupando por elevación...")
    
    # Redondear elevaciones según rango_z para agrupar curvas similares
    # Ejemplo: si rango_z=0.1, curvas de 110.05 y 110.08 se agrupan como 110.1
    # np.round(110.05 / 0.1) * 0.1 = round(1100.5) * 0.1 = 1100 * 0.1 = 110.0
    gdf['elev_grupo'] = np.round(gdf['Elevation'] / rango_z) * rango_z
    
    # Lista para almacenar las curvas procesadas
    resultados = []
    
    # ============================================================
    # 5. PROCESAMIENTO POR GRUPO DE ELEVACIÓN
    # ============================================================
    # Agrupar todas las curvas que tienen la misma elevación (o similar según rango_z)
    grupos = gdf.groupby('elev_grupo')
    total_grupos = len(grupos)
    
    # Procesar cada grupo (ej: todas las curvas de 110m juntas)
    for idx, (elevacion, grupo) in enumerate(grupos, 1):
        print(f"⚙️ Procesando elevación {elevacion:.2f}m ({idx}/{total_grupos})...")
        
        # ============================================================
        # 5.1. DESCOMPOSICIÓN DE GEOMETRÍAS MULTIPARTE
        # ============================================================
        # Convertir todas las geometrías a LineString simples
        # Algunas pueden ser MultiLineString (varias líneas en un solo registro)
        lineas = []
        
        for geom in grupo.geometry:
            # Doble verificación: saltar geometrías nulas o vacías
            if geom is None or geom.is_empty:
                continue
            
            # Si es una línea simple, añadirla directamente
            if geom.geom_type == 'LineString':
                lineas.append(geom)
            
            # Si es multilínea, descomponerla en líneas individuales
            elif geom.geom_type == 'MultiLineString':
                # geom.geoms devuelve las partes individuales del MultiLineString
                lineas.extend(list(geom.geoms))
        
        # Si no hay líneas válidas en este grupo, pasar al siguiente
        if not lineas:
            continue
        
        # ============================================================
        # 5.2. UNIÓN DE LÍNEAS CONECTADAS
        # ============================================================
        # linemerge() une automáticamente las líneas que comparten vértices
        # Ejemplo: si línea1 termina en (100,200) y línea2 empieza en (100,200),
        # las une en una sola línea continua
        lineas_unidas = linemerge(lineas)
        
        # ============================================================
        # 5.3. NORMALIZACIÓN DEL RESULTADO
        # ============================================================
        # linemerge() puede devolver:
        # - LineString (si todas se unieron en una sola)
        # - MultiLineString (si hay varias curvas separadas con la misma elevación)
        # - Lista de geometrías (en casos especiales)
        
        if lineas_unidas.geom_type == 'LineString':
            # Caso 1: Todas las líneas se unieron en una sola
            lineas_unidas = [lineas_unidas]
        
        elif lineas_unidas.geom_type == 'MultiLineString':
            # Caso 2: Hay varias curvas separadas (ej: curva 110 en 3 cerros diferentes)
            lineas_unidas = list(lineas_unidas.geoms)
        
        else:
            # Caso 3: No se pudo unir nada, mantener las originales
            lineas_unidas = lineas
        
        # ============================================================
        # 5.4. ALMACENAR RESULTADOS
        # ============================================================
        # Crear un registro para cada curva resultante
        for linea in lineas_unidas:
            # Validar que la línea no esté vacía
            if linea and not linea.is_empty:
                resultados.append({
                    'geometry': linea,          # La geometría de la curva
                    'Elevation': elevacion      # Su elevación
                })
    
    # ============================================================
    # 6. CREACIÓN DEL GEODATAFRAME DE SALIDA
    # ============================================================
    print("💾 Creando shapefile final...")
    
    # Convertir la lista de resultados en un GeoDataFrame
    # Mantiene el mismo sistema de coordenadas que la entrada
    gdf_resultado = gpd.GeoDataFrame(resultados, crs=gdf.crs)
    
    # ============================================================
    # 7. AÑADIR COORDENADAS Z (ELEVACIÓN)
    # ============================================================
    # Función para añadir el valor Z a cada vértice de la línea
    def add_z_coords(geom, z_value):
        """
        Convierte una línea 2D (X,Y) en 3D (X,Y,Z)
        """
        if geom.geom_type == 'LineString':
            # Para cada coordenada (que puede ser 2D o 3D):
            # - c[0] = coordenada X
            # - c[1] = coordenada Y
            # - z_value = nueva coordenada Z (elevación)
            return type(geom)([(c[0], c[1], z_value) for c in geom.coords])
        return geom
    
    # Aplicar la función a todas las geometrías
    # axis=1 significa "aplicar por fila"
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

    input_shp = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\PRO\2_SHAPES_EDICION\curva_nivel2.shp"

    output_shp = r"C:\argenis\_MDT\BARRANCO_BOL\44_Barranco_de_Loba_1K_(Bolívar)\OP\curvas_unidas.shp"
    
    # Ejecutar la función
    unir_curvas_rapido(
        input_shp=input_shp,
        output_shp=output_shp,
        rango_z=0.01,              # Tolerancia de elevación en metros
        tolerancia_espacial=0.01   # Parámetro reservado para futuras mejoras
    )
