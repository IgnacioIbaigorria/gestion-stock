#!/usr/bin/env python3
"""
Script para generar de forma automática un código de barras EAN-13 variable,
crear el archivo CSV con los datos de la etiqueta y llamar a BarTender para imprimirla.

Requisitos:
    - Instalar las librerías: python-barcode y pillow
      pip install python-barcode pillow
    - Contar con BarTender instalado (y ajustar la ruta al ejecutable).
"""

import barcode
from barcode.writer import ImageWriter
import csv
import subprocess
import os
import tempfile
import win32api
import win32print

def generar_codigo_variable_ean13(product_code: str, weight_kg: float) -> str:
    """
    Genera un código EAN-13 variable que codifica el ID del producto y su peso.
    """
    # Convertir el peso a gramos y formatear a 5 dígitos (por ejemplo: 1.25 kg → "01250")
    weight_g = int(weight_kg * 1000)
    weight_str = str(weight_g).zfill(5)
    
    # Asegurar que el código del producto tenga 5 dígitos (rellenando con ceros a la izquierda si es necesario)
    product_code_padded = product_code.zfill(5)
    
    # Construir la cadena base de 12 dígitos
    raw_code_12 = "2" + "0" + product_code_padded + weight_str
    
    # Generar el EAN-13; la librería calcula el dígito de control automáticamente.
    try:
        ean = barcode.get('ean13', raw_code_12, writer=ImageWriter())
        final_code = ean.get_fullcode()
        
        # Usar un directorio temporal para guardar la imagen
        import tempfile
        temp_dir = tempfile.gettempdir()
        
        # Asegurarse de que el directorio temporal existe
        os.makedirs(temp_dir, exist_ok=True)
        
        # Guardar con extensión .png explícita
        output_path = os.path.join(temp_dir, f"EAN_{product_code_padded}_{weight_str}")
        ean.save(output_path)
        
        print(f"Código de barras generado y guardado en: {output_path}.png")
        return final_code
    except Exception as e:
        print(f"Error al generar código de barras: {e}")
        raise

def generar_csv_etiqueta(datos: dict, ruta_csv: str):
    """
    Genera un archivo CSV con los datos para la etiqueta.
    
    Parámetros:
      - datos: Diccionario con claves: Codigo, Nombre, Ingredientes, CodigoBarras, Peso.
      - ruta_csv: Ruta y nombre del archivo CSV a generar.
    """
    # Asegurarse de que todos los valores sean strings
    datos_str = {k: str(v) for k, v in datos.items()}
    
    # Imprimir los datos para depuración
    print("Datos a escribir en CSV:")
    for k, v in datos_str.items():
        print(f"  {k}: {v}")
    
    fieldnames = ["Codigo", "Nombre", "Ingredientes", "CodigoBarras", "Peso"]
    
    try:
        with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(datos_str)
        print(f"CSV generado exitosamente en: {ruta_csv}")
        
        # Verificar el contenido del archivo generado
        with open(ruta_csv, "r", encoding="utf-8") as f:
            contenido = f.read()
            print(f"Contenido del CSV generado:\n{contenido}")
            
    except Exception as e:
        print(f"Error al generar CSV: {e}")
        import traceback
        print(traceback.format_exc())
        raise

def imprimir_etiqueta(ruta_plantilla: str, ruta_csv: str) -> bool:
    """
    Llama a BarTender para imprimir la etiqueta.
    
    Parámetros:
      - ruta_plantilla: Ruta completa al archivo .btw de BarTender.
      - ruta_csv: Ruta completa al archivo CSV con los datos.
      
    Retorna:
      - True si la impresión fue exitosa, False en caso contrario.
    """
    try:
        # Ruta al ejecutable de BarTender (ajustar según la instalación)
        bartender_exe = r"C:\Program Files\Seagull\BarTender Suite\bartend.exe"
        
        # Verificar que el ejecutable existe
        if not os.path.exists(bartender_exe):
            print(f"Error: No se encontró BarTender en {bartender_exe}")
            return False
            
        # Verificar que los archivos existen
        if not os.path.exists(ruta_plantilla):
            print(f"Error: No se encontró la plantilla en {ruta_plantilla}")
            return False
            
        if not os.path.exists(ruta_csv):
            print(f"Error: No se encontró el archivo CSV en {ruta_csv}")
            return False
            
        # Comando para imprimir con BarTender
        # /P: Imprimir
        # /F: Especificar el formato (plantilla)
        # /D: Especificar la base de datos (CSV)
        # /C: Cerrar BarTender después de imprimir
        comando = [
            bartender_exe,
            "/P",
            "/F", ruta_plantilla,
            "/D", ruta_csv,
            "/C"
        ]
        
        print(f"Ejecutando comando: {' '.join(comando)}")
        
        # Ejecutar el comando
        proceso = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proceso.communicate()
        
        # Verificar si hubo errores
        if proceso.returncode != 0:
            print(f"Error al imprimir: {stderr.decode('utf-8', errors='ignore')}")
            return False
            
        print("Impresión enviada correctamente")
        return True
        
    except Exception as e:
        import traceback
        print(f"Error al imprimir etiqueta: {e}")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    # Datos de prueba para la etiqueta (simula los datos que podrías obtener de tu DB)
    product_code = "12345"        # Este es el código base del producto que guardas en la DB
    product_name = "Manzana Golden"
    ingredients = "100% manzana"
    weight_kg = 1.25              # Peso en kilogramos obtenido (por ejemplo, del escaneo o balanza)
    
    # 1. Generar el código de barras EAN-13 variable en base al código y el peso.
    codigo_barras = generar_codigo_variable_ean13(product_code, weight_kg)
    print("Código EAN-13 generado:", codigo_barras)
    
    # 2. Reunir los datos para la etiqueta.
    datos_producto = {
        "Codigo": product_code,
        "Nombre": product_name,
        "Ingredientes": ingredients,
        "CodigoBarras": codigo_barras,
        "Peso": str(weight_kg)
    }
    
    # 3. Generar el archivo CSV para la etiqueta.
    # Se genera en el directorio actual; puedes modificar la ruta si lo requieres.
    ruta_csv = os.path.join(os.getcwd(), "datos_etiqueta.csv")
    generar_csv_etiqueta(datos_producto, ruta_csv)
    
    # 4. Definir la ruta de la plantilla de BarTender (.btw).
    # Cambia esta ruta a la ubicación real de tu plantilla.
    ruta_template = r"C:\ruta\etiqueta.btw"
    
    # 5. Llamar a BarTender para imprimir la etiqueta.
    imprimir_etiqueta(ruta_template, ruta_csv)

