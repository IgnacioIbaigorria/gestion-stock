# setup.py
import sys, os, site, shutil
from cx_Freeze import setup, Executable

# Regular setup continues
site_packages = site.getsitepackages()[0]
usb_dlls = []
libusb_path = os.path.join(site_packages, 'usb', 'backend')
if os.path.isdir(libusb_path):
    for f in os.listdir(libusb_path):
        if f.lower().endswith('.dll'):
            usb_dlls.append((os.path.join(libusb_path, f), f))

# Simplified include_files
include_files = [
    'styles.qss',
    *[(f, f) for f in os.listdir('.') if f.endswith('.db')],
    'client_secrets.json',
    'mycreds.txt',
    'lisintac.png',
    'spinner.gif',
    'config_postgres.py',
    ('fonts', 'fonts'),
] + usb_dlls

# Simplified build options
build_exe_options = {
    "packages": [
        "os", "sys", "PyQt6", "PIL", "reportlab", 
        "qrcode", "serial", "cachetools", 
        "dateutil", "pytz",
    ],
    "excludes": ["tkinter", "unittest"],
    "include_files": include_files,
    "include_msvcr": True,
    "build_exe": "dist",
}

# Executable definition
base = "Win32GUI" if sys.platform=="win32" else None
executables = [
    Executable("main.py",
               base=base,
               icon="stock.ico",
               target_name="Liss Sin Tacc.exe")
]

setup(
    name="Liss Sin Tacc",
    version="1.0",
    description="Aplicación Dietética",
    options={"build_exe": build_exe_options},
    executables=executables
)