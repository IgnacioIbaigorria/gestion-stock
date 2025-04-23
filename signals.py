# signals.py
from PyQt6.QtCore import QObject, pyqtSignal

class EventSignals(QObject):
    venta_realizada = pyqtSignal()
    cliente_agregado = pyqtSignal()  # Señal para notificar que un cliente fue agregado
    producto_actualizado = pyqtSignal()  # Señal para notificar que un producto fue actualizado
    actualizar_modificaciones = pyqtSignal()
# Instancia global para manejar señales
signals = EventSignals()
