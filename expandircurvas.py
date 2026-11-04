# -*- coding: utf-8 -*-
import arcpy
import os
import math

def expand_lines(input_fc, extension_distance, limite_fc, output_folder):
    # Rutas de salida
    temp_output_fc = os.path.join(output_folder, "tmp_curvas_expandidas.shp")
    recortado_fc = os.path.join(output_folder, "curva_nivel3.shp")
    final_merge_fc = os.path.join(output_folder, "polilineas_expandidas.shp")
    
    # Referencia espacial
    spatial_ref = arcpy.Describe(input_fc).spatialReference
    
    # Crear archivo temporal para curvas extendidas
    arcpy.CreateFeatureclass_management(output_folder, os.path.basename(temp_output_fc), "POLYLINE",
                                        input_fc, "ENABLED", "ENABLED", spatial_ref)
    
    # Copiar campos
    input_fields = [f.name for f in arcpy.ListFields(input_fc) if f.type not in ("OID", "Geometry")]
    existing_fields = [f.name for f in arcpy.ListFields(temp_output_fc)]
    fields_to_add = [(f, "TEXT") for f in input_fields if f not in existing_fields]
    
    if fields_to_add:
        arcpy.AddFields_management(temp_output_fc, fields_to_add)
    
    # Extender extremos
    with arcpy.da.SearchCursor(input_fc, ["SHAPE@"] + input_fields) as cursor_in, \
         arcpy.da.InsertCursor(temp_output_fc, ["SHAPE@"] + input_fields) as cursor_out:
        for row in cursor_in:
            geom = row[0]
            points = list(geom.getPart(0))
            
            if len(points) < 2:
                continue
            
            # Extremo inicial
            p0, p1 = points[0], points[1]
            dx_i, dy_i, dz_i = p1.X - p0.X, p1.Y - p0.Y, p1.Z - p0.Z
            length_i = math.sqrt(dx_i**2 + dy_i**2 + dz_i**2)
            
            if length_i == 0:
                continue
            
            ux_i, uy_i, uz_i = dx_i/length_i, dy_i/length_i, dz_i/length_i
            new_start = arcpy.Point(p0.X - ux_i * extension_distance,
                                    p0.Y - uy_i * extension_distance,
                                    p0.Z - uz_i * extension_distance)
            
            # Extremo final
            p_last, p_before_last = points[-1], points[-2]
            dx_f, dy_f, dz_f = p_last.X - p_before_last.X, p_last.Y - p_before_last.Y, p_last.Z - p_before_last.Z
            length_f = math.sqrt(dx_f**2 + dy_f**2 + dz_f**2)
            
            if length_f == 0:
                continue
            
            ux_f, uy_f, uz_f = dx_f/length_f, dy_f/length_f, dz_f/length_f
            new_end = arcpy.Point(p_last.X + ux_f * extension_distance,
                                  p_last.Y + uy_f * extension_distance,
                                  p_last.Z + uz_f * extension_distance)
            
            new_points = [new_start] + points + [new_end]
            array = arcpy.Array(new_points)
            new_polyline = arcpy.Polyline(array, spatial_ref, True)
            cursor_out.insertRow([new_polyline] + list(row[1:]))
    
    print("✅ Expansión completada.")
    
    # Recorte con Eraser
    if arcpy.Exists(limite_fc):
        arcpy.Erase_analysis(temp_output_fc, limite_fc, recortado_fc)
        arcpy.Delete_management(temp_output_fc)
        print("✅ Recorte fuera del límite completado.")
    else:
        print("⚠️ No se encontró la capa de límite.")
        return
    
    # Unión con capa original
    arcpy.Merge_management([input_fc, recortado_fc], final_merge_fc)
    print(f"✅ Polilíneas expandidas generadas en: {final_merge_fc}")

if __name__ == "__main__":

    extension_distance = 2
    
    input_fc = r"C:\argenis\_MDT\ELVARAL_BOLIVAR\23_El_Varal_1K_(Bolívar)\OP\curvas_unidas.shp"

    limite_fc = r"C:\argenis\_MDT\ELVARAL_BOLIVAR\23_El_Varal_1K_(Bolívar)\LIMITE\LIMITE_EL_VARAL_1K_13667016.shp"

    output_folder = r"C:\argenis\_MDT\ELVARAL_BOLIVAR\23_El_Varal_1K_(Bolívar)\OP\\"
    
    expand_lines(input_fc, extension_distance, limite_fc, output_folder)




