from PyQt6 import Qt

def keyPressEvent(self, event):
    if event.key() == Qt.Key.Key_Return:
        # Verificar si hay un elemento seleccionado en el completer
        if self.completer.popup().isVisible():
            # Si el popup del completer está visible, no hacer nada
            return
        else:
            # Si no hay un popup visible, agregar el producto
            term = self.product_input.text().strip()
            if term:
                self.agregar_producto()