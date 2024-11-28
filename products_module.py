from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QSpinBox, QPushButton, QTableWidget, QHBoxLayout, QCompleter, QDoubleSpinBox, QHeaderView, QMessageBox
from PyQt6.QtCore import Qt
from database import connect_db


class ProductsTab(QWidget):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.c = conn.cursor()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.name_input = QLineEdit()
        self.quantity_input = QSpinBox()
        # Configurar widgets y layouts
        form_layout = QHBoxLayout()

        # Campo de entrada para el Código de Barras
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Código de Barras")
        self.barcode_input.textChanged.connect(self.auto_fill_product_name)
        form_layout.addWidget(self.barcode_input)

        # Campo de entrada para el Nombre del Producto
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nombre del Producto")
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.name_input.setCompleter(self.completer)
        self.name_input.textChanged.connect(self.auto_fill_product_details)
        self.name_input.textChanged.connect(self.filter_products)
        form_layout.addWidget(self.name_input)

        # Campo de entrada para la Cantidad
        self.quantity_input = QSpinBox()
        self.quantity_input.setMinimum(0)
        self.quantity_input.setMaximum(10000)
        self.quantity_input.setPrefix("Cantidad: ")
        form_layout.addWidget(self.quantity_input)

        # Campo de entrada para el Precio de Costo
        self.cost_price_input = QDoubleSpinBox()
        self.cost_price_input.setMinimum(0.0)
        self.cost_price_input.setMaximum(99999.0)
        self.cost_price_input.setPrefix("Costo: $")
        self.cost_price_input.valueChanged.connect(self.update_final_price)
        form_layout.addWidget(self.cost_price_input)

        # Campo de entrada para el Margen de Ganancia
        self.profit_margin_input = QDoubleSpinBox()
        self.profit_margin_input.setMinimum(0.0)
        self.profit_margin_input.setMaximum(100.0)
        self.profit_margin_input.setPrefix("Margen de Ganancia: %")
        self.profit_margin_input.valueChanged.connect(self.update_final_price)
        form_layout.addWidget(self.profit_margin_input)

        # Campo de entrada para el Precio de Venta
        self.price_input = QDoubleSpinBox()
        self.price_input.setMinimum(0.0)
        self.price_input.setMaximum(99999.0)
        self.price_input.setPrefix("Venta: $")
        self.price_input.valueChanged.connect(self.update_profit_margin)
        form_layout.addWidget(self.price_input)

        # Botones de Producto
        button_layout = QHBoxLayout()
        add_button = QPushButton("AGREGAR/ACTUALIZAR PRODUCTO")
        add_button.clicked.connect(self.add_product)
        button_layout.addWidget(add_button)

        delete_button = QPushButton("ELIMINAR PRODUCTO")
        delete_button.clicked.connect(self.delete_product)
        button_layout.addWidget(delete_button)

        # Tabla de Productos
        self.product_table = QTableWidget()
        self.product_table.setColumnCount(6)  # Incluye 6 columnas: Código de Barras, Nombre, Cantidad, Precio de Costo, Margen de Ganancia, Precio de Venta
        self.product_table.setHorizontalHeaderLabels(['Código de Barras', 'Nombre', 'Cantidad', 'Costo', 'Margen de Ganancia', 'Precio de Venta'])
        self.product_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.product_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.product_table.cellClicked.connect(self.load_product_to_form)

        # Organizar los layouts
        layout.addLayout(form_layout)
        layout.addLayout(button_layout)
        layout.addWidget(self.product_table)
        layout.addWidget(self.name_input)
        layout.addWidget(self.quantity_input)
        self.setLayout(layout)

    def add_product(self):
        barcode = self.barcode_input.text().strip()  # Captura el código de barras
        name = self.name_input.text().strip()
        quantity = self.quantity_input.value()
        cost_price = self.cost_price_input.value()
        profit_margin = self.profit_margin_input.value()
        price = self.price_input.value()

        # Validar que los campos no estén vacíos o tengan valores inválidos
        if name and quantity >= 0 and cost_price >= 0 and price >= 0:
            # Busca si el producto ya existe
            c.execute("SELECT id FROM products WHERE name=?", (name,))
            result = c.fetchone()

            if result:
                # Si el producto ya existe, obtenemos su ID
                product_id = result[0]

                # Si el código de barras es diferente, verificar si el nuevo código de barras ya existe
                if barcode:
                    c.execute("SELECT id FROM products WHERE barcode=? AND id != ?", (barcode, product_id))
                    if c.fetchone():
                        QMessageBox.warning(self, "Error", "Ya existe otro producto con este código de barras.")
                        return

                # Actualiza el producto
                c.execute(
                    "UPDATE products SET barcode=?, name=?, quantity=?, cost_price=?, profit_margin=?, price=? WHERE id=?",
                    (barcode, name, quantity, cost_price, profit_margin, price, product_id)
                )
                QMessageBox.information(self, "Éxito", "Producto actualizado")
                self.clear_entries()  # Limpia los campos de entrada
            else:
                # Si el producto no existe, agrégalo
                c.execute(
                    "INSERT INTO products (name, quantity, cost_price, profit_margin, price, barcode) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, quantity, cost_price, profit_margin, price, barcode)
                )
                QMessageBox.information(self, "Éxito", "Producto agregado")
                self.clear_entries()  # Limpia los campos de entrada

            conn.commit()
            self.load_products()  # Actualiza la lista de productos en la interfaz
            self.update_completer()  # Actualiza el autocompletar
            self.clear_entries()  # Limpia los campos de entrada

        else:
            QMessageBox.critical(self, "Error", "Todos los campos son requeridos")

    def delete_product(self):
        # Lógica para eliminar producto
        pass