def imprimir_pdf_directo(ruta_pdf, impresora=None):
    """
    Imprime un archivo PDF directamente a una impresora específica.
    
    Parámetros:
      - ruta_pdf: Ruta completa al archivo PDF a imprimir.
      - impresora: Nombre de la impresora a utilizar. Si es None, usa la impresora predeterminada.
      
    Retorna:
      - True si la impresión fue exitosa, False en caso contrario.
    """
    try:
        # Verificar que el archivo existe
        if not os.path.exists(ruta_pdf):
            print(f"Error: No se encontró el archivo PDF en {ruta_pdf}")
            return False
        
        # Intentar usar SumatraPDF primero (más confiable para PDF)
        sumatra_paths = [
            r"C:\Users\ignac\AppData\Local\SumatraPDF\SumatraPDF.exe",
            r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
            os.path.join(os.getcwd(), "SumatraPDF.exe")
        ]
        
        sumatra_exists = False
        sumatra_path = None
        
        for path in sumatra_paths:
            if os.path.exists(path):
                sumatra_exists = True
                sumatra_path = path
                break
        
        if sumatra_exists:
            print(f"SumatraPDF encontrado en: {sumatra_path}")
            
            # Construir el comando para SumatraPDF
            if impresora:
                comando = [
                    sumatra_path,
                    "-print-to", impresora,
                    "-print-settings", "fit",
                    ruta_pdf
                ]
            else:
                comando = [
                    sumatra_path,
                    "-print-to-default",
                    "-print-settings", "fit",
                    ruta_pdf
                ]
            
            print(f"Ejecutando comando: {' '.join(comando)}")
            
            # Ejecutar el comando
            proceso = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proceso.communicate()
            
            # Verificar si hubo errores
            if proceso.returncode != 0:
                print(f"Error al imprimir con SumatraPDF: {stderr.decode('utf-8', errors='ignore')}")
                print("Intentando método alternativo...")
            else:
                print("Impresión enviada correctamente con SumatraPDF")
                return True
        else:
            print("SumatraPDF no encontrado, usando método alternativo de impresión")
        
        # Método alternativo: usar la API de Windows directamente
        try:
            # Si no se especificó impresora, usar la predeterminada
            if not impresora:
                impresora = win32print.GetDefaultPrinter()
            
            print(f"Imprimiendo directamente a: {impresora}")
            
            # Configurar la impresora
            hPrinter = win32print.OpenPrinter(impresora)
            try:
                # Imprimir el archivo
                win32api.ShellExecute(
                    0, 
                    "print", 
                    ruta_pdf,
                    f'"{impresora}"', 
                    ".", 
                    0
                )
                print(f"Impresión enviada a {impresora} usando ShellExecute")
                return True
            finally:
                win32print.ClosePrinter(hPrinter)
        except Exception as e:
            print(f"Error al imprimir con API de Windows: {e}")
            
            # Último recurso: usar el comando de impresión de Windows
            try:
                comando = f'cmd /c start /wait /b print /d:"{impresora}" "{ruta_pdf}"'
                print(f"Ejecutando comando: {comando}")
                
                proceso = subprocess.run(comando, shell=True, check=True)
                print("Impresión enviada correctamente con comando de Windows")
                return True
            except subprocess.CalledProcessError as e:
                print(f"Error al imprimir con comando de Windows: {e}")
                return False
    
    except Exception as e:
        import traceback
        print(f"Error al imprimir PDF directamente: {e}")
        print(traceback.format_exc())
        return False