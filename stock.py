import sys
import os
from tkinter import messagebox
import tkinter as tk

import traceback
import uuid
import win32api
import json
from PyQt6.QtWidgets import (QApplication, QComboBox, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel,
                             QTableWidget, QDialog, QTableWidgetItem, QStyleFactory, QHeaderView, QMessageBox, QSpinBox, QDoubleSpinBox, QDateEdit, QCompleter, QTabWidget)
from PyQt6.QtCore import Qt, QDate, QStringListModel
from PyQt6.QtGui import QFont, QIcon
import sqlite3
import datetime
from datetime import date
from reportlab.lib.pagesizes import mm
from reportlab.pdfgen import canvas
from datetime import datetime


# Conexión a la base de datos
conn = sqlite3.connect('stock_management.db')
c = conn.cursor()


c.execute('''CREATE TABLE IF NOT EXISTS products
          (id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            quantity INTEGER NOT NULL,
            cost_price REAL NOT NULL,
            profit_margin REAL NOT NULL,
            price REAL NOT NULL,
            barcode TEXT NOT NULL
                        )''')
# Crear tabla de ventas si no existe
c.execute('''
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        quantity INTEGER NOT NULL,
        total REAL NOT NULL,
        date TEXT NOT NULL,
        payment_method TEXT NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS sales_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        total REAL NOT NULL,
        date TEXT NOT NULL,
        payment_method TEXT NOT NULL
    )
''')

c.execute('''
        CREATE TABLE IF NOT EXISTS sales_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        total REAL NOT NULL,
        FOREIGN KEY(sale_id) REFERENCES sales_summary(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    )
''')


# Crear tabla de clientes si no existe
c.execute('''
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
''')

# Crear tabla de deudas si no existe
c.execute('''
    CREATE TABLE IF NOT EXISTS debts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        sale_id INTEGER,
        original_amount REAL NOT NULL,
        remaining_amount REAL NOT NULL,
        status TEXT DEFAULT 'pendiente',
        date TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers (id),
        FOREIGN KEY (sale_id) REFERENCES sales_summary (id)
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        debt_id INTEGER,
        customer_id INTEGER,
        amount REAL,
        date TEXT,
        FOREIGN KEY(debt_id) REFERENCES debts(id),
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS cash_withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL
    )
''')

def handle_exception(exc_type, exc_value, exc_traceback):
    # Ignorar las interrupciones de teclado
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Escribir el error en un archivo de log
    with open("error_log.txt", "a") as f:
        f.write("Error no manejado:\n")
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)

    # Mostrar un mensaje emergente con el error
    root = tk.Tk()
    root.withdraw()  # Ocultar la ventana principal
    messagebox.showerror("Error", f"Se ha producido un error: {exc_value}")


conn.commit()

class StockManagementApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.current_sale = []  # Inicializar la lista de ventas actuales

    
    def initUI(self):
        self.setWindowTitle('Control de Stock')
        self.showMaximized()
        # Configurar el icono de la ventana
        self.setWindowIcon(QIcon('stock.ico'))  # Reemplaza con la ruta de tu archivo ICO

        main_layout = QVBoxLayout()

        # Fuente más grande
        font = QFont()
        font.setPointSize(14)  # Tamaño de la fuente
        
        # Aplicar la fuente a toda la aplicación
        QApplication.setFont(font)

        self.tab_widget = QTabWidget()
            
        # Pestaña de Productos
        products_tab = QWidget()
        product_layout = QVBoxLayout()

        # Formulario de Producto
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
        product_layout.addLayout(form_layout)
        product_layout.addLayout(button_layout)
        product_layout.addWidget(self.product_table)
        products_tab.setLayout(product_layout)

        # Agregar la pestaña de productos al tab widget principal
        self.tab_widget.addTab(products_tab, "Productos")

        # Pestaña de Ventas
        sales_tab = QWidget()
        sales_layout = QVBoxLayout()
        # Crear el formulario de la venta
        sale_form_layout = QHBoxLayout()
        
        self.sale_barcode_input = QLineEdit()
        self.sale_barcode_input.setPlaceholderText("Código de Barras")
        self.sale_name_input = QLineEdit()
        self.sale_name_input.setPlaceholderText("Nombre del Producto")
        self.sale_completer = QCompleter()
        self.sale_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.sale_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.sale_name_input.setCompleter(self.sale_completer)
        
        self.sale_name_input.textChanged.connect(self.auto_fill_product_details)
        
        # ComboBox para seleccionar cliente
        self.customer_select = QComboBox()
        self.customer_select.setEditable(True)
        self.customer_select.setPlaceholderText("Ingresar cliente")
        self.load_customers_into_combobox()
        self.customer_select.setVisible(False)

        self.sale_quantity_input = QSpinBox()
        self.sale_quantity_input.setMinimum(1)
        self.sale_quantity_input.setMaximum(1000000)
        self.sale_quantity_input.setPrefix("Cantidad: ")

        self.payment_method_input = QComboBox()
        self.payment_method_input.addItems(["Efectivo", "Transferencia", "Débito", "A Crédito"])
        self.payment_method_input.currentTextChanged.connect(self.toggle_customer_input)



        sale_form_layout.addWidget(self.sale_barcode_input)
        sale_form_layout.addWidget(self.sale_name_input)
        sale_form_layout.addWidget(self.sale_quantity_input)
        sale_form_layout.addWidget(self.customer_select)  


        add_sale_button = QPushButton("AÑADIR")
        add_sale_button.clicked.connect(self.add_to_sale)

        remove_sale_button = QPushButton("QUITAR")
        remove_sale_button.clicked.connect(self.remove_from_sale)

        register_sale_button = QPushButton("REGISTRAR VENTA")
        register_sale_button.clicked.connect(self.register_sale)

        sale_button_layout = QHBoxLayout()
        sale_button_layout.addWidget(add_sale_button)
        sale_button_layout.addWidget(remove_sale_button)
        sale_button_layout.addWidget(register_sale_button)

        # Crear la tabla de productos para esta pestaña
        self.sale_table = QTableWidget()
        self.sale_table.setColumnCount(6)
        self.sale_table.setHorizontalHeaderLabels(
            ['Código de Barras', 'Nombre', 'Cantidad', 'Precio de Venta', 'Precio de Costo', 'Margen de Ganancia']
        )
        self.sale_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sale_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed)
        # Conectar la señal de cambio en la tabla para actualizar cantidad y total
        self.sale_table.cellChanged.connect(self.on_cell_changed)


        # Configurar la sección de totales
        sales_total_layout = QHBoxLayout()
        self.total_label = QLabel('TOTAL: $0.00')
        self.payment_input = QDoubleSpinBox()
        self.payment_input.setMinimum(0.0)
        self.payment_input.setMaximum(10000000.0)
        self.payment_input.setPrefix("PAGO: $")
        self.payment_input.valueChanged.connect(self.calculate_change)

        self.change_label = QLabel('VUELTO: $0.00')

        sales_total_layout.addWidget(QLabel("Método de Pago:"))
        sales_total_layout.addWidget(self.payment_method_input)
        sales_total_layout.addWidget(self.total_label)
        sales_total_layout.addWidget(self.payment_input)
        sales_total_layout.addWidget(self.change_label)

        # Añadir los layouts a la pestaña nueva
        sales_layout.addLayout(sale_form_layout)
        sales_layout.addLayout(sale_button_layout)
        sales_layout.addWidget(self.sale_table)
        sales_layout.addLayout(sales_total_layout)
        sales_tab.setLayout(sales_layout)

        self.tab_widget.addTab(sales_tab, "Ventas")

        # Pestaña de Caja
        caja_tab = QWidget()
        caja_layout = QVBoxLayout()

        daily_revenue_layout = QHBoxLayout()
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat('yyyy-MM-dd')
        self.date_input.setDate(date.today())

        calculate_revenue_button = QPushButton("CALCULAR RECAUDACIÓN")
        calculate_revenue_button.clicked.connect(self.calculate_revenue)

        self.revenue_label = QLabel('RECAUDACIÓN DEL DÍA: $0.00')
        self.daily_profit_label = QLabel('GANANCIA DEL DÍA: $0.00')
        self.cash_in_label = QLabel('EFECTIVO INGRESADO: $0.00')

        daily_revenue_layout.addWidget(self.date_input)
        daily_revenue_layout.addWidget(calculate_revenue_button)
        daily_revenue_layout.addWidget(self.revenue_label)
        daily_revenue_layout.addWidget(self.daily_profit_label)
        daily_revenue_layout.addWidget(self.cash_in_label)
        
        # Crear el botón de retiro de efectivo y campo de entrada
        cash_withdrawal_layout = QHBoxLayout()
        self.withdrawal_amount_input = QDoubleSpinBox()
        self.withdrawal_amount_input.setMinimum(0.0)
        self.withdrawal_amount_input.setMaximum(1000000.0)
        self.withdrawal_amount_input.setPrefix("Cantidad: $")

        withdraw_cash_button = QPushButton("RETIRAR EFECTIVO")
        withdraw_cash_button.clicked.connect(self.withdraw_cash)
        withdraw_cash_historial = QPushButton("HISTORIAL DE RETIROS")
        withdraw_cash_historial.clicked.connect(self.withdraw_historial)

        cash_withdrawal_layout.addWidget(self.withdrawal_amount_input)
        cash_withdrawal_layout.addWidget(withdraw_cash_button)
        cash_withdrawal_layout.addWidget(withdraw_cash_historial)


        self.daily_sales_report_table = QTableWidget()
        self.daily_sales_report_table.setColumnCount(7)
        self.daily_sales_report_table.setHorizontalHeaderLabels(['Producto', 'Cantidad', 'Total', 'Fecha', 'Precio de Costo', 'Margen de Ganancia', 'Método de Pago'])
        self.daily_sales_report_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.daily_sales_report_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        monthly_report_layout = QHBoxLayout()
        self.monthly_sales_label = QLabel('VENTAS: $0.00')
        self.monthly_profit_label = QLabel('GANANCIAS: $0.00')

        self.start_date_input = QDateEdit()
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDisplayFormat('yyyy-MM-dd')
        self.start_date_input.setDate(date.today().replace(day=1))

        self.end_date_input = QDateEdit()
        self.end_date_input.setCalendarPopup(True)
        self.end_date_input.setDisplayFormat('yyyy-MM-dd')
        self.end_date_input.setDate(date.today())

        generate_report_button = QPushButton("GENERAR REPORTE")
        generate_report_button.clicked.connect(self.generate_monthly_report)

        monthly_report_layout.addWidget(self.start_date_input)
        monthly_report_layout.addWidget(self.end_date_input)
        monthly_report_layout.addWidget(generate_report_button)
        monthly_report_layout.addWidget(self.monthly_sales_label)
        monthly_report_layout.addWidget(self.monthly_profit_label)

        self.monthly_sales_report_table = QTableWidget()
        self.monthly_sales_report_table.setColumnCount(7)
        self.monthly_sales_report_table.setHorizontalHeaderLabels(['Producto', 'Cantidad', 'Total', 'Fecha', 'Precio de Costo', 'Margen de Ganancia', 'Método de Pago'])
        self.monthly_sales_report_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.monthly_sales_report_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        

        caja_layout.addLayout(daily_revenue_layout)
        caja_layout.addWidget(self.daily_sales_report_table)
        caja_layout.addLayout(cash_withdrawal_layout)  
        caja_layout.addLayout(monthly_report_layout)
        caja_layout.addWidget(self.monthly_sales_report_table)
        caja_tab.setLayout(caja_layout)

        self.tab_widget.addTab(caja_tab, "Caja")
        
        # Agregar la pestaña de Clientes y Deudas
        customers_tab = QWidget()
        customers_layout = QVBoxLayout()

        # Formulario de Cliente
        customer_form_layout = QFormLayout()
        self.customer_name_input = QLineEdit()
        customer_form_layout.addRow('NOMBRE DEL CLIENTE:', self.customer_name_input)

        add_customer_button = QPushButton('AGREGAR CLIENTE')
        add_customer_button.clicked.connect(self.add_customer)
        customer_form_layout.addWidget(add_customer_button)

        # Tabla de Clientes
        self.customer_table = QTableWidget()
        self.customer_table.setColumnCount(4)
        self.customer_table.setHorizontalHeaderLabels(['Nombre', 'Deuda Total', 'Fecha de último pago', 'Monto de últmo pago'])
        self.customer_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.customer_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.customer_table.cellClicked.connect(self.load_customer_to_form)
        customers_layout.addLayout(customer_form_layout)
        customers_layout.addWidget(self.customer_table)


        view_payment_history_button = QPushButton('HISTORIAL DE PAGOS')
        view_payment_history_button.clicked.connect(self.show_payment_history)  # Conectar a la función show_payment_history
        customers_layout.addWidget(view_payment_history_button)  # Añadir el botón al layout


        # Formulario de Deudas
        debt_form_layout = QFormLayout()

        # Campo para el nombre del cliente (auto llenado con el cliente seleccionado)
        self.debt_customer_combobox = QComboBox()
        self.load_customers_to_combobox()  # Llenar el ComboBox con los clientes

        # Campo para ingresar el monto a pagar (permite pagar menos del total)
        self.debt_amount_input = QDoubleSpinBox()
        self.debt_amount_input.setMinimum(0.0)
        self.debt_amount_input.setMaximum(1000000.0)  # Limitar máximo de deuda, puede ajustarse

        # Botón para pagar la deuda parcial
        pay_debt_button = QPushButton('PAGAR DEUDA')
        pay_debt_button.clicked.connect(self.pay_debt)  # Conectar a la función pay_debt

        # Añadir al formulario
        debt_form_layout.addRow("CLIENTE", self.debt_customer_combobox)
        debt_form_layout.addRow("MONTO A PAGAR", self.debt_amount_input)
        debt_form_layout.addWidget(pay_debt_button)



        # Tabla de Deudas
        self.debt_table = QTableWidget()
        self.debt_table.setColumnCount(4)
        self.debt_table.setHorizontalHeaderLabels(['Cliente', 'Monto', 'Fecha', 'Detalles'])
        self.debt_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.debt_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.debt_table.cellClicked.connect(self.cell_clicked)
        customers_layout.addLayout(debt_form_layout)
        customers_layout.addWidget(self.debt_table)

        customers_tab.setLayout(customers_layout)
        self.tab_widget.addTab(customers_tab, "Clientes")


        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)
        self.load_products()
        self.initialize_completers()
        self.setup_completer()
        self.update_customer_table()
        self.update_debt_table()

        
    def initialize_completers(self):
        """Inicializa los autocompletadores con datos actuales de productos."""
        product_names = self.fetch_product_names()
        self.completer.setModel(QStringListModel(product_names))
        self.sale_completer.setModel(QStringListModel(product_names))
        
    def fetch_product_names(self):
        """Fetches existing product names from the database."""
        c.execute('SELECT name FROM products')
        product_names = [row[0] for row in c.fetchall()]
        return product_names

    def load_customers_into_combobox(self):
        c.execute("SELECT name FROM customers")
        customers = c.fetchall()
        for customer in customers:
            self.customer_select.addItem(customer[0])

    def load_customers_to_combobox(self):
        query = "SELECT name FROM customers"
        c.execute(query)
        customers = c.fetchall()

        self.debt_customer_combobox.clear()  # Limpiar las opciones previas
        for customer in customers:
            self.debt_customer_combobox.addItem(customer[0])  # Agregar nombres al ComboBox


    def load_products(self, filter_text=""):
        # Si hay texto en el filtro, usamos un LIKE para filtrar los productos
        if filter_text:
            query = "SELECT barcode, name, quantity, cost_price, profit_margin, price FROM products WHERE name LIKE ? ORDER BY name"
            c.execute(query, ('%' + filter_text + '%',))
        else:
            query = "SELECT barcode, name, quantity, cost_price, profit_margin, price FROM products ORDER BY name"
            c.execute(query)
        
        products = c.fetchall()
        
        # Limpiar la tabla antes de llenarla
        self.product_table.setRowCount(0)
        
        # Iterar sobre los productos y llenar la tabla
        for row_number, row_data in enumerate(products):
            self.product_table.insertRow(row_number)
            for column_number, data in enumerate(row_data):
                # Convertir los datos a cadena para mostrarlos en la tabla
                self.product_table.setItem(row_number, column_number, QTableWidgetItem(str(data)))

        # Ajustar el tamaño de las columnas para que se adapten al contenido
        self.product_table.resizeColumnsToContents()

    
    def setup_completer(self):
        c.execute("SELECT name FROM products")
        product_names = [row[0] for row in c.fetchall()]
        completer = QCompleter(product_names, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)  # Permite coincidencias parciales
        self.name_input.setCompleter(completer)
    
    def setup_sale_completer(self):
        c.execute("SELECT name FROM products")
        product_names = [row[0] for row in c.fetchall()]
        completer = QCompleter(product_names, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)  # Permite coincidencias parciales
        self.sale_name_input.setCompleter(completer)
        
    def search_product(self):
        search_term = self.name_input.text()  # Obtén el término de búsqueda del campo de texto de nombre
        if search_term:
            c.execute("SELECT barcode, name, quantity, cost_price, profit_margin, price FROM products WHERE name LIKE ? OR barcode LIKE ?", 
                    ('%' + search_term + '%', '%' + search_term + '%'))
            results = c.fetchall()
            
            # Limpiar la tabla antes de agregar los nuevos resultados
            self.product_table.setRowCount(0)
            
            # Mostrar los resultados en la tabla
            for row in results:
                row_position = self.product_table.rowCount()
                self.product_table.insertRow(row_position)
                for column, item in enumerate(row):
                    self.product_table.setItem(row_position, column, QTableWidgetItem(str(item)))
        else:
            QMessageBox.information(self, "Buscar Producto", "Por favor, ingresa un término de búsqueda.")


    def toggle_customer_input(self, payment_method):
        if payment_method == "A Crédito":
            self.customer_select.setVisible(True)
        else:
            self.customer_select.setVisible(False)


    def auto_fill_product_name(self):
        barcode = self.barcode_input.text().strip()

        # Verifica si el código de barras no es None ni una cadena vacía
        if barcode:
            c.execute("SELECT name FROM products WHERE barcode=?", (barcode,))
            result = c.fetchone()

            if result:
                self.name_input.setText(result[0])
            
    def filter_products(self):
        filter_text = self.name_input.text().strip()  # Obtener el texto de filtro
        self.load_products(filter_text)  # Filtrar los productos por nombre

    
    def auto_fill_product_details(self):
        product_name = self.name_input.text() if self.name_input else ""
        barcode = self.barcode_input.text() if self.barcode_input else ""

        if product_name:
            c.execute("SELECT price, quantity, barcode, cost_price, profit_margin FROM products WHERE name=?", (product_name,))
        elif barcode:
            c.execute("SELECT name, price, quantity, cost_price, profit_margin FROM products WHERE barcode=?", (barcode,))

        result = c.fetchone()
        if result:
            if product_name:
                self.price_input.setValue(result[0])
                self.quantity_input.setValue(result[1])
                self.barcode_input.setText(result[2])
                self.cost_price_input.setValue(result[3])
                self.profit_margin_input.setValue(result[4])
            else:
                self.name_input.setText(result[0])
                self.price_input.setValue(result[1])
                self.quantity_input.setValue(result[2])
                self.cost_price_input.setValue(result[3])
                self.profit_margin_input.setValue(result[4])
        else:
            self.price_input.setValue(0.0)
            self.quantity_input.setValue(0)
        self.product_table.resizeColumnsToContents()

            
    def load_product_by_barcode(self, barcode):
        print(f"Buscando el código de barras: '{barcode}'")  # Debug
        c.execute("SELECT name, price FROM products WHERE barcode=?", (barcode,))
        result = c.fetchone()
        if result:
            self.sale_name_input.setText(result[0])
            self.add_to_sale()
        else:
            QMessageBox.critical(self, "Error", "Producto no encontrado")

    
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
    
    def update_completer(self):
        # Obtener todos los nombres de los productos de la base de datos
        c.execute("SELECT name FROM products")
        product_names = [row[0] for row in c.fetchall()]

        # Configurar el QCompleter con los nuevos datos
        self.completer.setModel(QStringListModel(product_names))
        self.sale_completer.setModel(QStringListModel(product_names))

    
    def delete_product(self):
        name = self.name_input.text()
        if name:
            c.execute("DELETE FROM products WHERE name=?", (name,))
            conn.commit()
            self.update_product_list()
            self.clear_entries()
            self.setup_completer()
            QMessageBox.information(self, "Éxito", "Producto eliminado")
        else:
            QMessageBox.critical(self, "Error", "Seleccione un producto para eliminar")
            
    def update_product_barcode(self):
        # Asegúrate de que los inputs están inicializados
        if not self.name_input or not self.barcode_input:
            QMessageBox.warning(self, "Error", "Campos no inicializados correctamente.")
            return

        product_name = self.name_input.text().strip()
        barcode = self.barcode_input.text().strip()

        # Asegúrate de que ambos campos están llenos
        if product_name and barcode:
            # Verificar si ya existe un producto con el mismo nombre y código de barras
            c.execute("SELECT * FROM products WHERE name=?", (product_name,))
            existing_product = c.fetchone()

            if existing_product:
                # Si ya existe un producto con ese nombre, solo actualiza el código de barras
                c.execute("UPDATE products SET barcode=? WHERE name=?", (barcode, product_name))
                conn.commit()
                QMessageBox.information(self, "Éxito", "Código de barras actualizado correctamente.")
            else:
                QMessageBox.warning(self, "Advertencia", "No se encontró un producto con ese nombre.")
        else:
            QMessageBox.warning(self, "Advertencia", "Debe proporcionar tanto nombre como código de barras.")


    def update_product_list(self):
        self.product_table.setRowCount(0)  # Limpia la tabla antes de llenarla
        c.execute("SELECT barcode, name, quantity, cost_price, profit_margin, price FROM products")
        for row_index, row_data in enumerate(c.fetchall()):
            self.product_table.insertRow(row_index)
            for col_index, data in enumerate(row_data):
                self.product_table.setItem(row_index, col_index, QTableWidgetItem(str(data)))
                
    def update_final_price(self):
        cost_price = self.cost_price_input.value()
        profit_margin = self.profit_margin_input.value()
        
        if profit_margin != 0:
            final_price = cost_price * (1 + profit_margin / 100.00)
            self.price_input.blockSignals(True)
            self.price_input.setValue(final_price)
            self.price_input.blockSignals(False)

    def update_profit_margin(self):
        cost_price = self.cost_price_input.value()
        final_price = self.price_input.value()
        
        if cost_price > 0 and final_price != cost_price:
            profit_margin = ((final_price - cost_price) / cost_price) * 100.00
            self.profit_margin_input.blockSignals(True)
            self.profit_margin_input.setValue(profit_margin)
            self.profit_margin_input.blockSignals(False)
            
    def get_product_names(self):        
        c.execute('SELECT name FROM products')
        products = c.fetchall()
                
        # Convertir la lista de tuplas a una lista de cadenas
        product_names = [product[0] for product in products]
        return product_names

    
    def clear_entries(self):
        if self.tab_widget.currentIndex() == 0:  # Pestaña de Productos
            self.name_input.clear()
            self.quantity_input.setValue(0)
            self.price_input.setValue(0.0)
            self.cost_price_input.setValue(0.0)
            self.profit_margin_input.setValue(0.0)
            self.barcode_input.clear()
        elif self.tab_widget.currentIndex() == 1:
            self.sale_name_input.clear()
            self.sale_quantity_input.setValue(1)
            self.sale_barcode_input.clear()

    def load_product_to_form(self, row, column):
        try:
            barcode = str(self.product_table.item(row, 0).text())
            name = str(self.product_table.item(row, 1).text())
            quantity_text = self.product_table.item(row, 2).text()
            cost_price_text = self.product_table.item(row, 3).text()
            profit_margin_text = self.product_table.item(row, 4).text()
            price_text = self.product_table.item(row, 5).text()
            
            # Verifica y convierte los valores
            quantity = int(quantity_text) if quantity_text.isdigit() else 0
            cost_price = float(cost_price_text) if self.is_float(cost_price_text) else 0.0
            profit_margin = float(profit_margin_text) if self.is_float(profit_margin_text) else 0.0
            price = float(price_text) if self.is_float(price_text) else 0.0
            
            # Asignar los valores a los campos del formulario
            self.barcode_input.setText(barcode)
            self.name_input.setText(name)
            self.quantity_input.setValue(quantity)
            self.cost_price_input.setValue(cost_price)
            self.profit_margin_input.setValue(profit_margin)
            self.price_input.setValue(price)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar los datos del producto: {e}")

    # Corrige la función is_float para que acepte 'self'
    def is_float(self, value):
        try:
            float(value)
            return True
        except ValueError:
            return False
        
    def update_quantity_from_table(self, item):
        row = item.row()
        column = item.column()

        # Si la celda editada corresponde a la columna de "Cantidad"
        if column == 2:  
            try:
                new_quantity = int(self.sale_table.item(row, column).text())
                if new_quantity < 0:
                    QMessageBox.warning(self, "Error", "La cantidad no puede ser negativa.")
                    return

                # Actualizar la cantidad en self.current_sale
                self.current_sale[row] = (
                    self.current_sale[row][0],  # barcode
                    self.current_sale[row][1],  # name
                    new_quantity,               # nueva cantidad
                    self.current_sale[row][3],  # price
                    self.current_sale[row][4],  # cost_price
                    self.current_sale[row][5],  # profit_margin
                )

                # Actualizar el total de la venta
                self.calculate_total_sale()

            except ValueError:
                QMessageBox.warning(self, "Error", "La cantidad debe ser un número entero.")


    def add_to_sale(self):
        product_name = self.sale_name_input.text()
        barcode_input = self.sale_barcode_input.text().strip()
        quantity = self.sale_quantity_input.value()

        if product_name:
            c.execute("SELECT barcode, quantity, price, cost_price, profit_margin FROM products WHERE name=?", (product_name,))
            result = c.fetchone()
        elif barcode_input:
            c.execute("SELECT name, quantity, price, cost_price, profit_margin FROM products WHERE barcode=?", (barcode_input,))
            result = c.fetchone()
        else:
            QMessageBox.critical(self, "Error", "Debe ingresar un nombre de producto o un código de barras.")
            return

        if result:
            barcode_db, current_quantity, price, cost_price, profit_margin = result

            if current_quantity >= quantity:
                # Verificar si el producto ya está en la tabla
                product_found = False
                for row in range(self.sale_table.rowCount()):
                    table_barcode = self.sale_table.item(row, 0).text()  # Código de barras
                    table_name = self.sale_table.item(row, 1).text()      # Nombre

                    # Verificamos por nombre o código de barras
                    if table_name == product_name or table_barcode == barcode_db:
                        # Producto encontrado, actualizar cantidad
                        existing_quantity = int(self.sale_table.item(row, 2).text())  # Obtener cantidad actual
                        new_quantity = existing_quantity + quantity

                        if current_quantity >= new_quantity:
                            # Actualizamos cantidad y recalculamos precios
                            self.sale_table.setItem(row, 2, QTableWidgetItem(str(new_quantity)))
                            self.sale_table.setItem(row, 3, QTableWidgetItem(f"${price * new_quantity:.2f}"))  # Precio total
                            product_found = True
                            # Actualizamos también en `self.current_sale`
                            for i, (barcode, name, q, p, cost, profit) in enumerate(self.current_sale):
                                if name == product_name or barcode == barcode_db:
                                    self.current_sale[i] = (barcode_db, product_name, new_quantity, price, cost_price, profit_margin)
                            break
                        else:
                            QMessageBox.critical(self, "Error", f"No hay suficiente cantidad de {product_name} en inventario.")
                            return

                if not product_found:
                    # Si el producto no está en la tabla, lo añadimos como una nueva fila
                    current_row_count = self.sale_table.rowCount()
                    self.sale_table.insertRow(current_row_count)
                    self.sale_table.setItem(current_row_count, 0, QTableWidgetItem(barcode_db))
                    self.sale_table.setItem(current_row_count, 1, QTableWidgetItem(product_name))
                    self.sale_table.setItem(current_row_count, 2, QTableWidgetItem(str(quantity)))
                    self.sale_table.setItem(current_row_count, 3, QTableWidgetItem(f"${price * quantity:.2f}"))
                    self.sale_table.setItem(current_row_count, 4, QTableWidgetItem(f"${cost_price:.2f}"))
                    self.sale_table.setItem(current_row_count, 5, QTableWidgetItem(f"{profit_margin:.2f}%"))

                    # También añadirlo en `self.current_sale`
                    self.current_sale.append((barcode_db, product_name, quantity, price, cost_price, profit_margin))

                # Actualizamos el total
                self.calculate_total_sale()

            else:
                QMessageBox.critical(self, "Error", f"No hay suficiente cantidad de {product_name} en inventario.")
        else:
            QMessageBox.critical(self, "Error", "Producto no encontrado.")

        # Limpiar los campos de entrada
        self.sale_name_input.clear()
        self.sale_barcode_input.clear()
        self.sale_quantity_input.setValue(1)  # Reiniciar la cantidad a 1 o el valor predeterminado

    def update_current_sale_table(self):
        self.sale_table.setRowCount(0)  # Limpiar la tabla antes de actualizar

        total_sale = 0

        # Insertar filas en la tabla
        for idx, (barcode, name, quantity, price, cost_price, profit_margin) in enumerate(self.current_sale):
            self.sale_table.insertRow(idx)
            self.sale_table.setItem(idx, 0, QTableWidgetItem(barcode))  # Código de barras
            self.sale_table.setItem(idx, 1, QTableWidgetItem(name))     # Nombre del producto
            self.sale_table.setItem(idx, 2, QTableWidgetItem(str(quantity)))  # Cantidad
            self.sale_table.setItem(idx, 3, QTableWidgetItem(f"${price:.2f}"))  # Precio de venta
            self.sale_table.setItem(idx, 4, QTableWidgetItem(f"${cost_price:.2f}"))  # Precio de costo
            self.sale_table.setItem(idx, 5, QTableWidgetItem(f"{profit_margin}%"))  # Margen de ganancia
            # Calcular el total correctamente
            total_sale += quantity * price

        # Actualizar la etiqueta del total de la venta
        self.total_label.setText(f"TOTAL: ${total_sale:.2f}")
        self.current_total = total_sale  # Guardar el total actual para referencia futura
    
    def remove_from_sale(self):
        selected_row = self.sale_table.currentRow()
        if selected_row != -1:
            # Eliminar el producto de `self.current_sale` también
            del self.current_sale[selected_row]
            
            # Eliminar la fila de la tabla
            self.sale_table.removeRow(selected_row)
            
            # Volver a calcular el total de la venta
            self.calculate_total_sale()
        else:
            QMessageBox.warning(self, "Error", "Seleccione un producto para quitar de la venta.")

    def on_cell_changed(self, row, column):
        # Verificar si la columna modificada es la de cantidad (índice 2)
        if column == 2:
            # Asegurarse de que la fila exista en self.current_sale
            if row < len(self.current_sale):
                try:
                    # Obtener la nueva cantidad de la tabla
                    new_quantity = int(self.sale_table.item(row, column).text())
                    if new_quantity < 1:
                        raise ValueError("La cantidad no puede ser menor que 1.")

                    # Actualizar la cantidad en la lista `self.current_sale`
                    barcode, name, _, price, cost_price, profit_margin = self.current_sale[row]
                    self.current_sale[row] = (barcode, name, new_quantity, price, cost_price, profit_margin)

                    # Recalcular el total de la venta
                    self.calculate_total_sale()
                except ValueError:
                    QMessageBox.warning(self, "Error", "Por favor ingrese una cantidad válida.")
                    # Restaurar la cantidad anterior en la tabla si el valor no es válido
                    self.sale_table.blockSignals(True)
                    old_quantity = self.current_sale[row][2]
                    self.sale_table.setItem(row, 2, QTableWidgetItem(str(old_quantity)))
                    self.sale_table.blockSignals(False)
                    
                    
    def calculate_total_sale(self):
        total_sale = 0
        # Recorremos `self.current_sale` para calcular el total
        for (barcode, name, quantity, price, cost_price, profit_margin) in self.current_sale:
            total_sale += quantity * price  # Calcular total por cantidad y precio

        # Actualizamos la etiqueta del total
        self.total_label.setText(f"TOTAL: ${total_sale:.2f}")
        self.current_total = total_sale  # Guardar el total actual para referencia futura


    def clear_sale_entries(self):
        self.sale_name_input.clear()
        self.sale_quantity_input.setValue(0)

    def wrap_text(self, text, max_width, c, font_name, font_size):
        """Divide el texto en líneas que se ajusten al ancho máximo permitido."""
        lines = []
        words = text.split(' ')
        current_line = ''
        
        for word in words:
            test_line = f'{current_line} {word}'.strip()
            text_width = c.stringWidth(test_line, font_name, font_size)
            
            if text_width > max_width:
                lines.append(current_line)
                current_line = word
            else:
                current_line = test_line
        
        if current_line:
            lines.append(current_line)
        
        return lines

    def generate_ticket(self, sale_details, total, payment_method, customer_payment, change):
        try:
            ticket_width = 53 * mm
            line_height = 12.5
            top_margin = 10
            bottom_margin = 10
            max_line_width = ticket_width - 2 * 5  # Margen izquierdo y derecho

            lines = []

            # Encabezado del ticket
            lines.append("Kiosco 25")
            lines.append("")
            lines.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Detalle de la compra
            lines.append("Detalle de la compra:")
            c = canvas.Canvas("temp.pdf", pagesize=(ticket_width, 10000))  # Solo para calcular el ancho
            c.setFont("Helvetica", 10)
            
            for item in sale_details['items']:
                product_line = f"{item['name']} x {item['quantity']} - ${item['price']:.2f}"
                wrapped_lines = self.wrap_text(product_line, max_line_width, c, "Helvetica", 10)
                lines.extend(wrapped_lines)
            
            lines.append("----------------------------------------")
            lines.append(f"Subtotal: ${total['subtotal']:.2f}")

            # Total en negrita
            lines.append(f"Total: ${total['total']:.2f}")

            # Forma de pago
            lines.append(f"Forma de pago: {payment_method}")
            if payment_method == "Efectivo":
                lines.append(f"Recibimos: ${customer_payment:.2f}")
                lines.append(f"Vuelto: ${change:.2f}")

            # Mensaje de agradecimiento
            lines.append("----------------------------------------")
            lines.append("¡Gracias por su compra!")
            lines.append("----------------------------------------")
            lines.append("*NO VÁLIDO COMO FACTURA*")
            lines.append("----------------------------------------")

            # Calcular la altura total del ticket en función del número de líneas
            ticket_height = top_margin + line_height * len(lines) + bottom_margin

            # Crear el documento PDF con el tamaño calculado
            ticket_file = "ticket.pdf"
            c = canvas.Canvas(ticket_file, pagesize=(ticket_width, ticket_height))

            # Escalar el lienzo al 80%
            scale_factor = 0.8
            c.scale(scale_factor, scale_factor)

            # Imprimir la primera línea centrada, en negrita y más grande
            c.setFont("Helvetica-Bold", 14)
            first_line = lines.pop(0)
            text_width = c.stringWidth(first_line, "Helvetica-Bold", 14)
            c.drawString((ticket_width - text_width) / 2 / scale_factor, (ticket_height - top_margin) / scale_factor, first_line)
            y = (ticket_height - top_margin - line_height) / scale_factor

            # Imprimir el resto de las líneas
            c.setFont("Helvetica", 10)
            for line in lines:
                if "*NO VÁLIDO COMO FACTURA*" in line:
                    c.setFont("Helvetica", 10)
                    text_width = c.stringWidth(line, "Helvetica", 10)
                    c.drawString((ticket_width - text_width) / 2 / scale_factor, y, line)  # Centrar la frase
                else:
                    if "Total:" in line:
                        c.setFont("Helvetica-Bold", 10)  # Negrita para el total
                    c.drawString(5 / scale_factor, y, line)
                y -= line_height / scale_factor
                c.setFont("Helvetica", 10)  # Volver a la fuente normal

            c.save()
            return ticket_file
        except Exception as e:
            print(f"Error al generar el ticket: {e}")
            return None
                
    def print_ticket(self, ticket_file):
        # Usa la impresora predeterminada para imprimir el ticket
        win32api.ShellExecute(0, "print", ticket_file, None, ".", 0)

    def register_sale(self):
        try:
            sale_details = {'items': []}
            total_sale = 0
            low_stock_warnings = []

            # Calcular el total de la venta y actualizar stock de los productos
            for barcode, product_name, sale_quantity, sale_price, cost_price, profit_margin in self.current_sale:
                c.execute("SELECT id, quantity FROM products WHERE name=?", (product_name,))
                result = c.fetchone()
                if result:
                    product_id, current_quantity = result
                    new_quantity = current_quantity - sale_quantity

                    if new_quantity <= 5:
                        low_stock_warnings.append(f"El producto '{product_name}' tiene un stock bajo: {new_quantity} unidades restantes.")

                    # Actualizar el stock del producto
                    c.execute("UPDATE products SET quantity=? WHERE id=?", (new_quantity, product_id))

                    # Calcular total del producto
                    total_sale_item = sale_quantity * sale_price
                    total_sale += total_sale_item

                    sale_details['items'].append({
                        'product_id': product_id,
                        'barcode': barcode,
                        'name': product_name,
                        'quantity': sale_quantity,
                        'price': sale_price
                    })
                else:
                    QMessageBox.critical(self, "Error", f"Producto {product_name} no encontrado")
                    return

            # Registrar la venta en la tabla sales_summary
            payment_method = self.payment_method_input.currentText()
            formatted_datetime = datetime.now().strftime('%d-%m-%y %H:%M')
            c.execute("""
                INSERT INTO sales_summary (total, date, payment_method)
                VALUES (?, ?, ?)
            """, (total_sale, formatted_datetime, payment_method))

            # Obtener el id de la venta registrada
            c.execute("SELECT last_insert_rowid()")
            sale_id = c.fetchone()[0]

            # Registrar cada producto en la tabla sales_details
            for item in sale_details['items']:
                c.execute("""
                    INSERT INTO sales_details (sale_id, product_id, quantity, total)
                    VALUES (?, ?, ?, ?)
                """, (sale_id, item['product_id'], item['quantity'], item['quantity'] * item['price']))

            # Confirmar los cambios en la base de datos
            conn.commit()

            # Manejar ventas a crédito
            customer_payment = self.payment_input.value()
            customer_name = self.customer_select.currentText()  # Tomar el cliente del QComboBox

            if payment_method == "A Crédito":
                if not customer_name:
                    QMessageBox.warning(self, "Seleccionar Cliente", "Para registrar una venta a crédito debe seleccionar un cliente")
                    return
                
                # Registrar la deuda en la tabla debts
                self.register_debt(customer_name, total_sale, sale_id)
            elif payment_method != "A Crédito" and customer_payment < total_sale:
                QMessageBox.warning(self, "Pago Insuficiente", "El pago es menor que el total. Por favor, ingrese un monto adecuado.")
                return  # Salir si el pago es insuficiente
            else:
                # Generar y guardar el ticket
                change = 0
                if payment_method == "Efectivo":
                    change = customer_payment - total_sale

                ticket_file = self.generate_ticket(
                    sale_details=sale_details,
                    total={'subtotal': total_sale, 'total': total_sale},
                    payment_method=payment_method,
                    customer_payment=customer_payment,
                    change=change
                )

                if ticket_file:
                    response = QMessageBox.question(self, "Imprimir Ticket", "¿Desea imprimir el ticket?",
                                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
                    if response == QMessageBox.StandardButton.Yes:
                        self.print_ticket(ticket_file)

            # Mostrar advertencias de bajo stock si las hay
            if low_stock_warnings:
                QMessageBox.warning(self, "Advertencia de Stock Bajo", "\n".join(low_stock_warnings))

            # Limpiar la venta actual y resetear la interfaz
            self.current_sale = []
            self.update_current_sale_table()
            self.total_label.setText("TOTAL: $0.00")
            self.current_total = 0.0
            self.setup_sale_completer()
            self.sale_name_input.clear()
            self.sale_barcode_input.clear()
            self.sale_quantity_input.setValue(1)
            self.change_label.setText("VUELTO:$0.00")
            self.payment_input.setValue(0.00)
            self.payment_method_input.setCurrentText("Efectivo") 
            self.customer_select.setVisible(False)
            QMessageBox.information(self, "Éxito", "Venta registrada y ticket generado")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Se produjo un error al registrar la venta: {e}")
    
    def calculate_change(self):
        payment_method = self.payment_method_input.currentText()

        # Extraer el valor numérico del texto de self.total_label
        total_sale_str = self.total_label.text().replace('TOTAL: $', '').strip()

        try:
            # Intentar convertir la cadena a float
            total_sale = float(total_sale_str)
        except ValueError:
            # En caso de error, mostrar un mensaje o manejarlo adecuadamente
            QMessageBox.critical(self, "Error", "El total de la venta no es un número válido.")
            return

        customer_payment = self.payment_input.value()

        if payment_method == "Efectivo":
            change = customer_payment - total_sale
            if change >= 0:
                self.change_label.setText(f'VUELTO: ${change:.2f}')
            else:
                self.change_label.setText(f'FALTANTE: ${abs(change):.2f}')
            return change
        else:
            self.change_label.setText('Método de pago no requiere vuelto.')
            return 0
            
    def pay_debt(self):
        # Obtener el cliente seleccionado del QComboBox
        customer_name = self.debt_customer_combobox.currentText()
        if not customer_name:
            QMessageBox.warning(self, 'Advertencia', 'Por favor, seleccione un cliente.')
            return

        # Obtener el monto a pagar del input
        amount_to_pay = self.debt_amount_input.value()
        if amount_to_pay <= 0:
            QMessageBox.warning(self, 'Advertencia', 'El monto a pagar debe ser mayor que 0.')
            return

        # Obtener el ID del cliente de la base de datos
        query = "SELECT id FROM customers WHERE name = ?"
        c.execute(query, (customer_name,))
        result = c.fetchone()

        if not result:
            QMessageBox.warning(self, 'Error', 'Cliente no encontrado.')
            return

        customer_id = result[0]

        # Verificar si el cliente tiene deudas pendientes
        debt_check_query = "SELECT COUNT(*) FROM debts WHERE customer_id = ? AND remaining_amount > 0"
        c.execute(debt_check_query, (customer_id,))
        debt_count = c.fetchone()[0]

        if debt_count == 0:
            QMessageBox.warning(self, 'Error', 'El cliente no tiene deudas pendientes.')
            return

        # Obtener las deudas del cliente ordenadas por fecha
        debt_query = "SELECT id, remaining_amount FROM debts WHERE customer_id = ? AND remaining_amount > 0 ORDER BY date ASC"
        c.execute(debt_query, (customer_id,))
        debts = c.fetchall()

        total_debt = sum(debt_amount for _, debt_amount in debts)
        if amount_to_pay > total_debt:
            QMessageBox.warning(self, 'Advertencia', f'El monto a pagar (${amount_to_pay:.2f}) excede la deuda total (${total_debt:.2f}). Se ajustará el monto a la deuda total.')
            amount_to_pay = total_debt

        # Registrar el pago de deuda como una nueva venta en sales_summary
        insert_sale_query = """
            INSERT INTO sales_summary (total, date, payment_method)
            VALUES (?, ?, 'Pago de deuda')
        """
        current_date = QDate.currentDate().toString('yyyy-MM-dd')
        c.execute(insert_sale_query, (amount_to_pay, current_date))

        # Obtener el ID de la nueva venta
        sale_id = c.lastrowid

        # Registrar los detalles de la venta
        insert_sale_detail_query = """
            INSERT INTO sales_details (sale_id, product_id, quantity, total)
            VALUES (?, ?, ?, ?)
        """
        fake_product_id = 0
        c.execute(insert_sale_detail_query, (sale_id, fake_product_id, 1, amount_to_pay))

        # Asociar el pago con la deuda y registrar el pago en la tabla payments
        remaining_amount = amount_to_pay
        for debt_id, debt_amount in debts:
            if remaining_amount <= 0:
                break

            if remaining_amount >= debt_amount:
                payment_amount = debt_amount
                remaining_amount -= debt_amount
                # Actualizar el estado de la deuda a 'pagada'
                update_debt_query = "UPDATE debts SET remaining_amount = 0, status = 'pagada' WHERE id = ?"
                c.execute(update_debt_query, (debt_id,))
            else:
                payment_amount = remaining_amount
                remaining_amount = 0
                # Actualizar deuda parcialmente
                update_debt_query = "UPDATE debts SET remaining_amount = remaining_amount - ?, status = 'parcialmente pagada' WHERE id = ?"
                c.execute(update_debt_query, (payment_amount, debt_id))

            # Registrar el pago asociado a la deuda en la tabla payments
            insert_payment_query = "INSERT INTO payments (debt_id, customer_id, amount, date) VALUES (?, ?, ?, ?)"
            c.execute(insert_payment_query, (debt_id, customer_id, payment_amount, current_date))

        # Confirmar cambios en la base de datos
        conn.commit()

        # Mostrar mensaje de éxito
        QMessageBox.information(self, 'Éxito', f'Pago de ${amount_to_pay:.2f} registrado con éxito.')

        # Recargar la tabla de clientes
        self.update_customer_table()
        self.debt_customer_combobox.setCurrentIndex(0)
        self.debt_amount_input.setValue(0.0)
        
    def cancel_debt(self):
        # Obtener el cliente seleccionado del QComboBox
        customer_name = self.debt_customer_combobox.currentText()
        if not customer_name:
            QMessageBox.warning(self, 'Advertencia', 'Por favor, seleccione un cliente.')
            return

        # Obtener el ID del cliente de la base de datos
        query = "SELECT id FROM customers WHERE name = ?"
        c.execute(query, (customer_name,))
        result = c.fetchone()

        if not result:
            QMessageBox.warning(self, 'Error', 'Cliente no encontrado.')
            return

        customer_id = result[0]

        # Confirmar con el usuario si quiere cancelar todas las deudas
        reply = QMessageBox.question(
            self,
            'Confirmación',
            f'¿Está seguro de que desea cancelar todas las deudas del cliente {customer_name}?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            return

        # Eliminar todas las deudas del cliente
        delete_debts_query = "DELETE FROM debts WHERE customer_id = ?"
        c.execute(delete_debts_query, (customer_id,))

        # Confirmar cambios en la base de datos
        conn.commit()

        # Mostrar mensaje de éxito
        QMessageBox.information(self, 'Éxito', 'Todas las deudas del cliente han sido canceladas.')

        # Recargar la tabla de clientes
        self.load_customers()
        self.debt_customer_combobox.setCurrentIndex(0)

        
    def load_customers(self):
        # Consulta SQL para obtener los datos del cliente, deuda total y detalles del último pago
        query = """
            SELECT 
                c.name, 
                COALESCE(SUM(d.amount), 0) AS total_debt,  -- Total de la deuda (sumar de la tabla debts)
                COALESCE(MAX(p.date), 'N/A') AS last_payment_date,  -- Fecha del último pago
                COALESCE(p.amount, 0) AS last_payment_amount  -- Monto del último pago
            FROM 
                customers c
            LEFT JOIN 
                debts d ON c.id = d.customer_id  -- Unir con la tabla de deudas
            LEFT JOIN 
                payments p ON c.id = p.customer_id  -- Unir con la tabla de pagos
            GROUP BY 
                c.id
        """
        
        c.execute(query)
        customers = c.fetchall()
        
        # Establecer la cantidad de filas en la tabla de clientes
        self.customer_table.setRowCount(len(customers))
        
        for row, customer in enumerate(customers):
            # Mostrar el nombre del cliente
            self.customer_table.setItem(row, 0, QTableWidgetItem(customer[0]))
            
            # Mostrar la deuda total (columna 1)
            self.customer_table.setItem(row, 1, QTableWidgetItem(f"${customer[1]:.2f}"))
            
            # Mostrar la fecha del último pago (columna 2)
            last_payment_date = customer[2] if customer[2] != 'N/A' else 'N/A'
            self.customer_table.setItem(row, 2, QTableWidgetItem(last_payment_date))
            
            # Mostrar el monto del último pago (columna 3)
            last_payment_amount = f"${customer[3]:.2f}" if customer[3] != 0 else 'N/A'
            self.customer_table.setItem(row, 3, QTableWidgetItem(last_payment_amount))

        
    def update_debt_table(self, customer_name=None):
        # Limpiar la tabla de deudas antes de actualizarla
        self.debt_table.setRowCount(0)

        # Consulta SQL para obtener los detalles de las deudas y los productos vendidos
        query = """
            SELECT debts.id, customers.name, ROUND(debts.remaining_amount, 3) AS remaining_amount, debts.date, 
                GROUP_CONCAT(products.name, ', ') AS products_details
            FROM debts
            JOIN customers ON customers.id = debts.customer_id
            LEFT JOIN sales_summary ON debts.sale_id = sales_summary.id
            LEFT JOIN sales_details ON sales_summary.id = sales_details.sale_id
            LEFT JOIN products ON sales_details.product_id = products.id
            WHERE debts.remaining_amount > 0
        """

        # Si se especifica un cliente, filtrar por el nombre del cliente
        if customer_name:
            query += " AND customers.name = ?"
            query += " GROUP BY debts.id"
            c.execute(query, (customer_name,))
        else:
            query += " GROUP BY debts.id"
            c.execute(query)

        debts = c.fetchall()

        if debts:
            for row_number, debt in enumerate(debts):
                self.debt_table.insertRow(row_number)
                for column_number, data in enumerate(debt[1:]):  # Saltar el ID
                    if data is None:
                        data = ""
                    
                    item = QTableWidgetItem(str(data))
                    
                    if column_number == 3:  # Columna de "Detalles"
                        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                        item.setToolTip(str(data))  # Añadir tooltip con el texto completo

                    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)  # Hacer las celdas no editables
                    self.debt_table.setItem(row_number, column_number, item)

                # Guardar el ID de la deuda en la tabla para acceso posterior
                self.debt_table.setItem(row_number, 4, QTableWidgetItem(str(debt[0])))
            
    def cell_clicked(self, row, column):
        if column == 3:  # Columna "Detalles"
            detalles = self.debt_table.item(row, column).text()
            QMessageBox.information(self, "Detalles de la Deuda", detalles)

    def withdraw_historial(self):
        
        withdraw_history_window = QDialog(self)
        withdraw_history_window.setWindowTitle(f"Historial de retiros")

        # Ajustar tamaño mínimo de la ventana (por ejemplo, 600x400 píxeles)
        
        withdraw_history_window.setMinimumSize(800, 600)

        withdraw_history_table = QTableWidget()
        withdraw_history_table.setColumnCount(3)
        withdraw_history_table.setHorizontalHeaderLabels(['Monto', 'Fecha', 'Hora'])
        withdraw_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        withdraw_history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)


        # Consultar los pagos del cliente
        query = "SELECT amount, date, time FROM cash_withdrawals"
        c.execute(query)
        withdraws = c.fetchall()

        withdraw_history_table.setRowCount(len(withdraws))
        for row, withdraw in enumerate(withdraws):
            withdraw_history_table.setItem(row, 0, QTableWidgetItem(f"${withdraw[0]:.2f}"))
            withdraw_history_table.setItem(row, 1, QTableWidgetItem(withdraw[1]))
            withdraw_history_table.setItem(row, 2, QTableWidgetItem(withdraw[2]))

        layout = QVBoxLayout()
        layout.addWidget(withdraw_history_table)
        withdraw_history_window.setLayout(layout)
        withdraw_history_window.exec()

    def update_customer_table(self):
        self.customer_table.setRowCount(0)  # Limpiar la tabla

        query = """
            SELECT 
                customers.name, 
                COALESCE(total_debt.total_debt, 0) AS total_debt, 
                last_payment.last_payment_date, 
                last_payment.last_payment_amount
            FROM customers
            -- Subconsulta para obtener la suma de las deudas pendientes
            LEFT JOIN (
                SELECT customer_id, SUM(remaining_amount) AS total_debt
                FROM debts
                WHERE status IN ('pendiente', 'parcialmente pagada')
                GROUP BY customer_id
            ) total_debt ON customers.id = total_debt.customer_id
            -- Subconsulta para obtener la última fecha y monto de pago
            LEFT JOIN (
                SELECT p1.customer_id, p1.date AS last_payment_date, p1.amount AS last_payment_amount
                FROM payments p1
                WHERE p1.rowid = (
                    SELECT p2.rowid
                    FROM payments p2
                    WHERE p2.customer_id = p1.customer_id
                    ORDER BY p2.date DESC, p2.rowid DESC
                    LIMIT 1
                )
            ) last_payment ON customers.id = last_payment.customer_id
            GROUP BY customers.name, total_debt.total_debt;
        """
        c.execute(query)
        customers = c.fetchall()

        for row_number, row_data in enumerate(customers):
            self.customer_table.insertRow(row_number)
            for column_number, data in enumerate(row_data):
                if column_number == 1 and data is None:  # Columna de deuda total
                    data = "$0.00"
                elif column_number == 2 and data is None:  # Columna de fecha
                    data = "-"
                elif column_number == 3 and data is None:  # Columna de monto del pago
                    data = "$0.00"
                else:
                    if column_number == 1 or column_number == 3:  # Columnas monetarias
                        data = f"${data:.2f}" if data is not None else "$0.00"
                    else:
                        data = str(data) if data is not None else ""

                self.customer_table.setItem(row_number, column_number, QTableWidgetItem(data))

    def show_payment_history(self):
        selected_row = self.customer_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, 'Advertencia', 'Por favor, seleccione un cliente.')
            return

        customer_name = self.customer_table.item(selected_row, 0).text()
        customer_id_query = "SELECT id FROM customers WHERE name = ?"
        c.execute(customer_id_query, (customer_name,))
        customer_id = c.fetchone()[0]

        # Crear una ventana para mostrar el historial de pagos
        payment_history_window = QDialog(self)
        payment_history_window.setWindowTitle(f"Historial de pagos de {customer_name}")
        
        # Ajustar tamaño mínimo de la ventana (por ejemplo, 600x400 píxeles)
        payment_history_window.setMinimumSize(800, 600)

        payment_table = QTableWidget()
        payment_table.setColumnCount(3)
        payment_table.setHorizontalHeaderLabels(['Nombre', 'Monto Pagado', 'Fecha'])
        payment_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Consultar los pagos del cliente
        query = "SELECT amount, date FROM payments WHERE customer_id = ?"
        c.execute(query, (customer_id,))
        payments = c.fetchall()

        payment_table.setRowCount(len(payments))
        for row, payment in enumerate(payments):
            payment_table.setItem(row, 0, QTableWidgetItem(customer_name))
            payment_table.setItem(row, 1, QTableWidgetItem(f"${payment[0]:.2f}"))
            payment_table.setItem(row, 2, QTableWidgetItem(payment[1]))

        layout = QVBoxLayout()
        layout.addWidget(payment_table)
        payment_history_window.setLayout(layout)
        payment_history_window.exec()


    def calculate_revenue(self):
        selected_date = self.date_input.date().toString('dd-MM-yy')
        selected_date = f"{selected_date}%"

        # Calcular la recaudación total del día excluyendo las ventas a crédito
        c.execute("""
            SELECT SUM(total) 
            FROM sales_summary 
            WHERE date LIKE ? AND payment_method NOT IN ('A Crédito', 'Pago de deuda')
        """, (selected_date,))
        total_revenue_result = c.fetchone()
        total_revenue = total_revenue_result[0] if total_revenue_result and total_revenue_result[0] is not None else 0.0

        # Incluir pagos de deuda en la recaudación total
        c.execute("""
            SELECT SUM(amount)
            FROM payments
            WHERE date LIKE ?
        """, (selected_date,))
        debt_payments_result = c.fetchone()
        debt_payments = debt_payments_result[0] if debt_payments_result and debt_payments_result[0] is not None else 0.0

        total_revenue += debt_payments

        # Calcular el costo total de los productos vendidos en el día excluyendo las ventas a crédito
        c.execute("""
            SELECT SUM(p.cost_price * sd.quantity)
            FROM sales_details sd
            JOIN products p ON sd.product_id = p.id
            JOIN sales_summary ss ON sd.sale_id = ss.id
            WHERE ss.date = ? AND ss.payment_method != 'A Crédito'
        """, (selected_date,))
        total_cost_result = c.fetchone()
        total_cost = total_cost_result[0] if total_cost_result and total_cost_result[0] is not None else 0.0

        # Calcular la ganancia del día
        total_profit = total_revenue - total_cost
        

        self.revenue_label.setText(
            f'RECAUDACIÓN DEL DÍA: ${total_revenue:.2f}<br>'
            f'<span style="font-size: small;">*No incluye ventas a crédito</span><br>'
        )

        self.daily_profit_label.setText(f'GANANCIA DEL DÍA: ${total_profit:.2f}')

        # Actualizar la tabla de ventas diarias
        self.daily_sales_report_table.setRowCount(0)
        if total_revenue > 0:
            # Obtener los pagos y asociarlos con ventas por monto
            c.execute("""
                SELECT 
                    CASE WHEN ss.payment_method = 'Pago de deuda' THEN c.name ELSE p.name END AS product_name,
                    SUM(CASE WHEN sd.product_id IS NOT NULL THEN sd.quantity ELSE 0 END) AS total_quantity,
                    CASE WHEN ss.payment_method = 'Pago de deuda' THEN SUM(pay.amount) ELSE SUM(COALESCE(sd.total, 0)) END AS total_sales,
                    ss.date,
                    COALESCE(AVG(p.cost_price), 0) AS cost_price,
                    COALESCE(AVG(p.profit_margin), 0) AS profit_margin,
                    ss.payment_method
                FROM sales_summary ss
                LEFT JOIN sales_details sd ON ss.id = sd.sale_id
                LEFT JOIN products p ON sd.product_id = p.id
                LEFT JOIN payments pay ON ss.payment_method = 'Pago de deuda' AND pay.date = ss.date
                LEFT JOIN customers c ON pay.customer_id = c.id
                WHERE ss.date = ?
                GROUP BY c.name, ss.payment_method, ss.date, product_name
            """, (selected_date,))
            daily_sales = c.fetchall()
            for row_number, row_data in enumerate(daily_sales):
                self.daily_sales_report_table.insertRow(row_number)
                for column_number, data in enumerate(row_data):
                    item = QTableWidgetItem(str(data))
                    # Si es un pago de deuda, ajustar las columnas de cantidad, precio de costo y margen de ganancia
                    if row_data[6] == 'Pago de deuda':
                        if column_number in [1, 4, 5]:  # columnas de cantidad, precio de costo y margen de ganancia
                            item.setText('-')
                    self.daily_sales_report_table.setItem(row_number, column_number, item)

        # Calcular el total de retiros de efectivo del día
        c.execute("SELECT SUM(amount) FROM cash_withdrawals WHERE date = ?", (selected_date,))
        total_withdrawals_result = c.fetchone()
        total_withdrawals = total_withdrawals_result[0] if total_withdrawals_result and total_withdrawals_result[0] is not None else 0.0

        # Calcular el efectivo ingresado en caja
        c.execute("""
            SELECT SUM(total) 
            FROM sales_summary 
            WHERE payment_method = 'Efectivo' AND date = ?
        """, (selected_date,))        
        daily_cash_result = c.fetchone()
        daily_cash = daily_cash_result[0] if daily_cash_result and daily_cash_result[0] is not None else 0.0

        # Calcular la ganancia por método de pago, incluyendo pagos de deuda
        c.execute("""
            SELECT ss.payment_method, 
                SUM(COALESCE(sd.total, 0) + COALESCE(pay.amount, 0)), 
                SUM(COALESCE(sd.total, 0) - COALESCE(p.cost_price * sd.quantity, 0))
            FROM sales_summary ss
            LEFT JOIN sales_details sd ON ss.id = sd.sale_id
            LEFT JOIN products p ON sd.product_id = p.id
            LEFT JOIN payments pay ON ss.payment_method = 'Pago de deuda' AND pay.date = ss.date
            WHERE ss.date = ? and ss.payment_method != 'A Crédito'
            GROUP BY ss.payment_method
        """, (selected_date,))
        profit_by_payment_method = c.fetchall()

        profit_text = ""
        total_method_profit = 0.0
        for method, total, profit in profit_by_payment_method:
            # Asegúrate de que profit no sea None antes de formatear
            profit = profit if profit is not None else 0.0
            profit_text += f"{method}: ${profit:.2f}\n"
            total_method_profit += profit
            
            
        formatted_profit_text = profit_text.replace("\n", "<br>")

        self.daily_profit_label.setText(
            f'GANANCIA DEL DÍA: ${total_profit:.2f}<br>'
            f'<span style="font-size: small;">*No incluye ventas a crédito</span><br><br>'
            f'{formatted_profit_text}'
        )

        # Mostrar el efectivo ingresado y el efectivo retirado
        self.cash_in_label.setText(f'EFECTIVO INGRESADO: ${daily_cash:.2f}\nEFECTIVO RETIRADO: ${total_withdrawals:.2f}')
        self.adjust_column_width(self.daily_sales_report_table)
    
    def generate_monthly_report(self):
        start_date = self.start_date_input.date().toString('yyyy-MM-dd')
        end_date = self.end_date_input.date().toString('yyyy-MM-dd')

        # Calcular la recaudación total del período excluyendo las ventas a crédito
        c.execute("""
            SELECT SUM(total) 
            FROM sales_summary 
            WHERE date BETWEEN ? AND ? AND payment_method NOT IN ('A Crédito', 'Pago de deuda')
        """, (start_date, end_date))
        total_revenue_result = c.fetchone()
        total_revenue = total_revenue_result[0] if total_revenue_result and total_revenue_result[0] is not None else 0.0

        # Incluir pagos de deuda en la recaudación total
        c.execute("""
            SELECT SUM(amount)
            FROM payments
            WHERE date BETWEEN ? AND ?
        """, (start_date, end_date))
        debt_payments_result = c.fetchone()
        debt_payments = debt_payments_result[0] if debt_payments_result and debt_payments_result[0] is not None else 0.0

        total_revenue += debt_payments

        # Calcular el costo total de los productos vendidos en el período excluyendo las ventas a crédito
        c.execute("""
            SELECT SUM(p.cost_price * sd.quantity) 
            FROM sales_details sd
            JOIN products p ON sd.product_id = p.id
            JOIN sales_summary ss ON sd.sale_id = ss.id
            WHERE ss.date BETWEEN ? AND ? AND ss.payment_method != 'A Crédito'
        """, (start_date, end_date))
        total_cost_result = c.fetchone()
        total_cost = total_cost_result[0] if total_cost_result and total_cost_result[0] is not None else 0.0

        # Calcular el total de retiros de efectivo del período
        c.execute("SELECT SUM(amount) FROM cash_withdrawals WHERE date BETWEEN ? AND ?", (start_date, end_date))
        total_withdrawals_result = c.fetchone()
        total_withdrawals = total_withdrawals_result[0] if total_withdrawals_result and total_withdrawals_result[0] is not None else 0.0

        # Calcular la ganancia del período
        total_profit = total_revenue - total_cost
        
        self.monthly_sales_label.setText(
            f'VENTAS: ${total_revenue:.2f}<br>'
            f'<span style="font-size: small;">*No incluye ventas a crédito</span><br>'
        )

        self.monthly_profit_label.setText(f'GANANCIAS: ${total_profit:.2f}')

        # Actualizar la tabla de ventas mensuales
        self.monthly_sales_report_table.setRowCount(0)
        if total_revenue > 0:
            # Incluir ventas y pagos de deuda, excluyendo ventas a crédito
            c.execute("""
                SELECT 
                    CASE WHEN ss.payment_method = 'Pago de deuda' THEN c.name ELSE p.name END AS product_name,
                    SUM(sd.quantity) AS total_quantity,
                    CASE WHEN ss.payment_method = 'Pago de deuda' THEN SUM(pay.amount) ELSE SUM(COALESCE(sd.total, 0)) END AS total_sales,
                    ss.date,
                    COALESCE(AVG(p.cost_price), 0) AS cost_price,
                    COALESCE(AVG(p.profit_margin), 0) AS profit_margin,
                    ss.payment_method
                FROM sales_summary ss
                LEFT JOIN sales_details sd ON ss.id = sd.sale_id
                LEFT JOIN products p ON sd.product_id = p.id
                LEFT JOIN payments pay ON ss.payment_method = 'Pago de deuda' AND pay.date = ss.date
                LEFT JOIN customers c ON pay.customer_id = c.id
                WHERE ss.date BETWEEN ? AND ?
                GROUP BY c.name, ss.payment_method, ss.date, product_name
            """, (start_date, end_date))
            monthly_sales = c.fetchall()
            for row_number, row_data in enumerate(monthly_sales):
                self.monthly_sales_report_table.insertRow(row_number)
                for column_number, data in enumerate(row_data):
                    item = QTableWidgetItem(str(data))
                    # Si es un pago de deuda, ajustar las columnas de cantidad, precio de costo y margen de ganancia
                    if row_data[6] == 'Pago de deuda':
                        if column_number in [1, 4, 5]:  # columnas de cantidad, precio de costo y margen de ganancia
                            item.setText('-')
                    self.monthly_sales_report_table.setItem(row_number, column_number, item)

        # Calcular la ganancia por método de pago, incluyendo pagos de deuda
        c.execute("""
            SELECT ss.payment_method, 
                SUM(COALESCE(sd.total, 0) + COALESCE(pay.amount, 0)), 
                SUM(COALESCE(sd.total, 0) - COALESCE(p.cost_price * sd.quantity, 0))
            FROM sales_summary ss
            LEFT JOIN sales_details sd ON ss.id = sd.sale_id
            LEFT JOIN products p ON sd.product_id = p.id
            LEFT JOIN payments pay ON ss.payment_method = 'Pago de deuda' AND pay.date = ss.date
            WHERE ss.date BETWEEN ? AND ? and ss.payment_method != 'A Crédito'
            GROUP BY ss.payment_method
        """, (start_date, end_date))
        profit_by_payment_method = c.fetchall()

        profit_text = ""
        total_method_profit = 0.0
        for method, total, profit in profit_by_payment_method:
            # Asegúrate de que profit no sea None antes de formatear
            profit = profit if profit is not None else 0.0
            profit_text += f"{method}: ${profit:.2f}\n"
            total_method_profit += profit
            
            formatted_profit_text = profit_text.replace("\n", "<br>")

        self.monthly_profit_label.setText(
            f'GANANCIAS: ${total_profit:.2f}<br>'
            f'<span style="font-size: small;">*No incluye ventas a crédito</span><br><br>'
            f'{formatted_profit_text}'
        )

        self.adjust_column_width(self.monthly_sales_report_table)

    def adjust_column_width(self, table_widget):
        for column in range(table_widget.columnCount()):
            table_widget.resizeColumnToContents(column)

                
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return:
            if self.tab_widget.currentIndex() == 0:  # Pestaña de Productos
                barcode = self.sale_barcode_input.text().strip()
                if barcode:
                    self.update_product_barcode()
                else:
                    self.auto_fill_product_name()
            elif self.tab_widget.currentIndex() == 1:  # Pestaña de Ventas
                barcode = self.sale_barcode_input.text().strip()
                self.load_product_by_barcode(barcode)
            
    def withdraw_cash(self):
        """Realiza un retiro de efectivo y lo registra en la base de datos."""
        amount = self.withdrawal_amount_input.value()
        # Calcular el efectivo ingresado en caja
        selected_date = self.date_input.date().toString('yyyy-MM-dd')
        c.execute("SELECT SUM(total) FROM sales_summary WHERE payment_method = 'Efectivo' AND date = ?", (selected_date,))        
        daily_cash_result = c.fetchone()
        daily_cash = daily_cash_result[0] if daily_cash_result and daily_cash_result[0] is not None else 0.0


        if amount <= 0:
            QMessageBox.warning(self, "Advertencia", "La cantidad a retirar debe ser mayor que 0.")
            return
        if amount > daily_cash:
            QMessageBox.warning(self, "Error", "No hay el suficiente efectivo en caja.")
            return

        current_date = datetime.today().strftime('%Y-%m-%d')
        current_time = datetime.now().strftime('%H:%M:%S')

        # Registrar el retiro en la base de datos
        c.execute("INSERT INTO cash_withdrawals (amount, date, time) VALUES (?, ?, ?)", (amount, current_date, current_time))
        QMessageBox.information(self, "Éxito", f"Se han retirado ${amount:.2f} de la caja.")
        self.withdrawal_amount_input.setValue(0)  # Restablecer el campo de entrada de la cantidad

    def register_payment(self, customer_name, debt_id, payment_amount):
        try:
            # Obtener el ID del cliente según el nombre
            c.execute("SELECT id FROM customers WHERE name=?", (customer_name,))
            customer_id = c.fetchone()[0]

            # Registrar el pago en la tabla payments
            c.execute("""
                INSERT INTO payments (debt_id, customer_id, amount, date)
                VALUES (?, ?, ?, ?)
            """, (debt_id, customer_id, payment_amount, date.today().isoformat()))

            conn.commit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Se produjo un error al registrar el pago: {e}")


    def add_customer(self):
        customer_name = self.customer_name_input.text()
        if customer_name:
            try:
                c.execute("INSERT INTO customers (name) VALUES (?)", (customer_name,))
                conn.commit()
                self.update_customer_table()
                QMessageBox.information(self, "Éxito", "Cliente agregado correctamente")
                self.customer_name_input.clear()
            except sqlite3.IntegrityError:
                QMessageBox.critical(self, "Error", "El cliente ya existe")
        else:
            QMessageBox.critical(self, "Error", "Nombre del cliente es obligatorio")

    def load_customer_to_form(self, row):
        self.customer_name_input.setText(self.customer_table.item(row, 0).text())

    def register_debt(self, customer_name, total_sale, sale_id):
        try:
            # Obtener el ID del cliente
            query = "SELECT id FROM customers WHERE name = ?"
            c.execute(query, (customer_name,))
            result = c.fetchone()

            if not result:
                # Si el cliente no existe, crear un nuevo cliente
                self.create_customer(customer_name)
                
                # Volver a buscar el ID del cliente después de crearlo
                c.execute(query, (customer_name,))
                result = c.fetchone()

                if not result:
                    QMessageBox.critical(self, 'Error', 'No se pudo crear el cliente.')
                    return

            customer_id = result[0]

            # Registrar la deuda en la tabla debts
            insert_debt_query = """
                INSERT INTO debts (sale_id, customer_id, original_amount, remaining_amount, date, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            current_date = date.today().isoformat()
            c.execute(insert_debt_query, (sale_id, customer_id, total_sale, total_sale, current_date, 'pendiente'))

            # Confirmar los cambios en la base de datos
            conn.commit()
            QMessageBox.information(self, 'Éxito', f'Deuda de ${total_sale:.2f} registrada con éxito para el cliente {customer_name}.')

            # Actualizar la pestaña de deudas
            self.update_debt_table()
            self.update_customer_table()
            self.load_customers_to_combobox()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Se produjo un error al registrar la deuda: {e}")

    def create_customer(self, customer_name):
        try:
            # Crear un nuevo cliente en la base de datos
            insert_customer_query = "INSERT INTO customers (name) VALUES (?)"
            c.execute(insert_customer_query, (customer_name,))

            # Confirmar los cambios en la base de datos
            conn.commit()
            QMessageBox.information(self, 'Éxito', f'Cliente "{customer_name}" creado con éxito.')
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Se produjo un error al crear el cliente: {e}")




if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create('Fusion'))
    app.setStyleSheet("""
    QPushButton {
        background-color: #dddddd;
        color: black;
        font-weight: 600;
        border: none;
        padding: 4px 12px;
        font-size: 18px;
    }
    QLineEdit {
        font-weight: 600;
        font-size: 18px;
    }
    QWidget {
        font-size: 18px;
    }
    QSpinBox {
        font-size: 18px;
    }
    QDoubleSpinBox {
        font-size: 18px;
    }
    QDateEdit {
        font-size: 18px;
    }
    QLabel {
        color: black;
        font-size: 16px;
        font-weight: 600;
    }
    QTableWidget {
        background-color: #ececec;
        font-size: 18px;
        font-weight: 500;
    }
    """)
    
    ex = StockManagementApp()
    ex.show()

    sys.excepthook = handle_exception
    sys.exit(app.exec())
