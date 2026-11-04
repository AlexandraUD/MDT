import arcpy
from arcpy.sa import *
arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Spatial")

hillshade = Raster(r'C:\argenis\_MDT\LAGRANJA_SANTAND\LAGRANJA\LAGRANJA.gdb\HillSha_MDT_53')
umbral_min = 80
umbral_max = 230
min_pixeles = 9

sombra = Con((hillshade < umbral_min) | (hillshade > umbral_max), 1)
grupos = RegionGroup(sombra, 'FOUR', 'WITHIN', 'ADD_LINK')
sombra_filtrada = Con(grupos, 1, '', 'COUNT > ' + str(min_pixeles))

arcpy.conversion.RasterToPolygon(
    sombra_filtrada,
    r'C:\argenis\_MDT\LAGRANJA_SANTAND\19_La_Granja_1K_(Santander)\OP\sombras.shp',
    'SIMPLIFY',
    'Value'
)
print("Listo")