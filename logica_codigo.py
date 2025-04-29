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
import traceback
from barcode.writer import ImageWriter
import csv
import subprocess
import os
import sys
import tempfile
import win32api
import win32print
from PIL import ImageFont

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def generar_codigo_variable_ean13(product_code: str, weight_kg: float) -> str:
    """Genera un código EAN-13 variable..."""
    
    print(f"\n[DEBUG] Iniciando generación de código para: {product_code}, peso: {weight_kg}kg")
    
    # Font debugging
    print("[DEBUG] Buscando fuentes en las siguientes rutas:")
    possible_paths = [
        os.path.join(os.environ['WINDIR'], 'Fonts', 'arial.ttf'),  # Windows
        resource_path('fonts/ARIAL.TTF'),  # PyInstaller
        resource_path('fonts/arial.ttf'),  # PyInstaller
        os.path.join(os.path.dirname(__file__), 'fonts', 'ARIAL.TTF')  # Desarrollo
    ]
    
    font_path = None
    for i, path in enumerate(possible_paths, 1):
        exists = os.path.exists(path)
        print(f"  {i}. {path} → {'EXISTE' if exists else 'NO EXISTE'}")
        if exists and not font_path:
            font_path = path
            print(f"  ¡Fuente seleccionada: {path}!")

    if not font_path:
        print("[ERROR] No se encontró ninguna fuente válida en las rutas especificadas")
        raise FileNotFoundError("No se pudo encontrar ninguna fuente válida")

    print(f"[DEBUG] Intentando cargar fuente desde: {font_path}")
    print(f"[DEBUG] Permisos de archivo: Lectura → {'SI' if os.access(font_path, os.R_OK) else 'NO'}")

    try:
        font = ImageFont.truetype(font_path, size=12)
        print("[DEBUG] Fuente cargada exitosamente")
        
        # Add explicit font file verification for PyInstaller
        print(f"[DEBUG] Información de fuente cargada:")
        print(f" - Font path: {font.path}")
        print(f" - Font size: {font.size}")
        
        # Add manual font path validation for PyInstaller environment
        if hasattr(sys, '_MEIPASS'):
            print("[DEBUG] Modo PyInstaller detectado - verificando acceso a fuente")
            normalized_path = os.path.normpath(font_path)
            print(f"[DEBUG] Ruta normalizada: {normalized_path}")
            
            if not os.access(normalized_path, os.R_OK):
                raise OSError(f"PyInstaller no pudo empaquetar la fuente correctamente. Ruta inaccesible: {normalized_path}")

    except Exception as e:
        print(f"[ERROR] Fallo al cargar fuente: {str(e)}")
        print("[DEBUG] Usando fuente predeterminada")
        font = ImageFont.load_default()

    # Barcode generation debugging
    try:
        weight_g = int(weight_kg * 1000)
        weight_str = str(weight_g).zfill(5)
        product_code_padded = product_code.zfill(5)
        raw_code_12 = "2" + "0" + product_code_padded + weight_str
        
        print(f"[DEBUG] Código bruto generado: {raw_code_12}")
        print(f"[DEBUG] Longitud código: {len(raw_code_12)} caracteres")

        options = {
            'font_path': font_path,
            'font_size': 12,
            'text_distance': 2.0,
            'background': 'white',
            'foreground': 'black',
            'dpi': 300
        }
        writer = ImageWriter()
        writer.set_options(options)
        
        print("[DEBUG] Creando objeto EAN13")
        ean = barcode.get('ean13', raw_code_12, writer=writer)
        
        temp_dir = tempfile.gettempdir()
        
        output_path = os.path.join(temp_dir, f"EAN_{product_code_padded}_{weight_str}")

        ean.save(output_path)
        
        return ean.get_fullcode()
        
    except Exception as e:
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
            r"C:\Users\Usuario\AppData\Local\SumatraPDF\SumatraPDF.exe",
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