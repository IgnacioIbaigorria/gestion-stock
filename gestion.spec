# -*- mode: python ; coding: utf-8 -*-
import os
import site
import sys
from PyInstaller.utils.hooks import collect_dynamic_libs
from PyInstaller.utils.hooks import collect_data_files
barcode_datas = collect_data_files('barcode')

block_cipher = None

base_dir = os.path.abspath(os.getcwd())

# Find site-packages directory
site_packages = site.getsitepackages()[0]

# Collect USB backend DLLs
usb_dlls = []
try:
    # Try to find libusb DLLs
    libusb_path = os.path.join(site_packages, 'usb', 'backend')
    if os.path.exists(libusb_path):
        for file in os.listdir(libusb_path):
            if file.endswith('.dll'):
                full_path = os.path.join(libusb_path, file)
                usb_dlls.append((full_path, '.'))
except Exception as e:
    print(f"Warning: Could not find USB DLLs: {e}")

# Add any additional DLLs needed
additional_binaries = []
additional_binaries.extend(usb_dlls)

a = Analysis(['main.py'],
    pathex=[],
    binaries=additional_binaries,  # Add the USB DLLs here
    datas = [
        ('styles.qss', '.'),
        ('client_secrets.json', '.'),
        ('mycreds.txt', '.'),
        ('lisintac.png', '.'),
        ('spinner.gif', '.'),
        ('config_postgres.py', '.'),
        (os.path.abspath('fonts') + '\\*', 'fonts'),  # Absolute path with wildcard
        ('fonts/ARIAL.TTF', 'fonts'),
        ('fonts/ARIALBD.TTF', 'fonts'),
        ('fonts/arial.TTF', 'fonts'),
        ('fonts/arialbd.TTF', 'fonts')
    ] + barcode_datas,
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'signals',
        'datetime',
        'sqlite3',
        'pywin32',
        'sys',
        'os',
        'styles',
        'reportlab',
        'reportlab.lib',
        'reportlab.pdfgen',
        'reportlab.lib.pagesizes',
        'reportlab.lib.utils',
        'date',
        'PyQt6.QtWidgets',
        'productos_tab',
        'ventas_tab',
        'caja_tab',
        'clientes_tab',
        'logica_codigo',
        'config',
        'logging',
        'db',
        'sync',
        'backup',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'barcode',
        'barcode.writer',
        'win32print',
        'win32api',
        'qrcode',
        'serial',
        'modificaciones',
        'login_window',
        'usuarios_tab',
        'dateutil',
        'win32timezone',
        'modificaciones_tab',
        'etiquetas_tab',
        'psycopg2',
        'psycopg2.pool',
        'pytz',
        'hashlib',
        'functools',
        'cachetools',
        'contextlib',
        'db_postgres',
        'config_postgres'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Liss Sin Tacc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='stock.ico'  # Reemplaza con la ruta a tu archivo .ico
)