import sys
import uuid
import platform
import subprocess
import hashlib
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox, QTextEdit

def obtener_hardware_id():
    """Genera un ID de hardware único basado en múltiples componentes del sistema"""
    # Obtener información del sistema
    system_info = platform.uname()
    
    # Obtener número de serie del disco duro en Windows
    disk_serial = ""
    try:
        if platform.system() == "Windows":
            # Ejecutar comando para obtener información del disco
            output = subprocess.check_output("wmic diskdrive get SerialNumber", shell=True).decode().strip()
            lines = output.split('\n')
            if len(lines) >= 2:
                disk_serial = lines[1].strip()
    except:
        disk_serial = "unknown_disk"
    
    # Obtener CPU ID
    cpu_info = ""
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output("wmic cpu get ProcessorId", shell=True).decode().strip()
            lines = output.split('\n')
            if len(lines) >= 2:
                cpu_info = lines[1].strip()
    except:
        cpu_info = "unknown_cpu"
    
    # Obtener información de la placa base
    motherboard_info = ""
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output("wmic baseboard get SerialNumber", shell=True).decode().strip()
            lines = output.split('\n')
            if len(lines) >= 2:
                motherboard_info = lines[1].strip()
    except:
        motherboard_info = "unknown_motherboard"
    
    # Combinar toda la información
    hardware_components = [
        system_info.node,  # Nombre del equipo
        system_info.machine,  # Arquitectura
        disk_serial,
        cpu_info,
        motherboard_info,
        str(uuid.getnode())  # MAC address como respaldo
    ]
    
    # Crear un hash único a partir de los componentes
    fingerprint = hashlib.sha256(":".join(hardware_components).encode()).hexdigest()
    
    return fingerprint

def obtener_direccion_mac():
    """Obtiene la dirección MAC para compatibilidad con versiones anteriores"""
    mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)][::-1])
    return mac_address

class VentanaMAC(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Obtener ID de Hardware")
        self.layout = QVBoxLayout()

        # Obtener y mostrar el ID de hardware
        self.hardware_id = obtener_hardware_id()
        self.label_title = QLabel("ID de Hardware único para licencia:")
        self.layout.addWidget(self.label_title)
        
        # Usar QTextEdit para mostrar el ID completo
        self.text_id = QTextEdit()
        self.text_id.setPlainText(self.hardware_id)
        self.text_id.setReadOnly(True)
        self.text_id.setMaximumHeight(60)
        self.layout.addWidget(self.text_id)
        
        # Mostrar también la MAC para referencia
        self.direccion_mac = obtener_direccion_mac()
        self.label_mac = QLabel(f"Dirección MAC actual (puede cambiar): {self.direccion_mac}")
        self.layout.addWidget(self.label_mac)

        # Botón para copiar
        self.boton_copiar = QPushButton("Copiar ID de Hardware al portapapeles")
        self.boton_copiar.clicked.connect(self.copiar_al_portapapeles)
        self.layout.addWidget(self.boton_copiar)

        self.setLayout(self.layout)
        self.resize(500, 200)

    def copiar_al_portapapeles(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.hardware_id)
        QMessageBox.information(self, "Copiado", "El ID de Hardware ha sido copiado al portapapeles.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VentanaMAC()
    ventana.show()
    sys.exit(app.exec())