"""
Script para copiar y procesar datos desde dos archivos Excel (.xls)
y pegarlos en un archivo destino (.xlsx) según la nueva estructura.
Edita los parámetros abajo antes de ejecutar.
"""
import xlrd
import openpyxl
import os
import re
import shutil

# ============= CAMBIAR ESTOS PARÁMETROS =============
 
archivo_destino = r"C:\argenis\_MDT\Verificacion_de_la_Precision_MDT1_52405006_20230620.xlsx"
 
ruta_origen = r"C:\argenis\_MDT\SINCERIN_BOL\43_Sincerín_(Bolívar)\PRO\4_CONTROL_CALIDAD\EXCEL"
 
valor_f5 = "MDT1_13052004_20260410"  # Nombre Modelo
 
valor_f6 = "1:1000"       # Escala
 
valor_f7 = "Sincerín"   # Proyecto/Contrato
 
valor_f8 = "Arjona"  # Municipio
 
valor_f9 = "Bolívar"  # Departamento
 
valor_r3 = "21/10/2026"   # Fecha
 
valor_s47 = "0,3"       # Valor_Z
# ====================================================

def script_tool(archivo_destino, ruta_origen, valor_f5, valor_f6, valor_f7, valor_f8, valor_f9, valor_r3, valor_s47):
    archivo_origen_1 = os.path.join(ruta_origen, "puntos_CC_reporte.xls")
    archivo_origen_2 = os.path.join(ruta_origen, "puntos_CC_reporte_modelo.xls")

    # Validar archivos
    if not os.path.exists(archivo_origen_1):
        print(f"❌ No existe: {archivo_origen_1}")
        return
    if not os.path.exists(archivo_origen_2):
        print(f"❌ No existe: {archivo_origen_2}")
        return
    if not os.path.exists(archivo_destino):
        print(f"❌ No existe: {archivo_destino}")
        return

    # Abrir archivos origen y destino
    wb_origen = xlrd.open_workbook(archivo_origen_1)
    hoja_origen = wb_origen.sheet_by_index(0)
    wb_destino = openpyxl.load_workbook(archivo_destino)
    hoja_destino = wb_destino.active

    def col_letra_a_indice(letra):
        return openpyxl.utils.column_index_from_string(letra) - 1

    # Detectar número de filas de datos en archivo origen (omite filas vacías)
    filas_datos = 0
    for i in range(1, hoja_origen.nrows):
        if str(hoja_origen.cell_value(i, 0)).strip() != "":
            filas_datos += 1
        else:
            break

    fila_base = 13  # En destino los datos comienzan en fila 13
    print(f"📊 Filas de datos detectadas: {filas_datos}")

    # PARTE 1: Copiar columnas desde archivo .xls al .xlsx
    copias = [
        ("F", 1, "Q"),  # No. Punto
        ("E", 1, "R"),  # Coordenada Este Terreno
        ("H", 1, "E"),  # Coordenada Norte Terreno
        ("G", 1, "F"),  # Coordenada Este Lectura modelo
        ("J", 1, "G"),  # Coordenada Norte Lectura modelo
        ("I", 1, "H"),  # Dif E
    ]

    for col_o, fila_o, col_d in copias:
        col_index_o = col_letra_a_indice(col_o)
        for i in range(filas_datos):
            valor = hoja_origen.cell_value(fila_o + i, col_index_o)
            try:
                valor = float(valor)
            except:
                valor = str(valor).strip()
            hoja_destino[f"{col_d}{fila_base + i}"] = valor
    print("✓ Columnas copiadas")

    # PARTE 2: Procesar archivo_origen_2 y pegar pares consecutivos en columna C
    libro2 = xlrd.open_workbook(archivo_origen_2)
    hoja2 = libro2.sheet_by_index(0)

    clasificaciones = {i: [] for i in range(1, filas_datos + 1)}
    for row in range(1, hoja2.nrows):
        try:
            d_val = int(float(hoja2.cell_value(row, 3)))  # Columna D
            k_val = str(hoja2.cell_value(row, 10)).strip()  # Columna K
            if d_val in clasificaciones:
                clasificaciones[d_val].append(k_val)
        except:
            continue

    def extraer_sufijo(valor):
        match = re.search(r"-(\d{4})", valor)
        return int(match.group(1)) if match else None

    for i in range(1, filas_datos + 1):
        valores = clasificaciones[i]
        pares = []
        for val1 in valores:
            suf1 = extraer_sufijo(val1)
            if suf1 is None:
                continue
            for val2 in valores:
                if val1 == val2:
                    continue
                suf2 = extraer_sufijo(val2)
                if suf2 is None:
                    continue
                if suf2 == suf1 + 1:
                    base_match = re.match(r"^(.*)-\d{4}-?\d{0,4}-?\d?$", val1)
                    base = base_match.group(1) if base_match else val1[:-5]
                    par = f"{base}-{str(suf1).zfill(4)}-{str(suf2).zfill(4)}"
                    if par not in pares:
                        pares.append(par)
        hoja_destino[f"C{fila_base + i - 1}"] = pares[1] if len(pares) >= 2 else (pares[0] if pares else "SIN DATOS")
    print("✓ Clasificaciones procesadas")

    # PARTE 3: Insertar valores adicionales en celdas
    hoja_destino["F5"] = valor_f5       # Modelo
    hoja_destino["F6"] = valor_f6       # Escala
    hoja_destino["F7"] = valor_f7       # Proyecto contrato
    hoja_destino["F8"] = valor_f8       # Municipio
    hoja_destino["F9"] = valor_f9       # Departamento
    hoja_destino["R3"] = valor_r3       # Fecha
    hoja_destino["S47"] = valor_s47     # Valor_Z (nuevo)
    print("✓ Parámetros insertados")

    # Guardar archivo modificado
    wb_destino.save(archivo_destino)
    print(f"✓ Archivo guardado: {archivo_destino}")

    # PARTE 4: Renombrar archivo y copiar a carpeta origen
    nombre_original = os.path.basename(archivo_destino)
    nombre_sin_ext, ext = os.path.splitext(nombre_original)
    n = len(valor_f5)
    nuevo_nombre_sin_ext = valor_f5 if n > len(nombre_sin_ext) else nombre_sin_ext[:-n] + valor_f5
    ruta_nueva = os.path.join(ruta_origen, nuevo_nombre_sin_ext + ext)
    shutil.copyfile(archivo_destino, ruta_nueva)
    print(f"✓ Archivo copiado como: {ruta_nueva}")
    print("✅ Proceso completado")

if __name__ == "__main__":
    script_tool(archivo_destino, ruta_origen, valor_f5, valor_f6, valor_f7, valor_f8, valor_f9, valor_r3, valor_s47)