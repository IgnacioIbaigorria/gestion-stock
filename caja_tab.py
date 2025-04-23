from PyQt6.QtWidgets import QWidget, QDialog, QToolTip, QAbstractItemView, QMessageBox, QVBoxLayout, QHeaderView, QLabel, QDateEdit, QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout, QLineEdit
from PyQt6.QtCore import QDate, Qt, QTimer
from PyQt6.QtGui import QMovie  # Add this import
from datetime import date, datetime
from db_postgres import obtener_total_ventas_efectivo, obtener_ventas_por_dia, obtener_ventas_por_periodo

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Create semi-transparent background
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.7);
                border-radius: 10px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Create loading spinner
        self.spinner_label = QLabel()
        self.spinner_movie = QMovie("spinner.gif")
        self.spinner_label.setMovie(self.spinner_movie)
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Add loading text
        self.text_label = QLabel("Cargando...")
        self.text_label.setStyleSheet("""
            QLabel {
                color: #333;
                font-size: 16px;
                background-color: transparent;
            }
        """)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.spinner_label)
        layout.addWidget(self.text_label)
        self.hide()

    def showEvent(self, event):
        # Position overlay over the table
        if self.parent():
            self.setGeometry(self.parent().geometry())
        self.spinner_movie.start()

    def hideEvent(self, event):
        self.spinner_movie.stop()
        
class CajaTab(QWidget):
    def __init__(self):
        super().__init__()
        self.loading = LoadingOverlay(self)

        # Layout principal
        layout = QVBoxLayout()

        # Fecha para la recaudación diaria
        self.daily_revenue_label = QLabel("Recaudación del día:")
        self.daily_profit_label = QLabel("Ganancia del día:")
        self.daily_date = QDateEdit()
        self.daily_date.setDate(QDate.currentDate())
        self.daily_date.setCalendarPopup(True)
        
        self.daily_button = QPushButton("Calcular Recaudación Diaria")
        self.daily_button.setObjectName("botonRecaudacionDiaria")
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
        self.start_date.setDate(date.today().replace(day=1))
        self.start_date.setCalendarPopup(True)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        
        self.period_button = QPushButton("Calcular Recaudación por Período")
        self.period_button.setObjectName("botonRecaudacionPeriodo")
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
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.loading = LoadingOverlay(self.table)
        layout.addWidget(self.table)

        # Conectar la señal de clic para abrir el detalle en una ventana
        self.table.cellClicked.connect(self.mostrar_detalle_ventana)
        
        # Conectar el evento de pasar el cursor
        self.table.cellEntered.connect(self.mostrar_tooltip_detalle)
        
        self.setLayout(layout)

    def calcular_recaudacion_diaria(self):
        self.loading.show()
        self.table.setRowCount(0)  # Clear table
        self.daily_revenue_label.setText("Recaudación del día: Cargando...")
        self.daily_profit_label.setText("Ganancia del día: Cargando...")
        
        # Use QTimer to allow the UI to update before processing
        QTimer.singleShot(100, self._procesar_recaudacion_diaria)

    def _procesar_recaudacion_diaria(self):
        fecha = self.daily_date.date().toString("yyyy-MM-dd")
        ventas = obtener_ventas_por_dia(fecha)
        
        total_ventas = sum(venta[1] for venta in ventas)
        ganancia_total = sum(venta[4] for venta in ventas)
        total_efectivo = obtener_total_ventas_efectivo(fecha)

        self.daily_revenue_label.setText(f"Recaudación del día: ${total_ventas:.2f}")
        self.daily_profit_label.setText(f"Ganancia del día: ${ganancia_total:.2f}")
        self.period_revenue_label.setText(f"Recaudación por período: ")
        self.period_profit_label.setText(f"Ganancia por período: ")
        
        self.mostrar_ventas(ventas)
        self.loading.hide()

    def calcular_recaudacion_periodo(self):
        self.loading.show()
        self.table.setRowCount(0)  # Clear table
        self.period_revenue_label.setText("Recaudación por período: Cargando...")
        self.period_profit_label.setText("Ganancia por período: Cargando...")
        
        # Use QTimer to allow the UI to update before processing
        QTimer.singleShot(100, self._procesar_recaudacion_periodo)

    def _procesar_recaudacion_periodo(self):
        fecha_inicio = self.start_date.date().toString("yyyy-MM-dd")
        fecha_fin = self.end_date.date().toString("yyyy-MM-dd")
        ventas = obtener_ventas_por_periodo(fecha_inicio, fecha_fin)

        total = sum(venta[1] for venta in ventas)
        ganancia_total = sum(venta[4] for venta in ventas)
        
        self.period_revenue_label.setText(f"Recaudación por período: ${total:.2f}")
        self.period_profit_label.setText(f"Ganancia por período: ${ganancia_total:.2f}")
        self.daily_revenue_label.setText(f"Recaudación del día: ")
        self.daily_profit_label.setText(f"Ganancia del día: ")

        self.mostrar_ventas(ventas)
        self.loading.hide()
        
    def mostrar_ventas(self, ventas):
        self.table.setRowCount(0)
        for venta in ventas:
            row = self.table.rowCount()
            self.table.insertRow(row)

            fecha, monto_total, metodo_pago, detalle, ganancia = venta

            if not detalle:
                # Si no hay detalles, mostrar un mensaje o continuar
                detalle_texto = "Sin detalles disponibles"
            else:
                # Procesar los detalles de la venta
                detalle_texto = "\n".join([
                    f"{nombre} - {cantidad:.2f}kg x ${precio_venta}/kg" if isinstance(cantidad, float) and not cantidad.is_integer() 
                    else f"{nombre} - {(cantidad)} x ${precio_venta}"
                    for nombre, cantidad, _, precio_venta in detalle
                ])

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

