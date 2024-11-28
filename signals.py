# signals.py
from PyQt6.QtCore import QObject, pyqtSignal

class EventSignals(QObject):
    venta_realizada = pyqtSignal()
    cliente_agregado = pyqtSignal()  # Señal para notificar que un cliente fue agregado

# Instancia global para manejar señales
signals = EventSignals()
