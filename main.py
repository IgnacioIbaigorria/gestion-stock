import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget
from PyQt6.QtCore import QFile, QTextStream
from productos_tab import ProductosTab
from ventas_tab import VentasTab
from caja_tab import CajaTab
from clientes_tab import ClientesTab
from db import crear_tablas  # Asegurarnos de que las tablas estén creadas

def cargar_estilos(app):
    archivo_qss = QFile("styles.qss")
    if archivo_qss.open(QFile.OpenModeFlag.ReadOnly):  # Cambiado a OpenModeFlag.ReadOnly
        stream = QTextStream(archivo_qss)
        app.setStyleSheet(stream.readAll())
    else:
        print("No se pudo cargar el archivo QSS")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Kiosco")
        self.setGeometry(100, 100, 800, 600)

        # Crear y configurar las pestañas
        self.tabs = QTabWidget()
        self.tabs.addTab(ProductosTab(), "Productos")
        self.tabs.addTab(VentasTab(), "Ventas")
        self.tabs.addTab(CajaTab(), "Caja")
        self.tabs.addTab(ClientesTab(), "Clientes")

        # Establecer el widget central
        self.setCentralWidget(self.tabs)
        
    def cargar_estilos():
        archivo_qss = QFile("styles.qss")
        if archivo_qss.open(QFile.OpenModeFlag.ReadOnly):
            stream = QTextStream(archivo_qss)
            app.setStyleSheet(stream.readAll())
        else:
            print("No se pudo cargar el archivo QSS")


if __name__ == "__main__":
    # Crear tablas en la base de datos si no existen
    crear_tablas()
    
    # Ejecutar la aplicación
    app = QApplication(sys.argv)
    cargar_estilos(app)
    main_window = MainWindow()
    main_window.showMaximized()  # Mostrar maximizado
    sys.exit(app.exec())
