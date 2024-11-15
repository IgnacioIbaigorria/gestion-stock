from PyQt6.QtWidgets import QWidget, QToolTip, QMessageBox, QVBoxLayout, QHeaderView, QLabel, QDateEdit, QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout
from PyQt6.QtCore import QDate
from db import obtener_ventas_por_dia, obtener_ventas_por_periodo

class CajaTab(QWidget):
    def __init__(self):
        super().__init__()

        # Layout principal
        layout = QVBoxLayout()

        # Fecha para la recaudación diaria
        self.daily_revenue_label = QLabel("Recaudación del día:")
        self.daily_profit_label = QLabel("Ganancia del día:")
        self.daily_date = QDateEdit()
        self.daily_date.setDate(QDate.currentDate())
        self.daily_date.setCalendarPopup(True)
        
        self.daily_button = QPushButton("Calcular Recaudación Diaria")
        self.daily_button.clicked.connect(self.calcular_recaudacion_diaria)

        # Layout para la recaudación diaria
        daily_layout = QHBoxLayout()
        daily_layout.addWidget(self.daily_date)
        daily_layout.addWidget(self.daily_button)
        layout.addWidget(self.daily_revenue_label)
        layout.addWidget(self.daily_profit_label)
        layout.addLayout(daily_layout)

        # Fecha para la recaudación por período
        self.period_revenue_label = QLabel("Recaudación por período:")
        self.period_profit_label = QLabel("Ganancia por período:")
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate())
        self.start_date.setCalendarPopup(True)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        
        self.period_button = QPushButton("Calcular Recaudación por Período")
        self.period_button.clicked.connect(self.calcular_recaudacion_periodo)

        # Layout para la recaudación por período
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("Desde"))
        period_layout.addWidget(self.start_date)
        period_layout.addWidget(QLabel("Hasta"))
        period_layout.addWidget(self.end_date)
        period_layout.addWidget(self.period_button)
        layout.addWidget(self.period_revenue_label)
        layout.addWidget(self.period_profit_label)
        layout.addLayout(period_layout)

        # Tabla para mostrar el detalle de ventas
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Fecha", "Monto Total", "Método de Pago", "Detalle"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # Conectar la señal de clic para abrir el detalle en una ventana
        self.table.cellClicked.connect(self.mostrar_detalle_ventana)
        
        # Conectar el evento de pasar el cursor
        self.table.cellEntered.connect(self.mostrar_tooltip_detalle)
        
        self.setLayout(layout)

    def calcular_recaudacion_diaria(self):
        fecha = self.daily_date.date().toString("yyyy-MM-dd")
        ventas = obtener_ventas_por_dia(fecha)
        
        # Calcular la recaudación total y la ganancia total
        total = sum(venta[1] for venta in ventas)  # Suma de monto_total
        ganancia_total = sum(venta[4] for venta in ventas)  # Suma de ganancias
        self.daily_revenue_label.setText(f"Recaudación del día: ${total:.2f}")
        self.daily_profit_label.setText(f"Ganancia del día: ${ganancia_total:.2f}")
        
        # Mostrar las ventas en la tabla
        self.mostrar_ventas(ventas)

    def calcular_recaudacion_periodo(self):
        fecha_inicio = self.start_date.date().toString("yyyy-MM-dd")
        fecha_fin = self.end_date.date().toString("yyyy-MM-dd")
        ventas = obtener_ventas_por_periodo(fecha_inicio, fecha_fin)

        # Calcular la recaudación total y la ganancia total
        total = sum(venta[1] for venta in ventas)  # Suma de monto_total
        ganancia_total = sum(venta[4] for venta in ventas)  # Suma de ganancias
        self.period_revenue_label.setText(f"Recaudación por período: ${total:.2f}")
        self.period_profit_label.setText(f"Ganancia por período: ${ganancia_total:.2f}")
        
        # Mostrar las ventas en la tabla
        self.mostrar_ventas(ventas)

    def mostrar_ventas(self, ventas):
        self.table.setRowCount(0)
        for venta in ventas:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Desempaquetar la venta, incluyendo el detalle y ganancia
            fecha, monto_total, metodo_pago, detalle, ganancia = venta
            
            # Convertir el detalle en un texto para mostrar
            detalle_texto = "\n".join([f"{nombre} x {cantidad:.2f}kg" if isinstance(cantidad, float) and not cantidad.is_integer() else f"{nombre} x {int(cantidad)}" for nombre, cantidad, _, _ in detalle])
            
            # Insertar los datos en la tabla
            self.table.setItem(row, 0, QTableWidgetItem(str(fecha)))
            self.table.setItem(row, 1, QTableWidgetItem(f"${monto_total:.2f}"))
            self.table.setItem(row, 2, QTableWidgetItem(metodo_pago))
            self.table.setItem(row, 3, QTableWidgetItem(detalle_texto))

    def mostrar_tooltip_detalle(self, row, column):
        # Solo mostrar el tooltip si estamos en la columna de detalles
        if column == 3:
            item = self.table.item(row, column)
            if item:
                QToolTip.showText(self.table.viewport().mapToGlobal(self.table.visualItemRect(item).center()), item.text(), self.table)

    def mostrar_detalle_ventana(self, row, column):
        # Solo mostrar la ventana emergente si estamos en la columna de detalles
        if column == 3:
            item = self.table.item(row, column)
            if item:
                # Crear y mostrar una ventana emergente con el detalle completo
                mensaje = QMessageBox(self)
                mensaje.setWindowTitle("Detalle Completo")
                mensaje.setText(item.text())
                mensaje.exec()
