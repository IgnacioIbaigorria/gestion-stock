from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QHeaderView, QScrollArea, QToolTip, QVBoxLayout, QLineEdit, QPushButton, QLabel, QHBoxLayout, QTableWidget, QTableWidgetItem, QComboBox, QMessageBox)
from PyQt6.QtCore import QDate
from signals import signals
from db import agregar_cliente_a_db, obtener_clientes, obtener_detalle_ventas_deudas, obtener_deudas_cliente, obtener_pagos_cliente, registrar_pago_cliente

class ClientesTab(QWidget):
    def __init__(self):
        super().__init__()

        # Layout principal
        layout = QVBoxLayout()

        # Formulario para agregar cliente
        form_layout = QVBoxLayout()
        form_layout.addWidget(QLabel("Agregar cliente"))

        self.client_name_input = QLineEdit()
        self.client_name_input.setPlaceholderText("Nombre del cliente")
        form_layout.addWidget(self.client_name_input)

        self.add_client_button = QPushButton("Agregar Cliente")
        self.add_client_button.setObjectName("clienteButton")
        self.add_client_button.clicked.connect(self.agregar_cliente)
        form_layout.addWidget(self.add_client_button)

        layout.addLayout(form_layout)

        # Selector de clientes
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Seleccionar Cliente:"))
        self.client_selector = QComboBox()
        self.client_selector.currentIndexChanged.connect(self.mostrar_deuda_cliente)
        self.client_selector.currentIndexChanged.connect(self.cargar_datos_cliente)
        selector_layout.addWidget(self.client_selector)

        layout.addLayout(selector_layout)
        
        # Etiqueta para mostrar la deuda total
        deuda_pago_layout = QHBoxLayout()
        self.total_debt_label = QLabel("Deuda Total: $0.00")
        self.total_debt_label.setStyleSheet("font-weight: bold; color: red;")
        self.total_debt_label.hide()  # Ocultar inicialmente
        deuda_pago_layout.addWidget(self.total_debt_label)
        
        self.client_pay_input = QLineEdit()
        self.client_pay_input.setPlaceholderText("Ingrese el pago")
        self.client_pay_input.hide()
        deuda_pago_layout.addWidget(self.client_pay_input)
        
        layout.addLayout(deuda_pago_layout)

        self.register_pay_button = QPushButton("Registrar pago")
        self.register_pay_button.setObjectName("pagoButton")
        self.register_pay_button.clicked.connect(self.registrar_pago)
        self.register_pay_button.hide()
        layout.addWidget(self.register_pay_button)



        # Crear un área desplazable para las tablas
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)  # Ajustar contenido al tamaño disponible

        # Widget contenedor dentro del área desplazable
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Tabla de deudas
        scroll_layout.addWidget(QLabel("Deudas del Cliente:"))
        self.debt_table = QTableWidget(0, 3)
        self.debt_table.setHorizontalHeaderLabels(["Fecha", "Monto", "Detalle"])
        self.debt_table.horizontalHeader().setStretchLastSection(True)
        self.debt_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        scroll_layout.addWidget(self.debt_table)
        
        self.debt_table.cellClicked.connect(self.mostrar_detalle_ventana)
        self.debt_table.cellEntered.connect(self.mostrar_tooltip_detalle)

        # Tabla de pagos
        scroll_layout.addWidget(QLabel("Pagos del Cliente:"))
        self.payment_table = QTableWidget(0, 2)
        self.payment_table.setHorizontalHeaderLabels(["Fecha", "Monto"])
        self.payment_table.horizontalHeader().setStretchLastSection(True)
        self.payment_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        scroll_layout.addWidget(self.payment_table)

        # Configurar el área desplazable
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        # Configuración final
        self.setLayout(layout)

        # Cargar datos iniciales
        self.cargar_clientes()

    def agregar_cliente(self):
        """Agrega un cliente a la base de datos."""
        nombre_cliente = self.client_name_input.text().strip()
        if not nombre_cliente:
            QMessageBox.warning(self, "Error", "El nombre del cliente no puede estar vacío.")
            return

        # Lógica para insertar cliente en la base de datos
        exito = agregar_cliente_a_db(nombre_cliente)
        if exito:
            QMessageBox.information(self, "Éxito", f"Cliente '{nombre_cliente}' agregado correctamente.")
            self.client_name_input.clear()
            self.cargar_clientes()  # Recargar lista de clientes
            signals.cliente_agregado.emit()  # Emitir la señal

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
        """Carga las deudas y pagos del cliente seleccionado y actualiza la deuda total."""
        cliente_id = self.client_selector.currentData()
        if cliente_id is None:
            self.debt_table.setRowCount(0)
            self.payment_table.setRowCount(0)
            self.total_debt_label
            self.total_debt_label.setText("Deuda Total: $0.00")
            return

        # Obtener deudas con detalles de ventas
        deudas = obtener_detalle_ventas_deudas(cliente_id)
        pagos = obtener_pagos_cliente(cliente_id)

        # Calcular deuda total
        total_deuda = sum(deuda["monto"] for deuda in deudas)
        total_pagos = sum(pago["monto"] for pago in pagos)
        deuda_final = total_deuda - total_pagos

        # Actualizar etiqueta de deuda total
        self.total_debt_label.setText(f"Deuda Total: ${deuda_final:.2f}")

        # Mostrar deudas en la tabla
        self.debt_table.setRowCount(len(deudas))
        for row, deuda in enumerate(deudas):
            fecha_formateada = datetime.strptime(deuda["fecha"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            # Convertir el detalle en un texto para mostrar
            detalle_texto = "\n".join([
                f"{item['nombre']} - {item['cantidad']:.2f}kg x ${item['precio_unitario']}/kg" if isinstance(item['cantidad'], float) and not item['cantidad'].is_integer() 
                else f"{item['nombre']} - {int(item['cantidad'])} x ${item['precio_unitario']}" 
                for item in deuda["detalle"]
            ])

            # Insertar datos en la tabla
            self.debt_table.setItem(row, 0, QTableWidgetItem(fecha_formateada))
            self.debt_table.setItem(row, 1, QTableWidgetItem(f"${deuda['monto']:.2f}"))
            self.debt_table.setItem(row, 2, QTableWidgetItem(detalle_texto))

        # Mostrar pagos en la tabla
        self.payment_table.setRowCount(len(pagos))
        for row, pago in enumerate(pagos):
            fecha_formateada = datetime.strptime(pago["fecha"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            self.payment_table.setItem(row, 0, QTableWidgetItem(fecha_formateada))
            self.payment_table.setItem(row, 1, QTableWidgetItem(f"${pago['monto']:.2f}"))
            
            
    def mostrar_tooltip_detalle(self, row, column):
        # Solo mostrar el tooltip si estamos en la columna de detalles
        if column == 3:
            item = self.table.item(row, column)
            if item:
                QToolTip.showText(self.debt_table.viewport().mapToGlobal(self.debt_table.visualItemRect(item).center()), item.text(), self.debt_table)

    def mostrar_detalle_ventana(self, row, column):
        # Solo mostrar la ventana emergente si estamos en la columna de detalles
        if column == 2:
            item = self.debt_table.item(row, column)
            if item:
                # Crear y mostrar una ventana emergente con el detalle completo
                mensaje = QMessageBox(self)
                mensaje.setWindowTitle("Detalle Completo")
                mensaje.setText(item.text())
                mensaje.exec()

    def mostrar_deuda_cliente(self):
        """Muestra u oculta el selector de cliente según el método de pago."""
        if self.client_selector.currentText() != "-- Seleccione un cliente --":
            self.total_debt_label.show()
            self.client_pay_input.show()
            self.register_pay_button.show()
        else:
            self.total_debt_label.hide()
            self.client_pay_input.hide()
            self.register_pay_button.hide()

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

        # Obtener la deuda total actual
        deudas = obtener_deudas_cliente(cliente_id)
        pagos = obtener_pagos_cliente(cliente_id)
        deuda_total = sum(deuda["monto"] for deuda in deudas) - sum(pago["monto"] for pago in pagos)
        print(deuda_total)

        if monto > deuda_total:
            # Ajustar el monto al total de la deuda si es mayor
            QMessageBox.information(
                self, 
                "Aviso", 
                f"El monto ingresado excede la deuda total. Se ajustará el pago a ${deuda_total:.2f}."
            )
            monto = deuda_total

        # Registrar el pago con el monto ajustado
        exito = registrar_pago_cliente(cliente_id, monto)
        if exito:
            QMessageBox.information(self, "Éxito", "Pago registrado correctamente.")
            self.client_pay_input.clear()
            self.cargar_datos_cliente()  # Recargar datos del cliente (deudas y pagos actualizados)
        else:
            QMessageBox.warning(self, "Error", "No se pudo registrar el pago.")
