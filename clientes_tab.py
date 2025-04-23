from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QScrollArea, QComboBox, QMessageBox,
    QHeaderView, QSpacerItem, QSizePolicy, QDialog, QAbstractItemView

)
from PyQt6.QtCore import Qt
from datetime import datetime
from db_postgres import (
    agregar_cliente_a_db, obtener_clientes, obtener_detalle_ventas_deudas,
    obtener_deudas_cliente, obtener_pagos_cliente, registrar_pago_cliente
)
from signals import signals

class DetalleDeudaDialog(QDialog):
    def __init__(self, deuda, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detalle de Deuda")
        self.setGeometry(100, 100, 400, 300)

        layout = QVBoxLayout()

        # Mostrar información de la deuda
        layout.addWidget(QLabel(f"Fecha: {deuda['fecha']}"))
        layout.addWidget(QLabel(f"Total: ${deuda['monto_total']:.2f}"))
        layout.addWidget(QLabel(f"Pagado: ${deuda['monto_pagado']:.2f}"))
        layout.addWidget(QLabel(f"Deuda: ${deuda['monto']:.2f}"))
        layout.addWidget(QLabel(f"Detalle: {deuda['detalle']}"))
        close_button = QPushButton("Cerrar")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
                
        self.setLayout(layout)
                
class ClientesTab(QWidget):
    def __init__(self):
        super().__init__()

        # Layout principal
        main_layout = QVBoxLayout()

        # Sección: Agregar Cliente con layout horizontal
        add_client_layout = QVBoxLayout()
        add_client_layout.addWidget(QLabel("<b>Agregar Cliente</b>"))

        # Crear un layout horizontal para el input y el botón
        input_button_layout = QHBoxLayout()
        
        # Input del cliente
        self.client_name_input = QLineEdit()
        self.client_name_input.setPlaceholderText("Nombre del cliente")
        input_button_layout.addWidget(self.client_name_input)

        # Contenedor para el botón
        btn_container = QWidget()
        btn_container.setObjectName("contenedorBotonCliente")
        btn_container_layout = QHBoxLayout()
        btn_container_layout.setContentsMargins(0, 0, 0, 0)

        # Botón de agregar
        self.add_client_button = QPushButton("+ Nuevo Cliente")
        self.add_client_button.setObjectName("agregarClienteCompacto")
        self.add_client_button.clicked.connect(self.agregar_cliente)
        btn_container_layout.addWidget(self.add_client_button)
        
        btn_container.setLayout(btn_container_layout)
        input_button_layout.addWidget(btn_container)

        # Agregar el layout horizontal al layout principal
        add_client_layout.addLayout(input_button_layout)
        main_layout.addLayout(add_client_layout)
        main_layout.addSpacing(10)

        # Sección: Seleccionar Cliente
        client_selection_layout = QHBoxLayout()
        client_selection_layout.addWidget(QLabel("<b>Seleccionar Cliente:</b>"))
        signals.cliente_agregado.connect(self.cargar_clientes)


        self.client_selector = QComboBox()
        self.client_selector.currentIndexChanged.connect(self.cargar_datos_cliente)
        client_selection_layout.addWidget(self.client_selector)

        main_layout.addLayout(client_selection_layout)
        main_layout.addSpacing(10)

        # Sección: Información de Deudas y Pagos
        info_layout = QVBoxLayout()

        # Etiqueta de deuda total
        self.total_debt_label = QLabel("Deuda Total: $0.00")
        self.total_debt_label.setStyleSheet("font-weight: bold; color: red;")
        self.total_debt_label.hide()
        info_layout.addWidget(self.total_debt_label)

        # Registro de pago
        payment_layout = QHBoxLayout()
        self.client_pay_input = QLineEdit()
        self.client_pay_input.setPlaceholderText("Ingrese el pago")
        self.client_pay_input.hide()
        payment_layout.addWidget(self.client_pay_input)

        self.register_pay_button = QPushButton("Registrar Pago")
        self.register_pay_button.setObjectName("registrarPago")
        self.register_pay_button.clicked.connect(self.registrar_pago)
        self.register_pay_button.hide()
        payment_layout.addWidget(self.register_pay_button)

        info_layout.addLayout(payment_layout)
        main_layout.addLayout(info_layout)
        main_layout.addSpacing(10)

        # Área de tablas: Deudas y Pagos
        tables_layout = QHBoxLayout()

        # Tabla de deudas
        debt_layout = QVBoxLayout()
        debt_layout.addWidget(QLabel("<b>Deudas del Cliente</b>"))
        self.debt_table = QTableWidget(0, 5)
        self.debt_table.setHorizontalHeaderLabels(["Fecha", "Total", "Pagado", "Deuda", "Detalle"])
        self.debt_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.debt_table.verticalHeader().setVisible(False)
        self.debt_table.setAlternatingRowColors(True)
        self.debt_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.debt_table.cellDoubleClicked.connect(self.mostrar_detalle_deuda)
        debt_layout.addWidget(self.debt_table)

        tables_layout.addLayout(debt_layout)

        # Tabla de pagos
        payment_layout = QVBoxLayout()
        payment_layout.addWidget(QLabel("<b>Pagos Realizados</b>"))
        self.payment_table = QTableWidget(0, 2)
        self.payment_table.verticalHeader().setVisible(False)
        self.payment_table.setHorizontalHeaderLabels(["Fecha", "Monto"])
        self.payment_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.payment_table.setAlternatingRowColors(True)
        self.payment_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        payment_layout.addWidget(self.payment_table)

        tables_layout.addLayout(payment_layout)
        main_layout.addLayout(tables_layout)

        # Espaciado final
        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        main_layout.addSpacerItem(spacer)

        # Configuración final
        self.setLayout(main_layout)

        # Cargar datos iniciales
        self.cargar_clientes()
        
    def mostrar_detalle_deuda(self, row, column):
        """Muestra el detalle de la deuda seleccionada en una nueva ventana."""
        if row < 0:  # Verifica que la fila sea válida
            return

        # Obtener la deuda seleccionada
        deuda = {
            "fecha": self.debt_table.item(row, 0).text(),
            "monto_total": float(self.debt_table.item(row, 1).text().replace('$', '').replace(',', '')),
            "monto_pagado": float(self.debt_table.item(row, 2).text().replace('$', '').replace(',', '')),
            "monto": float(self.debt_table.item(row, 3).text().replace('$', '').replace(',', '')),
            "detalle": self.debt_table.item(row, 4).text()
        }

        # Aquí deberías buscar el detalle real de la deuda en tu estructura de datos
        # Por ejemplo, podrías tener una lista de resultados que contenga todas las deudas
        # y buscar la deuda correspondiente por algún identificador.

        # Abre la ventana de detalle
        dialog = DetalleDeudaDialog(deuda, self)
        dialog.exec()  # Cambiar exec_() por exec()            
            
    def agregar_cliente(self):
        """Agrega un cliente a la base de datos."""
        nombre_cliente = self.client_name_input.text().strip()
        if not nombre_cliente:
            QMessageBox.warning(self, "Error", "El nombre del cliente no puede estar vacío.")
            return

        exito = agregar_cliente_a_db(nombre_cliente)
        if exito:
            QMessageBox.information(self, "Éxito", f"Cliente '{nombre_cliente}' agregado correctamente.")
            self.client_name_input.clear()
            self.cargar_clientes()
        else:
            QMessageBox.warning(self, "Error", "No se pudo agregar el cliente.")

    def cargar_clientes(self):
        """Carga la lista de clientes desde la base de datos."""
        clientes = obtener_clientes()
        self.client_selector.clear()
        self.client_selector.addItem("-- Seleccione un cliente --")
        for cliente in clientes:
            self.client_selector.addItem(cliente["nombre"], cliente["id"])

    def cargar_datos_cliente(self):
        """Carga las deudas y pagos del cliente seleccionado."""
        cliente_id = self.client_selector.currentData()
        if cliente_id is None:
            self.debt_table.setRowCount(0)
            self.payment_table.setRowCount(0)
            self.total_debt_label.setText("Deuda Total: $0.00")
            self.total_debt_label.hide()
            self.client_pay_input.hide()
            self.register_pay_button.hide()
            return

        deudas = obtener_detalle_ventas_deudas(cliente_id)
        pagos = obtener_pagos_cliente(cliente_id)

        # Calcular deuda total
        total_deuda = sum(deuda["monto"] for deuda in deudas)
        total_pagado = sum(pago["monto"] for pago in pagos if pago["venta_id"] in [deuda["venta_id"] for deuda in deudas])  # Filtrar pagos
        total_ventas = sum(deuda["monto_total"] for deuda in deudas)
        deuda_restante = total_ventas - total_pagado  # Calcular deuda restante

        self.total_debt_label.setText(f"Deuda Total: ${total_ventas:.2f}, Pagado: ${total_pagado:.2f}, Deuda Restante: ${deuda_restante:.2f}")
        self.total_debt_label.show()
        self.client_pay_input.show()
        self.register_pay_button.show()

        # Mostrar deudas en la tabla
        self.debt_table.setRowCount(len(deudas))
        for row, deuda in enumerate(deudas):
            self.debt_table.setItem(row, 0, QTableWidgetItem(deuda["fecha"]))
            self.debt_table.setItem(row, 3, QTableWidgetItem(f"${deuda['monto']:.2f}"))
            self.debt_table.setItem(row, 1, QTableWidgetItem(f"${deuda['monto_total']:.2f}"))  # Monto total
            self.debt_table.setItem(row, 2, QTableWidgetItem(f"${deuda['monto_pagado']:.2f}"))  # Monto pagado

            # Convertir la lista de detalles en un string
            detalles_str = ", ".join([f"{detalle['nombre']} (x{detalle['cantidad']})" for detalle in deuda["detalle"]])
            self.debt_table.setItem(row, 4, QTableWidgetItem(detalles_str))  # Detalles de la venta

        # Mostrar pagos en la tabla
        self.payment_table.setRowCount(len(pagos))
        for row, pago in enumerate(pagos):
            self.payment_table.setItem(row, 0, QTableWidgetItem(pago["fecha"]))
            self.payment_table.setItem(row, 1, QTableWidgetItem(f"${pago['monto']:.2f}"))


    def registrar_pago(self):
        """Registra un pago para el cliente seleccionado."""
        cliente_id = self.client_selector.currentData()
        if cliente_id is None:
            QMessageBox.warning(self, "Error", "Debe seleccionar un cliente para registrar el pago.")
            return

        try:
            monto = float(self.client_pay_input.text())
            if monto <= 0:
                raise ValueError("El monto debe ser mayor que 0.")
        except ValueError as e:
            QMessageBox.warning(self, "Error", f"Monto inválido: {e}")
            return

        # Verificar la deuda total actual
        deudas = obtener_deudas_cliente(cliente_id)
        total_deuda = sum(deuda["monto"] for deuda in deudas)

        if total_deuda == 0:
            QMessageBox.information(self, "Sin deudas", "El cliente no tiene deudas pendientes.")
            return

        if monto > total_deuda:
            # Ajustar el monto al total de la deuda si es mayor
            QMessageBox.information(
                self, 
                "Aviso", 
                f"El monto ingresado excede la deuda total. Se ajustará el pago a ${total_deuda:.2f}."
            )
            monto = total_deuda

        # Registrar el pago con el monto ajustado
        exito = registrar_pago_cliente(cliente_id, monto)
        if exito:
            QMessageBox.information(self, "Éxito", "Pago registrado correctamente.")
            self.client_pay_input.clear()
            self.cargar_datos_cliente()  # Recargar datos del cliente (deudas y pagos actualizados)
        else:
            QMessageBox.warning(self, "Error", "No se pudo registrar el pago.")
