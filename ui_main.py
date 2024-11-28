import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout

from productos_tab import ProductosTab
from ventas_tab import VentasTab
from caja_tab import CajaTab
from clientes_tab import ClientesTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Stock")
        self.setGeometry(100, 100, 800, 600)

        # Configuración de pestañas
        self.tabs = QTabWidget()
        
        # Agregar pestañas individuales
        self.tabs.addTab(ProductosTab(), "Productos")
        self.tabs.addTab(VentasTab(), "Ventas")
        self.tabs.addTab(CajaTab(), "Caja")
        self.tabs.addTab(ClientesTab(), "Clientes")

        self.setCentralWidget(self.tabs)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())
