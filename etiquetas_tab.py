from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QLineEdit, QComboBox, QFileDialog, QMessageBox,
                            QScrollArea, QSpinBox, QDoubleSpinBox, QFormLayout, QCompleter)
from PyQt6.QtCore import Qt, QBuffer, QStringListModel
from PyQt6.QtGui import QPixmap, QImage
from db_postgres import buscar_producto, buscar_coincidencias_producto
from logica_codigo import generar_codigo_variable_ean13, generar_csv_etiqueta, imprimir_etiqueta, imprimir_pdf_directo
import os
import sys
import io
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
from signals import signals
import win32print  # Add this import for printer selection


class EtiquetasTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("etiquetas")
        self.init_ui()
        self.cargar_productos()
        
    def init_ui(self):
        # Layout principal
        main_layout = QVBoxLayout()
                
        # Contenedor para formulario y previsualización
        content_layout = QHBoxLayout()
        
        # Panel izquierdo - Formulario
        form_widget = QWidget()
        form_layout = QFormLayout()
        form_widget.setObjectName("panelFormulario")
        
        # Campo de búsqueda con autocompletado
        self.busqueda_producto = QLineEdit()
        self.busqueda_producto.setPlaceholderText("Buscar producto por nombre o código")
        self.busqueda_producto.textChanged.connect(self.actualizar_sugerencias)
        self.busqueda_producto.returnPressed.connect(self.buscar_producto_enter)
        form_layout.addRow("Buscar:", self.busqueda_producto)
        
        # Configurar el autocompletado
        self.completer = QCompleter([])
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.busqueda_producto.setCompleter(self.completer)
        self.completer.activated.connect(self.seleccionar_producto_completer)
        
        # Código de producto
        self.codigo_input = QLineEdit()
        self.codigo_input.setReadOnly(True)
        form_layout.addRow("Código:", self.codigo_input)
        
        # Nombre del producto
        self.nombre_input = QLineEdit()
        form_layout.addRow("Nombre:", self.nombre_input)
        
        # Ingredientes
        self.ingredientes_input = QLineEdit()
        self.ingredientes_input.setPlaceholderText("Ingredientes del producto")
        self.ingredientes_input.textChanged.connect(self.generar_vista_previa)
        form_layout.addRow("Ingredientes:", self.ingredientes_input)
        
        # Peso
        self.peso_input = QDoubleSpinBox()
        self.peso_input.setObjectName("peso_input")  # Add object name for CSS styling
        self.peso_input.setRange(0.00001, 1000.0)
        self.peso_input.setValue(1.0)
        self.peso_input.setSingleStep(0.1)  # Cambiar el paso a 0.1kg
        self.peso_input.setSuffix(" kg")
        self.peso_input.setDecimals(3)
        self.peso_input.setSingleStep(0.1)  # Cambiar el paso a 0.1kg
        self.peso_input.setMinimumHeight(40)
        self.peso_input.setMinimumWidth(150)
        self.peso_input.valueChanged.connect(self.generar_vista_previa)
        form_layout.addRow("Peso:", self.peso_input)
                
        self.impresora_combo = QComboBox()
        self.impresora_combo.setObjectName("impresora_combo")
        self.cargar_impresoras()
        form_layout.addRow("Impresora:", self.impresora_combo)

        
        # Botones de acción
        buttons_layout = QHBoxLayout()
        
        self.btn_generar_preview = QPushButton("Generar Vista Previa")
        self.btn_generar_preview.setObjectName("btn_generar_preview")
        self.btn_generar_preview.clicked.connect(self.generar_vista_previa)
        buttons_layout.addWidget(self.btn_generar_preview)
        
        self.btn_imprimir = QPushButton("Imprimir Etiqueta")
        self.btn_imprimir.setObjectName("btn_imprimir")
        self.btn_imprimir.clicked.connect(self.imprimir_pdf_directo)
        buttons_layout.addWidget(self.btn_imprimir)
        
        # Nuevo botón para guardar como PDF
        self.btn_guardar_pdf = QPushButton("Guardar como PDF")
        self.btn_guardar_pdf.setObjectName("btn_guardar_pdf")
        self.btn_guardar_pdf.clicked.connect(self.guardar_etiqueta_pdf)
        buttons_layout.addWidget(self.btn_guardar_pdf)
                
        form_layout.addRow("", buttons_layout)
        form_widget.setLayout(form_layout)
        content_layout.addWidget(form_widget, 1)
        
        # Panel derecho - Previsualización
        preview_widget = QWidget()
        preview_layout = QVBoxLayout()
        preview_widget.setObjectName("panelPreview")
        preview_widget.setMinimumWidth(400)  # Ensure preview panel has enough width

        preview_title = QLabel("Vista Previa de la Etiqueta")
        preview_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(preview_title)
        
        # Área de previsualización con scroll
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("scrollPreview")
        
        # Create a container widget to center the preview label
        preview_container = QWidget()
        preview_container_layout = QVBoxLayout(preview_container)
        preview_container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.preview_label = QLabel("Genere una vista previa para ver la etiqueta")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setFixedSize(384, 576)  # Exact 4x6 inch size at 96 DPI
        self.preview_label.setObjectName("labelPreview")
        self.preview_label.setScaledContents(True)
        
        preview_container_layout.addWidget(self.preview_label)
        scroll_area.setWidget(preview_container)
        preview_layout.addWidget(scroll_area)
        
        # Botón para guardar la previsualización
        self.btn_guardar_preview = QPushButton("Guardar Vista Previa")
        self.btn_guardar_preview.setObjectName("btn_guardar_preview")
        self.btn_guardar_preview.clicked.connect(self.guardar_vista_previa)
        preview_layout.addWidget(self.btn_guardar_preview)
        
        preview_widget.setLayout(preview_layout)
        content_layout.addWidget(preview_widget, 2)
        
        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)
        
        # Conectar señales para actualización de productos
        signals.producto_actualizado.connect(self.cargar_productos)
    
    def cargar_productos(self):
        """Carga los productos desde la base de datos para el autocompletado"""
        self.productos = buscar_producto()
        self.nombres_productos = []
        
        for producto in self.productos:
            if producto[3] == 1:
                codigo = producto[1] or ""
                nombre = producto[2]
                self.nombres_productos.append(f"{codigo} - {nombre}")
        
        # Actualizar el modelo del completer
        model = QStringListModel()
        model.setStringList(self.nombres_productos)
        self.completer.setModel(model)
    
    def actualizar_sugerencias(self, texto):
        """Actualiza las sugerencias del autocompletado según el texto ingresado"""
        if len(texto) >= 2:  # Solo buscar si hay al menos 2 caracteres
            sugerencias = []
            for producto in self.productos:
                if producto[3] == 1:
                    codigo = producto[1] or ""
                    nombre = producto[2]
                    texto_producto = f"{codigo} - {nombre}"
                    if texto.lower() in texto_producto.lower():
                        sugerencias.append(texto_producto)
            
            # Actualizar el modelo del completer
            model = QStringListModel()
            model.setStringList(sugerencias)
            self.completer.setModel(model)
            self.completer.complete()

    def buscar_producto_enter(self):
        """Busca y selecciona el producto cuando se presiona Enter en el campo de búsqueda"""
        texto = self.busqueda_producto.text().lower().strip()
        
        if not texto:
            return
        
        # Imprimir para depuración
        print(f"Buscando producto con texto: '{texto}'")
        
        # Buscar coincidencias exactas primero
        for producto in self.productos:
            codigo = producto[1] or ""
            nombre = producto[2].lower()
            texto_producto = f"{codigo} - {nombre}".lower()
            
            # Verificar coincidencia exacta con código, nombre o texto completo
            if (texto == codigo.lower() or 
                texto == nombre or 
                texto == texto_producto or
                texto in texto_producto):
                
                print(f"Coincidencia encontrada: {producto[2]}")
                self.cargar_datos_producto(producto)
                return
        
        # Si no hay coincidencia exacta, buscar coincidencias parciales
        mejores_coincidencias = []
        
        for producto in self.productos:
            codigo = producto[1] or ""
            nombre = producto[2].lower()
            texto_producto = f"{codigo} - {nombre}".lower()
            
            # Verificar si el texto está contenido en el código, nombre o texto completo
            if (texto in codigo.lower() or 
                texto in nombre or 
                texto in texto_producto):
                
                # Calcular un puntaje de coincidencia (menor es mejor)
                if nombre.startswith(texto):
                    puntaje = 0  # Prioridad máxima si comienza con el texto
                elif codigo.lower() == texto:
                    puntaje = 1  # Alta prioridad si coincide con el código
                else:
                    # Buscar la posición de la coincidencia
                    pos_nombre = nombre.find(texto)
                    pos_codigo = codigo.lower().find(texto)
                    pos_texto = texto_producto.find(texto)
                    
                    # Tomar la mejor posición (la más cercana al inicio)
                    puntaje = min(
                        pos_nombre if pos_nombre != -1 else 999,
                        pos_codigo if pos_codigo != -1 else 999,
                        pos_texto if pos_texto != -1 else 999
                    )
                
                mejores_coincidencias.append((puntaje, producto))
        
        # Ordenar por puntaje (las mejores coincidencias primero)
        mejores_coincidencias.sort(key=lambda x: x[0])
        
        # Seleccionar la mejor coincidencia si existe
        if mejores_coincidencias:
            mejor_producto = mejores_coincidencias[0][1]
            print(f"Mejor coincidencia: {mejor_producto[2]} (puntaje: {mejores_coincidencias[0][0]})")
            self.cargar_datos_producto(mejor_producto)
        else:
            print("No se encontraron coincidencias")
            QMessageBox.information(self, "Búsqueda", 
                                f"No se encontró ningún producto que coincida con '{texto}'")

    def seleccionar_producto_completer(self, texto_seleccionado):
        """Carga los datos del producto seleccionado desde el autocompletado"""
        for producto in self.productos:
            codigo = producto[1] or ""
            nombre = producto[2]
            texto_producto = f"{codigo} - {nombre}"
            
            if texto_producto == texto_seleccionado:
                self.cargar_datos_producto(producto)
                break
    
    def cargar_datos_producto(self, producto):
        """Carga los datos del producto en los campos del formulario"""
        # Mapeo de índices: [id, codigo_barras, nombre, venta_por_peso, disponible, precio_costo, precio_venta, margen_ganancia]
        self.codigo_input.setText(producto[1] or "")  # código_barras
        self.nombre_input.setText(producto[2])  # nombre
        
        # Guardar el precio de venta para cálculos posteriores
        self.precio_venta = float(producto[6] or 0)  # precio_venta
        
        # Limpiar ingredientes para que el usuario los ingrese
        self.ingredientes_input.clear()
        
        # Si el producto se vende por peso, habilitar el campo de peso
        venta_por_peso = producto[3] == 1
        self.peso_input.setEnabled(venta_por_peso)
        if not venta_por_peso:
            self.peso_input.setValue(1.0)
            QMessageBox.information(self, "Producto por unidad", 
                                   "Este producto se vende por unidad, no por peso.")
        
        # Generar vista previa automáticamente
        self.generar_vista_previa()
    
    def seleccionar_plantilla(self):
        """Abre un diálogo para seleccionar la plantilla de BarTender"""
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Plantilla BarTender", "", "Archivos BarTender (*.btw)"
        )
        if ruta:
            self.ruta_plantilla.setText(ruta)
    
    def generar_vista_previa(self):
        """Actualiza la vista previa de la etiqueta"""
        if not self.codigo_input.text() or not self.nombre_input.text():
            self.preview_label.setText("Seleccione un producto para generar la vista previa")
            return
        
        try:
            # Generar el código de barras
            codigo_barras = generar_codigo_variable_ean13(
                self.codigo_input.text(), self.peso_input.value()
            )
            
            # Verificar que el código de barras se generó correctamente
            if not codigo_barras:
                raise ValueError("No se pudo generar el código de barras")
            
            # Calcular el precio basado en el peso
            peso = float(self.peso_input.value())
            precio_total = round(peso * self.precio_venta, 2)
            
            # Datos del producto (nombre en mayúsculas)
            datos_producto = {
                "Codigo": self.codigo_input.text(),
                "Nombre": self.nombre_input.text().upper(),  # Convertir a mayúsculas
                "Ingredientes": self.ingredientes_input.text(),
                "CodigoBarras": codigo_barras,
                "Peso": str(self.peso_input.value()),
                "PrecioVenta": self.precio_venta,
                "PrecioTotal": precio_total
            }
            
            # Crear una sola etiqueta
            imagen_etiqueta = self.generar_imagen_etiqueta(datos_producto)
            
            # Redimensionar para la vista previa manteniendo la proporción
            # Ajustar para que se vea completa en la vista previa
            preview_width = 384  # Ancho para la vista previa
            preview_height = 576  # 6 pulgadas a 96 DPI
            ratio = imagen_etiqueta.height / imagen_etiqueta.width
            
            # Redimensionar con alta calidad
            preview_img = imagen_etiqueta.resize((preview_width, preview_height), Image.LANCZOS)
            
            # Convertir la imagen PIL a QPixmap para mostrarla
            buffer = QBuffer()
            buffer.open(QBuffer.OpenModeFlag.ReadWrite)
            preview_img.save(buffer, format="PNG")
            buffer.seek(0)
            
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.data())
            
            # Mostrar la imagen en el label
            self.preview_label.setPixmap(pixmap)
            self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.preview_label.setScaledContents(True)  # No estirar la imagen

        except Exception as e:
            import traceback
            error_detallado = traceback.format_exc()
            print(f"Error detallado: {error_detallado}")
            QMessageBox.warning(self, "Error", f"Error al generar la vista previa: {str(e)}")
            self.preview_label.setText(f"Error: {str(e)}")

    def generar_imagen_etiqueta(self, datos_producto):
        """
        Genera una imagen de la etiqueta con el código de barras y los datos del producto.
        Tamaño ajustado para etiquetas de 4x6 pulgadas (aproximadamente 384 x 576 píxeles a 96 DPI)
        """
        # Aumentar la resolución para mejor calidad (de 96 DPI a 300 DPI)
        # 4x6 pulgadas a 300 DPI = 1200 x 1800 píxeles
        width, height = 1200, 1800
        etiqueta = Image.new('RGB', (width, height), color='white')

        from logica_codigo import resource_path
        
        # Crear un objeto Draw para dibujar en la etiqueta
        draw = ImageDraw.Draw(etiqueta)
        try:
            # Cargar fuentes usando resource_path
            arial_path = resource_path('fonts/ARIAL.TTF')
            arialbd_path = resource_path('fonts/ARIALBD.TTF')
            
            font_normal = ImageFont.truetype(arial_path, 70)
            font_ingredients = ImageFont.truetype(arial_path, 50)
            font_title = ImageFont.truetype(arialbd_path, 90)
            
        except Exception as e:
            print(f"Error cargando fuentes: {e}, usando fuentes predeterminadas")
            font_normal = ImageFont.load_default()
            font_title = ImageFont.load_default()

        
        # Calcular márgenes y espaciado
        margin_x = 70  # Margen horizontal
        margin_y = 40  # Margen vertical
        line_spacing = 15  # Espacio entre líneas (reducido)
        
        # Espacio entre secciones (reducido a 1 cm a 300 DPI ≈ 118 pixels)
        section_spacing = 70  # Reducido para ajustar mejor el contenido
        
        # Primero, calcular el espacio total que ocuparán todos los elementos
        # para poder distribuirlos uniformemente
        
        # Calcular altura del nombre (ya en mayúsculas desde el método generar_vista_previa)
        nombre_height = font_title.size + line_spacing
        
        # Calcular altura de los ingredientes
        ingredientes = datos_producto['Ingredientes']
        ingredientes_height = 0
        
        if ingredientes:
            # Título de ingredientes
            ingredientes_height += font_normal.size + line_spacing
            
            # Dividir los ingredientes por comas o puntos y comas si existen
            if ',' in ingredientes:
                lista_ingredientes = [item.strip() for item in ingredientes.split(',')]
            elif ';' in ingredientes:
                lista_ingredientes = [item.strip() for item in ingredientes.split(';')]
            else:
                # Si no hay separadores, tratar como un solo elemento
                lista_ingredientes = [ingredientes]
            
            # Calcular altura para cada ingrediente (considerando posible ajuste de línea)
            max_width = width - margin_x * 2 - 40  # Ancho máximo para el texto
            
            for ingrediente in lista_ingredientes:
                if ingrediente:  # Evitar elementos vacíos
                    palabras = ingrediente.split()
                    linea_actual = "- "
                    lineas_ingrediente = 1
                    
                    for palabra in palabras:
                        # Verificar si agregar la palabra excede el ancho máximo
                        linea_prueba = linea_actual + palabra + " "
                        if draw.textlength(linea_prueba, font=font_ingredients) <= max_width:
                            linea_actual = linea_prueba
                        else:
                            # Nueva línea
                            lineas_ingrediente += 1
                            linea_actual = "  " + palabra + " "  # Indentación para continuación
                    
                    ingredientes_height += lineas_ingrediente * (font_normal.size + line_spacing)
        else:
            # Si no hay ingredientes, solo una línea
            ingredientes_height += font_normal.size + line_spacing
        
        # Altura del peso
        peso_height = font_normal.size + line_spacing
        
        # Calcular altura aproximada del código de barras (80% del ancho)
        barcode_width = int(width * 0.8)
        barcode_height_approx = int(barcode_width * 0.3)  # Proporción aproximada (reducida)
        
        # Altura del texto del código de barras
        codigo_height = font_normal.size + line_spacing
        
        # Altura total estimada del contenido
        contenido_height = (
            nombre_height + 
            section_spacing + 
            ingredientes_height + 
            section_spacing + 
            peso_height + 
            section_spacing + 
            barcode_height_approx + 
            codigo_height
        )
        
        # Calcular el espacio vertical disponible
        espacio_disponible = height - contenido_height - margin_y * 2
        
        # Distribuir el espacio disponible para centrar verticalmente
        espacio_extra = espacio_disponible / 2 if espacio_disponible > 0 else 0
        
        # Posición vertical inicial ajustada para centrar todo el contenido
        y_pos = margin_y + espacio_extra
        
        # Nombre del producto (centrado y en mayúsculas)
        nombre = datos_producto["Nombre"]  # Ya está en mayúsculas desde generar_vista_previa
        nombre_width = draw.textlength(nombre, font=font_title)
        nombre_x = int((width - nombre_width) / 2)
        draw.text((nombre_x, int(y_pos)), nombre, fill='black', font=font_title)
        
        # Actualizar posición vertical después del nombre
        y_pos += nombre_height + section_spacing
        
        # Formatear los ingredientes como una lista con guiones
        if ingredientes:
            # Dibujar el título "Ingredientes:"
            draw.text((margin_x, int(y_pos)), "Ingredientes:", fill='black', font=font_normal)
            y_pos += font_normal.size + line_spacing
            
            # Dividir los ingredientes por comas o puntos y comas si existen
            if ',' in ingredientes:
                lista_ingredientes = [item.strip() for item in ingredientes.split(',')]
            elif ';' in ingredientes:
                lista_ingredientes = [item.strip() for item in ingredientes.split(';')]
            else:
                # Si no hay separadores, tratar como un solo elemento
                lista_ingredientes = [ingredientes]
            
            # Dibujar cada ingrediente como un elemento de lista
            for ingrediente in lista_ingredientes:
                if ingrediente:  # Evitar elementos vacíos
                    # Manejar texto largo con ajuste automático
                    max_width = width - margin_x * 2 - 40  # Ancho máximo para el texto
                    palabras = ingrediente.split()
                    linea_actual = "- "
                    
                    for palabra in palabras:
                        # Verificar si agregar la palabra excede el ancho máximo
                        linea_prueba = linea_actual + palabra + " "
                        if draw.textlength(linea_prueba, font=font_normal) <= max_width:
                            linea_actual = linea_prueba
                        else:
                            # Dibujar la línea actual y comenzar una nueva
                            draw.text((margin_x + 40, int(y_pos)), linea_actual, fill='black', font=font_normal)
                            y_pos += font_normal.size + line_spacing
                            linea_actual = "  " + palabra + " "  # Indentación para continuación
                    
                    # Dibujar la última línea
                    if linea_actual:
                        draw.text((margin_x + 40, int(y_pos)), linea_actual, fill='black', font=font_normal)
                        y_pos += font_normal.size + line_spacing
        else:
            # Si no hay ingredientes, mostrar un mensaje
            draw.text((margin_x, int(y_pos)), "Ingredientes: No especificados", fill='black', font=font_normal)
            y_pos += font_normal.size + line_spacing
        
        # Agregar espacio adicional después de los ingredientes
        y_pos += section_spacing
        
        # Agregar el peso y precio (centrado)
        peso_texto = f"Peso: {datos_producto['Peso']} kg   -   Precio: ${datos_producto['PrecioTotal']:.2f}"
        peso_width = draw.textlength(peso_texto, font=font_normal)
        peso_x = int((width - peso_width) / 2)
        draw.text((peso_x, int(y_pos)), peso_texto, fill='black', font=font_normal)
        
        # Actualizar posición vertical después del peso
        y_pos += peso_height + section_spacing
        
        # Agregar el código de barras
        codigo_producto = datos_producto["Codigo"].zfill(5)
        peso_g = int(float(datos_producto["Peso"]) * 1000)
        peso_str = str(peso_g).zfill(5)
        
        try:
            # Generar el código de barras directamente
            import tempfile
            temp_dir = tempfile.gettempdir()
            
            # Asegurarse de que el directorio temporal existe
            os.makedirs(temp_dir, exist_ok=True)
            
            # Crear el código de barras directamente con python-barcode
            raw_code_12 = "2" + "0" + codigo_producto + peso_str
            ean = barcode.get('ean13', raw_code_12, writer=ImageWriter())
            
            # Configurar opciones del escritor para mayor calidad
            options = {
                'module_height': 15.0,   # Altura de las barras
                'module_width': 0.8,     # Ancho de las barras
                'quiet_zone': 5.0,       # Espacio en blanco alrededor
                'font_size': 36,         # Reducir tamaño de fuente
                'text_distance': 10.0,   # Aumentar la distancia entre barras y texto
                'dpi': 300               # Alta resolución
            }
            
            # Guardar en un archivo temporal con extensión .png y opciones personalizadas
            temp_filename = os.path.join(temp_dir, f"temp_barcode_{codigo_producto}_{peso_str}")
            ean.save(temp_filename, options)
            
            # Verificar que el archivo existe
            if not os.path.exists(temp_filename + ".png"):
                raise FileNotFoundError(f"No se pudo crear el archivo: {temp_filename}.png")
            
            # Abrir la imagen del código de barras
            barcode_img = Image.open(temp_filename + ".png")
            
            # Calcular dimensiones proporcionales para el código de barras
            barcode_width = int(width * 0.8)  # 80% del ancho de la etiqueta
            barcode_ratio = barcode_img.height / barcode_img.width
            barcode_height = int(barcode_width * barcode_ratio)
            
            # Asegurarse de que el código de barras no sea demasiado grande
            espacio_disponible_barcode = height - y_pos - margin_y
            if barcode_height > espacio_disponible_barcode:
                barcode_height = int(espacio_disponible_barcode * 0.8)
                barcode_width = int(barcode_height / barcode_ratio)
            
            # Redimensionar el código de barras con alta calidad
            barcode_img = barcode_img.resize((barcode_width, barcode_height), Image.LANCZOS)
            
            # Calcular posición para centrar el código de barras
            barcode_x = (width - barcode_width) // 2
            
            # Pegar el código de barras en la etiqueta
            etiqueta.paste(barcode_img, (barcode_x, int(y_pos)))
            
            # No necesitamos agregar el texto manualmente, ya que está incluido en la imagen del código de barras
            
            # Eliminar el archivo temporal
            try:
                os.remove(temp_filename + ".png")
            except Exception as e:
                print(f"No se pudo eliminar el archivo temporal: {e}")
                
        except Exception as e:
            import traceback
            print(f"Error detallado: {traceback.format_exc()}")
            print(f"Error al generar o cargar el código de barras: {e}")
            # Dibujar un rectángulo como placeholder para el código de barras
            draw.rectangle([(width*0.1, y_pos), (width*0.9, y_pos + 300)], outline="black")
            error_msg = f"Error: {str(e)}"
            error_width = draw.textlength(error_msg, font=font_normal)
            error_x = int((width - error_width) / 2)
            draw.text((error_x, int(y_pos + 150)), error_msg, fill="red", font=font_normal)
        
        return etiqueta
    
    def cargar_impresoras(self):
        """Carga la lista de impresoras disponibles en el sistema"""
        try:
            impresoras = [printer[2] for printer in win32print.EnumPrinters(2)]
            self.impresora_combo.clear()
            self.impresora_combo.addItems(impresoras)
            
            # Seleccionar la impresora predeterminada
            impresora_default = win32print.GetDefaultPrinter()
            index = self.impresora_combo.findText(impresora_default)
            if index >= 0:
                self.impresora_combo.setCurrentIndex(index)
        except Exception as e:
            print(f"Error al cargar impresoras: {e}")
            self.impresora_combo.addItem("No se pudieron cargar las impresoras")

    def imprimir_pdf_directo(self):
        """Genera un PDF de la etiqueta y lo imprime directamente a la impresora seleccionada"""
        if not self.codigo_input.text() or not self.nombre_input.text():
            QMessageBox.warning(self, "Error", "Seleccione un producto para imprimir la etiqueta")
            return
        
        try:
            # Generar el código de barras
            codigo_barras = generar_codigo_variable_ean13(
                self.codigo_input.text(), self.peso_input.value()
            )
            
            # Verificar que el código de barras se generó correctamente
            if not codigo_barras:
                raise ValueError("No se pudo generar el código de barras")
            
            # Calcular el precio basado en el peso
            peso = float(self.peso_input.value())
            precio_total = round(peso * self.precio_venta, 2)
            
            # Datos del producto (nombre en mayúsculas)
            datos_producto = {
                "Codigo": self.codigo_input.text(),
                "Nombre": self.nombre_input.text().upper(),
                "Ingredientes": self.ingredientes_input.text(),
                "CodigoBarras": codigo_barras,
                "Peso": str(self.peso_input.value()),
                "PrecioVenta": self.precio_venta,
                "PrecioTotal": precio_total
            }
            
            # Crear la etiqueta
            etiqueta = self.generar_imagen_etiqueta(datos_producto)
            
            # Usar un directorio temporal para guardar el PDF
            import tempfile
            temp_dir = tempfile.gettempdir()
            nombre_archivo = f"etiqueta_{self.codigo_input.text()}_{self.peso_input.value()}.pdf"
            ruta_pdf = os.path.join(temp_dir, nombre_archivo)
            
            # Guardar como PDF con alta resolución
            etiqueta.save(ruta_pdf, "PDF", resolution=300.0)
            
            # Verificar que el archivo se creó correctamente
            if not os.path.exists(ruta_pdf):
                raise FileNotFoundError(f"No se pudo crear el archivo PDF en: {ruta_pdf}")
            
            # Obtener la impresora seleccionada
            impresora = self.impresora_combo.currentText()
            
            # Mostrar mensaje de espera
            self.setCursor(Qt.CursorShape.WaitCursor)
            QMessageBox.information(self, "Imprimiendo", 
                               f"Enviando etiqueta a la impresora {impresora}.\nEsto puede tardar unos segundos...")
            
            # Imprimir el PDF directamente
            exito = imprimir_pdf_directo(ruta_pdf, impresora)
            
            # Restaurar cursor
            self.setCursor(Qt.CursorShape.ArrowCursor)
            
            if exito:
                QMessageBox.information(self, "Éxito", f"Etiqueta impresa correctamente en {impresora}")
                # Limpiar los campos después de imprimir exitosamente
                self.limpiar_campos()
            else:
                QMessageBox.warning(self, "Error", 
                               f"No se pudo imprimir la etiqueta en {impresora}.\n"
                               f"El archivo PDF se guardó en: {ruta_pdf}")
            
            # Intentar eliminar el archivo temporal
            try:
                os.remove(ruta_pdf)
            except Exception as e:
                print(f"No se pudo eliminar el archivo temporal: {e}")
            
        except Exception as e:
            import traceback
            error_detallado = traceback.format_exc()
            print(f"Error detallado: {error_detallado}")
            QMessageBox.warning(self, "Error", f"Error al imprimir la etiqueta: {str(e)}")

    def generar_pagina_etiquetas(self, datos_producto):
        """
        Genera una página con 2 etiquetas lado a lado.
        Útil para imprimir 2 etiquetas de 4x6 pulgadas en una página.
        """
        # Generar la etiqueta individual
        etiqueta_individual = self.generar_imagen_etiqueta(datos_producto)
        
        # Crear una nueva imagen para la página completa (2 etiquetas lado a lado)
        pagina = Image.new('RGB', (2400, 1800), color='white')
        
        # Pegar la primera etiqueta a la izquierda
        pagina.paste(etiqueta_individual, (0, 0))
        
        # Pegar la segunda etiqueta a la derecha (la misma etiqueta duplicada)
        pagina.paste(etiqueta_individual, (1200, 0))
        
        # Dibujar una línea divisoria entre las etiquetas
        draw = ImageDraw.Draw(pagina)
        draw.line([(1200, 0), (1200, 1800)], fill='black', width=1)
        
        return pagina
    
    def guardar_vista_previa(self):
        """Guarda la vista previa de la etiqueta como imagen"""
        if self.preview_label.pixmap() is None:
            QMessageBox.warning(self, "Error", "No hay vista previa para guardar")
            return
        
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar Vista Previa", "", "Imágenes (*.png *.jpg)"
        )
        
        if ruta:
            self.preview_label.pixmap().save(ruta)
            QMessageBox.information(self, "Éxito", f"Vista previa guardada en {ruta}")
    
    def imprimir_etiqueta_actual(self):
        """Genera el CSV y llama a BarTender para imprimir la etiqueta"""
        if not self.codigo_input.text() or not self.nombre_input.text():
            QMessageBox.warning(self, "Error", "Seleccione un producto para imprimir la etiqueta")
            return
                
        if not os.path.exists(self.ruta_plantilla.text()):
            QMessageBox.warning(self, "Error", "La plantilla de BarTender no existe")
            return
        
        try:
            # Generar el código de barras
            codigo_barras = generar_codigo_variable_ean13(
                self.codigo_input.text(), self.peso_input.value()
            )
            
            # Calcular el precio basado en el peso
            peso = float(self.peso_input.value())
            precio_total = round(peso * self.precio_venta, 2)
            
            # Datos del producto (nombre en mayúsculas)
            datos_producto = {
                "Codigo": self.codigo_input.text(),
                "Nombre": self.nombre_input.text().upper(),  # Convertir a mayúsculas
                "Ingredientes": self.ingredientes_input.text(),
                "CodigoBarras": codigo_barras,
                "Peso": str(self.peso_input.value()),
                "PrecioVenta": self.precio_venta,
                "PrecioTotal": precio_total
            }
            
            # Imprimir los datos para depuración
            print("Datos enviados a la etiqueta:")
            for key, value in datos_producto.items():
                print(f"  {key}: {value}")
            
            # Usar un directorio temporal para evitar problemas de permisos
            import tempfile
            temp_dir = tempfile.gettempdir()
            ruta_csv = os.path.join(temp_dir, "datos_etiqueta.csv")
            
            print(f"Generando CSV en: {ruta_csv}")
            
            # Generar el CSV
            generar_csv_etiqueta(datos_producto, ruta_csv)
            
            # Verificar el contenido del CSV generado
            print("Verificando contenido del CSV generado:")
            with open(ruta_csv, 'r', encoding='utf-8') as f:
                print(f.read())
            
            # Verificar que el archivo se creó correctamente
            if not os.path.exists(ruta_csv):
                raise FileNotFoundError(f"No se pudo crear el archivo CSV en: {ruta_csv}")
            
            # Llamar a BarTender para imprimir
            print(f"Llamando a BarTender con plantilla: {self.ruta_plantilla.text()} y datos: {ruta_csv}")
            exito = imprimir_etiqueta(self.ruta_plantilla.text(), ruta_csv)
            
            if exito:
                QMessageBox.information(self, "Éxito", "Etiqueta enviada a imprimir")
                # Limpiar los campos después de imprimir exitosamente
                self.limpiar_campos()
            else:
                QMessageBox.warning(self, "Advertencia", "La etiqueta se envió a imprimir, pero hubo algún problema")
            
        except Exception as e:
            import traceback
            error_detallado = traceback.format_exc()
            print(f"Error detallado: {error_detallado}")
            QMessageBox.warning(self, "Error", f"Error al imprimir la etiqueta: {str(e)}")

    def limpiar_campos(self):
        """Limpia todos los campos de entrada después de imprimir exitosamente"""
        self.codigo_input.clear()
        self.nombre_input.clear()
        self.ingredientes_input.clear()
        self.peso_input.setValue(1.0)
        self.preview_label.clear()
        self.preview_label.setText("Seleccione un producto para generar la vista previa")
        
        # Limpiar y enfocar el campo de búsqueda
        self.busqueda_producto.clear()
        self.busqueda_producto.setFocus()

    def guardar_etiqueta_pdf(self):
        """Guarda la etiqueta actual como un archivo PDF"""
        if not self.codigo_input.text() or not self.nombre_input.text():
            QMessageBox.warning(self, "Error", "Seleccione un producto para generar el PDF")
            return
        
        try:
            # Generar el código de barras
            codigo_barras = generar_codigo_variable_ean13(
                self.codigo_input.text(), self.peso_input.value()
            )
            
            # Verificar que el código de barras se generó correctamente
            if not codigo_barras:
                raise ValueError("No se pudo generar el código de barras")
            
            peso = float(self.peso_input.value())
            precio_total = round(peso * self.precio_venta, 2)
            
            # Datos del producto
            datos_producto = {
                "Nombre": self.nombre_input.text(),
                "Ingredientes": self.ingredientes_input.text(),
                "CodigoBarras": codigo_barras,
                "Peso": str(self.peso_input.value()),
                "PrecioVenta": self.precio_venta,
                "PrecioTotal": precio_total
            }
            
            # Crear la etiqueta
            etiqueta = self.generar_imagen_etiqueta(datos_producto)
            
            # Solicitar la ubicación para guardar el PDF
            ruta, _ = QFileDialog.getSaveFileName(
                self, "Guardar Etiqueta como PDF", "", "Archivos PDF (*.pdf)"
            )
            
            if not ruta:
                return  # El usuario canceló
                
            # Asegurarse de que la ruta termine en .pdf
            if not ruta.lower().endswith('.pdf'):
                ruta += '.pdf'
            
            # Convertir la imagen PIL a PDF
            etiqueta.save(ruta, "PDF", resolution=100.0)
            
            QMessageBox.information(self, "Éxito", f"Etiqueta guardada como PDF en:\n{ruta}")
            
        except Exception as e:
            import traceback
            error_detallado = traceback.format_exc()
            print(f"Error detallado: {error_detallado}")
            QMessageBox.warning(self, "Error", f"Error al guardar el PDF: {str(e)}")

