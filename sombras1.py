import arcpy
from arcpy.sa import *
arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Spatial")

hillshade = Raster(r'C:\argenis\_MDT\SOCRRO_SANT\SOCORRO\SOCORRO.gdb\HillSha_MDT_251')

min_pixeles = 3
umbral_diferencia = 30  # ajustar según resultados

media_vecinos = FocalStatistics(hillshade, NbrRectangle(12, 12, 'CELL'), 'MEAN')
diferencia = hillshade - media_vecinos
anomalias = Con((diferencia > umbral_diferencia) | (diferencia < -umbral_diferencia), 1)

grupos = RegionGroup(anomalias, 'FOUR', 'WITHIN', 'ADD_LINK')
anomalias_filtradas = Con(grupos, 1, '', 'COUNT > ' + str(min_pixeles))

arcpy.conversion.RasterToPolygon(
    anomalias_filtradas,

    r'C:\argenis\_MDT\SOCRRO_SANT\21_Socorro_1K_(Santander)\OP\anomalias.shp',

    'SIMPLIFY',
    'Value'
)
print("Listo")