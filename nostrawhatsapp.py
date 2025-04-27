import sys
import os
import pandas as pd
import random
import time
import datetime
import re
import pywhatkit
import phonenumbers
import sqlite3

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton,
                             QTableView, QHeaderView, QComboBox, QProgressBar,
                             QMessageBox, QFileDialog, QCheckBox, QGroupBox)
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSlot, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap


class PandasModel(QAbstractTableModel):
    # Modelo para mostrar DataFrame de pandas en QTableView

    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=QModelIndex()):
        return self._data.shape[0]

    def columnCount(self, parent=QModelIndex()):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._data.columns[section]
        return None


class DatabaseManager:
    # Gestiona todas las operaciones con la base de datos SQLite
    
    def __init__(self, db_file="nostra_whatsapp.db"):
        self.db_file = db_file
        self.create_tables()
    
    def get_connection(self):
        """Obtiene una conexión a la base de datos"""
        return sqlite3.connect(self.db_file)
    
    def create_tables(self):
        """Crea las tablas necesarias si no existen"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Tabla de clientes
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            razon_social TEXT,
            rut TEXT,
            giro TEXT,
            direccion TEXT,
            comuna TEXT,
            ciudad TEXT,
            nombre_contacto TEXT,
            telefono TEXT
        )
        ''')
        
        # Tabla de historial de envíos
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_envios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            razon_social TEXT,
            telefono TEXT,
            ciudad TEXT,
            resultado TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def import_excel_to_db(self, excel_file):
        # Importa datos desde un archivo Excel a la base de datos SQLite
        try:
            df = pd.read_excel(excel_file)
            
            # Verificar columnas requeridas
            required_columns = [
                'Razón social', 'RUT', 'Giro', 'Dirección', 'Comuna',
                'Ciudad', 'Nombre contacto', 'Teléfono'
            ]
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return False, f"Columnas faltantes: {', '.join(missing_columns)}"
            
            # Normalizar datos
            df = df.fillna("")
            for col in required_columns:
                df[col] = df[col].astype(str)
            
            # Conectar a la base de datos
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Limpiar tabla antes de importar (opcional)
            cursor.execute("DELETE FROM clientes")
            
            # Insertar datos
            for _, row in df.iterrows():
                cursor.execute('''
                INSERT INTO clientes (razon_social, rut, giro, direccion, comuna, ciudad, nombre_contacto, telefono)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['Razón social'], 
                    row['RUT'], 
                    row['Giro'], 
                    row['Dirección'], 
                    row['Comuna'], 
                    row['Ciudad'], 
                    row['Nombre contacto'], 
                    row['Teléfono']
                ))
            
            conn.commit()
            conn.close()
            
            return True, f"Se importaron {len(df)} registros."
        
        except Exception as e:
            return False, f"Error al importar: {str(e)}"
    
    def get_all_clients(self):
        # Obtiene todos los clientes como DataFrame
        conn = self.get_connection()
        query = '''
        SELECT razon_social as 'Razón social', 
               rut as 'RUT', 
               giro as 'Giro', 
               direccion as 'Dirección', 
               comuna as 'Comuna', 
               ciudad as 'Ciudad', 
               nombre_contacto as 'Nombre contacto', 
               telefono as 'Teléfono'
        FROM clientes
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def get_filtered_clients(self, city=None, commune=None, giro=None):
        # Obtiene clientes filtrados según los criterios
        conn = self.get_connection()
        
        query = '''
        SELECT razon_social as 'Razón social', 
               rut as 'RUT', 
               giro as 'Giro', 
               direccion as 'Dirección', 
               comuna as 'Comuna', 
               ciudad as 'Ciudad', 
               nombre_contacto as 'Nombre contacto', 
               telefono as 'Teléfono'
        FROM clientes
        WHERE 1=1
        '''
        
        params = []
        
        if city and city.lower() != "todas las ciudades":
            query += " AND LOWER(ciudad) = ?"
            params.append(city.lower())
        
        if commune and commune.lower() != "todas las comunas":
            query += " AND LOWER(comuna) = ?"
            params.append(commune.lower())
        
        if giro and giro.lower() != "todos los giros":
            query += " AND LOWER(giro) = ?"
            params.append(giro.lower())
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    
    def get_unique_values(self, column):
        """Obtiene valores únicos para una columna"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT DISTINCT LOWER({column}) FROM clientes WHERE {column} IS NOT NULL AND {column} != ''")
        values = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return sorted(values)
    
    def record_message_sent(self, razon_social, telefono, ciudad, resultado):
        """Registra un envío en el historial"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO historial_envios (razon_social, telefono, ciudad, resultado)
        VALUES (?, ?, ?, ?)
        ''', (razon_social, telefono, ciudad, resultado))
        
        conn.commit()
        conn.close()
    
    def get_sent_phones(self):
        """Obtiene números de teléfono a los que ya se ha enviado mensaje"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT telefono FROM historial_envios WHERE resultado = 'Éxito'")
        phones = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return set(phones)
    
    def get_message_history(self, limit=100):
        """Obtiene historial de mensajes enviados"""
        conn = self.get_connection()
        
        query = '''
        SELECT fecha_hora, razon_social, telefono, ciudad, resultado
        FROM historial_envios
        ORDER BY fecha_hora DESC
        LIMIT ?
        '''
        
        df = pd.read_sql_query(query, conn, params=[limit])
        conn.close()
        return df


class WhatsAppSenderThread(QThread):
    """Hilo separado para envío de mensajes sin bloquear la interfaz"""

    progress_update = pyqtSignal(int, int)  # Emite (valor actual, total)
    # Emite (razon_social, telefono, ciudad, exito)
    message_sent = pyqtSignal(str, str, str, bool)
    finished_sending = pyqtSignal()

    def __init__(self, df_filtered, message_template, db_manager, test_mode=False, check_history=False):
        super().__init__()
        self.df = df_filtered
        self.message_template = message_template
        self.test_mode = test_mode
        self.check_history = check_history
        self.db_manager = db_manager
        self.stop_requested = False

    def run(self):
        total = 1 if self.test_mode else len(self.df)
        sent_count = 0

        # Cargar historial si está habilitada la verificación
        sent_numbers = set()
        if self.check_history:
            sent_numbers = self.db_manager.get_sent_phones()

        # Limitar a 1 registro si es modo prueba
        process_df = self.df.head(1) if self.test_mode else self.df

        for index, row in process_df.iterrows():
            if self.stop_requested:
                break

            # Preparar número de teléfono en formato internacional
            phone = str(row['Teléfono']).strip()
            # Eliminar caracteres no numéricos
            phone = re.sub(r'\D', '', phone)

            # Validar formato de teléfono chileno
            valid_phone = False
            if phone.startswith('9') and len(phone) == 9:
                formatted_phone = f"+56{phone}"
                valid_phone = True
            elif phone.startswith('569') and len(phone) == 11:
                formatted_phone = f"+{phone}"
                valid_phone = True
            elif phone.startswith('+569') and len(phone) == 12:
                formatted_phone = phone
                valid_phone = True

            # Verificar si ya fue enviado
            if self.check_history and formatted_phone in sent_numbers:
                self.message_sent.emit(
                    row['Razón social'],
                    formatted_phone,
                    row['Ciudad'],
                    False
                )
                self.progress_update.emit(sent_count, total)
                continue

            # Solo procesar si es un número válido
            if valid_phone:
                # Reemplazar variables en la plantilla de mensaje
                message = self.message_template
                for col in self.df.columns:
                    placeholder = f"[{col}]"
                    if placeholder in message:
                        message = message.replace(placeholder, str(row[col]))

                success = False
                try:
                    # Enviar mensaje por WhatsApp
                    pywhatkit.sendwhatmsg_instantly(
                        formatted_phone,
                        message,
                        wait_time=15,  # Tiempo para cargar WhatsApp Web
                        tab_close=True
                    )
                    success = True
                    sent_count += 1
                except Exception as e:
                    print(f"Error al enviar mensaje: {e}")

                # Registrar en la base de datos
                resultado = "Éxito" if success else "Error"
                self.db_manager.record_message_sent(
                    row['Razón social'],
                    formatted_phone,
                    row['Ciudad'],
                    resultado
                )

                # Emitir señal de mensaje enviado (o fallido)
                self.message_sent.emit(
                    row['Razón social'],
                    formatted_phone,
                    row['Ciudad'],
                    success
                )

                # Actualizar progreso
                self.progress_update.emit(sent_count, total)

                # Esperar un tiempo aleatorio entre mensajes para evitar bloqueos
                if not self.test_mode and index < len(process_df) - 1:
                    time.sleep(random.uniform(3, 7))
            else:
                # Registrar error por número inválido
                self.db_manager.record_message_sent(
                    row['Razón social'],
                    phone,
                    row['Ciudad'],
                    "Error - Número inválido"
                )
                
                # Emitir señal de mensaje fallido por número inválido
                self.message_sent.emit(
                    row['Razón social'],
                    phone,
                    row['Ciudad'],
                    False
                )
                self.progress_update.emit(sent_count, total)

        # Señal de finalización
        self.finished_sending.emit()

    def stop(self):
        self.stop_requested = True


class NostraWhatsApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.df = None  # DataFrame original
        self.df_filtered = None  # DataFrame filtrado
        self.sender_thread = None  # Hilo para envío de mensajes
        self.db_manager = DatabaseManager()  # Gestor de base de datos

        self.init_ui()
        self.load_data_from_db()  # Cargar datos iniciales de la base de datos

    def init_ui(self):
        self.setWindowTitle("NostraWhatsApp - Envío Masivo")
        self.setGeometry(100, 100, 1000, 700)

        # Widget central y layout principal
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Sección de gestión de datos
        data_group = QGroupBox("Gestión de datos")
        data_layout = QVBoxLayout()

        load_layout = QHBoxLayout()
        self.btn_load_excel = QPushButton("Importar desde Excel")
        self.btn_load_excel.clicked.connect(self.import_excel)
        self.btn_view_history = QPushButton("Ver Historial de Envíos")
        self.btn_view_history.clicked.connect(self.view_history)
        self.lbl_data_status = QLabel("Base de datos cargada")
        load_layout.addWidget(self.btn_load_excel)
        load_layout.addWidget(self.btn_view_history)
        load_layout.addWidget(self.lbl_data_status)
        load_layout.addStretch()

        data_layout.addLayout(load_layout)

        # Tabla para mostrar datos
        self.table_data = QTableView()
        self.table_data.setMinimumHeight(200)
        data_layout.addWidget(self.table_data)

        data_group.setLayout(data_layout)
        main_layout.addWidget(data_group)

        # Sección de filtros
        filter_group = QGroupBox("Filtrar destinatarios")
        filter_layout = QVBoxLayout()

        # Filtro por Ciudad
        city_layout = QHBoxLayout()
        city_layout.addWidget(QLabel("Filtrar por Ciudad:"))
        self.cmb_cities = QComboBox()
        self.cmb_cities.setMinimumWidth(200)
        self.cmb_cities.currentIndexChanged.connect(self.filter_data)
        city_layout.addWidget(self.cmb_cities)
        filter_layout.addLayout(city_layout)

        # Filtro por Comuna
        commune_layout = QHBoxLayout()
        commune_layout.addWidget(QLabel("Filtrar por Comuna:"))
        self.cmb_communes = QComboBox()
        self.cmb_communes.setMinimumWidth(200)
        self.cmb_communes.currentIndexChanged.connect(self.filter_data)
        commune_layout.addWidget(self.cmb_communes)
        filter_layout.addLayout(commune_layout)

        # Filtro por Giro
        giro_layout = QHBoxLayout()
        giro_layout.addWidget(QLabel("Filtrar por Giro:"))
        self.cmb_giros = QComboBox()
        self.cmb_giros.setMinimumWidth(200)
        self.cmb_giros.currentIndexChanged.connect(self.filter_data)
        giro_layout.addWidget(self.cmb_giros)
        filter_layout.addLayout(giro_layout)

        # Conectar señales para deshabilitar otros filtros
        self.cmb_cities.currentIndexChanged.connect(self.city_filter_selected)
        self.cmb_communes.currentIndexChanged.connect(self.commune_filter_selected)
        self.cmb_giros.currentIndexChanged.connect(self.giro_filter_selected)

        # Etiqueta para mostrar el número de contactos seleccionados
        self.lbl_filter_count = QLabel("0 contactos seleccionados")
        filter_layout.addWidget(self.lbl_filter_count)

        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)

        # Sección de mensaje
        message_group = QGroupBox("Mensaje personalizado")
        message_layout = QVBoxLayout()

        message_layout.addWidget(QLabel(
            "Variables disponibles: [Razón social], [RUT], [Giro], [Dirección], [Comuna], [Ciudad], [Nombre contacto], [Teléfono]"))

        self.txt_message = QTextEdit()
        self.txt_message.setPlaceholderText(
            "Escribe tu mensaje aquí usando variables entre corchetes..."
        )
        self.txt_message.setText(
            "¡Hola [Nombre contacto]! 👋\n\n"
            "Te saludamos desde *Nostra SPA* 🏢, la empresa detrás de *https://www.eltecle.cl/* y *https://hidratanos.com/hidratanos.com*.\n\n"
            "Nos ponemos en contacto con ustedes de *[Razón social]*, ubicada en *[Ciudad]*, para compartir una excelente noticia: "
            "¡estamos ampliando nuestra línea de productos para ofrecerte más soluciones! 🚀\n\n"
            "Entre las novedades que pronto estarán disponibles, se incluyen:\n"
            "• 🛠️ Transpaletas manuales y eléctricas\n"
            "• ⚡ Generadores\n"
            "• 🪜 Escaleras industriales\n"
            "• 🔒 Candados y elementos de seguridad\n\n"
            "Queremos que seas de los primeros en conocer esta expansión y, como parte de nuestra red de contactos, "
            "te ofrecemos condiciones preferenciales. 🎉\n\n"
            "¿Te gustaría recibir nuestro catálogo actualizado con todos los detalles? 📄\n\n"
            "Quedamos atentos a tu respuesta. 😊\n\n"
            "Saludos cordiales,\n"
            "*Equipo de Nostra SPA*"
        )
        message_layout.addWidget(self.txt_message)

        message_group.setLayout(message_layout)
        main_layout.addWidget(message_group)

        # Sección de opciones de envío
        send_options_group = QGroupBox("Opciones de envío")
        send_options_layout = QHBoxLayout()

        self.chk_test_mode = QCheckBox(
            "Modo prueba (solo enviar al primer contacto)")
        self.chk_test_mode.setChecked(True)
        send_options_layout.addWidget(self.chk_test_mode)

        self.chk_avoid_resend = QCheckBox(
            "Evitar reenvíos a contactos ya en historial")
        self.chk_avoid_resend.setChecked(True)
        send_options_layout.addWidget(self.chk_avoid_resend)

        send_options_layout.addStretch()

        send_options_group.setLayout(send_options_layout)
        main_layout.addWidget(send_options_group)

        # Sección de progreso y envío
        progress_group = QGroupBox("Envío y progreso")
        progress_layout = QVBoxLayout()

        send_layout = QHBoxLayout()
        self.btn_send = QPushButton("Iniciar Envío")
        self.btn_send.setMinimumHeight(40)
        self.btn_send.clicked.connect(self.start_sending)
        self.btn_send.setEnabled(False)

        self.btn_stop = QPushButton("Detener Envío")
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.clicked.connect(self.stop_sending)
        self.btn_stop.setEnabled(False)

        send_layout.addWidget(self.btn_send)
        send_layout.addWidget(self.btn_stop)

        progress_layout.addLayout(send_layout)

        progress_stats_layout = QHBoxLayout()
        self.lbl_progress = QLabel("Progreso: 0/0")
        progress_stats_layout.addWidget(self.lbl_progress)

        progress_stats_layout.addStretch()

        self.lbl_status = QLabel("Listo")
        progress_stats_layout.addWidget(self.lbl_status)

        progress_layout.addLayout(progress_stats_layout)

        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)

        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)

    def load_data_from_db(self):
        """Carga datos desde la base de datos SQLite"""
        try:
            # Obtener todos los clientes
            self.df = self.db_manager.get_all_clients()
            
            if len(self.df) > 0:
                # Mostrar en la tabla
                model = PandasModel(self.df)
                self.table_data.setModel(model)
                
                # Ajustar tamaño de las columnas
                header = self.table_data.horizontalHeader()
                for i in range(len(self.df.columns)):
                    header.setSectionResizeMode(i, QHeaderView.Stretch)
                
                # Actualizar estado
                self.lbl_data_status.setText(f"Base de datos cargada: {len(self.df)} registros")
                
                # Actualizar filtros
                self.update_filter_options()
                
                # Aplicar filtro inicial (todos)
                self.filter_data()
                
                # Habilitar botón de envío
                self.btn_send.setEnabled(True)
            else:
                self.lbl_data_status.setText("No hay datos en la base de datos")
                self.btn_send.setEnabled(False)
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar datos: {str(e)}")
    
    def import_excel(self):
        """Importa datos desde un archivo Excel a la base de datos"""
        try:
            # Por defecto busca un archivo llamado clientes.xlsx en el directorio actual
            default_file = "clientes.xlsx"
            
            if os.path.exists(default_file):
                file_path = default_file
            else:
                file_path, _ = QFileDialog.getOpenFileName(
                    self, "Seleccionar archivo Excel", "", "Archivos Excel (*.xlsx *.xls)"
                )
            
            if not file_path:
                return
            
            # Importar datos
            success, message = self.db_manager.import_excel_to_db(file_path)
            
            if success:
                QMessageBox.information(self, "Importación exitosa", message)
                self.load_data_from_db()  # Recargar datos
            else:
                QMessageBox.warning(self, "Error", message)
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al importar Excel: {str(e)}")
    
    def update_filter_options(self):
        """Actualiza las opciones en los filtros desplegables"""
        # Ciudades
        self.cmb_cities.clear()
        self.cmb_cities.addItem("Todas las ciudades")
        cities = self.db_manager.get_unique_values("ciudad")
        for city in cities:
            self.cmb_cities.addItem(city.capitalize())
        
        # Comunas
        self.cmb_communes.clear()
        self.cmb_communes.addItem("Todas las comunas")
        communes = self.db_manager.get_unique_values("comuna")
        for commune in communes:
            self.cmb_communes.addItem(commune.capitalize())
        
        # Giros
        self.cmb_giros.clear()
        self.cmb_giros.addItem("Todos los giros")
        giros = self.db_manager.get_unique_values("giro")
        for giro in giros:
            self.cmb_giros.addItem(giro.capitalize())
    
    def filter_data(self):
        """Aplica filtros a los datos mostrados"""
        if self.df is None:
            return
        
        # Obtener valores seleccionados en los filtros
        selected_city = self.cmb_cities.currentText()
        selected_commune = self.cmb_communes.currentText()
        selected_giro = self.cmb_giros.currentText()
        
        # Filtrar datos usando el gestor de base de datos
        self.df_filtered = self.db_manager.get_filtered_clients(
            city=selected_city if selected_city != "Todas las ciudades" else None,
            commune=selected_commune if selected_commune != "Todas las comunas" else None,
            giro=selected_giro if selected_giro != "Todos los giros" else None
        )
        
        # Actualizar tabla con datos filtrados
        model = PandasModel(self.df_filtered)
        self.table_data.setModel(model)
        
        # Ajustar etiqueta de conteo
        self.lbl_filter_count.setText(f"{len(self.df_filtered)} contactos seleccionados")
    
    def view_history(self):
        """Muestra el historial de envíos en una nueva ventana"""
        try:
            history_df = self.db_manager.get_message_history(limit=500)
            
            if len(history_df) > 0:
                # Crear ventana sencilla para mostrar el historial
                history_window = QMainWindow(self)
                history_window.setWindowTitle("Historial de Envíos")
                history_window.setGeometry(150, 150, 800, 500)
                
                # Crear widget central y layout
                central_widget = QWidget()
                layout = QVBoxLayout()
                
                # Etiqueta de información
                layout.addWidget(QLabel(f"Últimos {len(history_df)} envíos registrados:"))
                
                # Tabla para mostrar historial
                table_history = QTableView()
                model = PandasModel(history_df)
                table_history.setModel(model)
                
                # Ajustar tamaño de las columnas
                header = table_history.horizontalHeader()
                for i in range(len(history_df.columns)):
                    header.setSectionResizeMode(i, QHeaderView.Stretch)
                
                layout.addWidget(table_history)
                
                # Botón para cerrar
                btn_close = QPushButton("Cerrar")
                btn_close.clicked.connect(history_window.close)
                layout.addWidget(btn_close)
                
                central_widget.setLayout(layout)
                history_window.setCentralWidget(central_widget)
                
                history_window.show()
            else:
                QMessageBox.information(self, "Historial", "No hay registros en el historial de envíos.")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar historial: {str(e)}")
    
    def start_sending(self):
        if self.df_filtered is None or len(self.df_filtered) == 0:
            QMessageBox.warning(
                self, "Error", "No hay contactos seleccionados para enviar")
            return

        message_template = self.txt_message.toPlainText()
        if not message_template:
            QMessageBox.warning(self, "Error", "Debe ingresar un mensaje")
            return

        # Verificar si WhatsApp Web está disponible
        reply = QMessageBox.question(
            self,
            "Confirmar envío",
            "¿Ha iniciado sesión en WhatsApp Web y está listo para enviar los mensajes?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.No:
            QMessageBox.information(
                self,
                "Información",
                "Primero debe iniciar sesión en WhatsApp Web antes de continuar.\n"
                "1. Abra Google Chrome\n"
                "2. Navegue a web.whatsapp.com\n"
                "3. Escanee el código QR con su teléfono\n"
                "4. Una vez logueado, regrese e intente nuevamente."
            )
            return

        # Configurar la interfaz para el modo de envío
        self.btn_send.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_load_excel.setEnabled(False)
        self.cmb_cities.setEnabled(False)
        self.cmb_communes.setEnabled(False)
        self.cmb_giros.setEnabled(False)

        # Número total para la barra de progreso
        total = 1 if self.chk_test_mode.isChecked() else len(self.df_filtered)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(0)

        # Iniciar hilo de envío
        self.sender_thread = WhatsAppSenderThread(
            self.df_filtered,
            message_template,
            self.db_manager,
            test_mode=self.chk_test_mode.isChecked(),
            check_history=self.chk_avoid_resend.isChecked()
        )

        # Conectar señales
        self.sender_thread.progress_update.connect(self.update_progress)
        self.sender_thread.message_sent.connect(self.register_sent_message)
        self.sender_thread.finished_sending.connect(self.sending_finished)

        # Iniciar envío
        self.sender_thread.start()
        self.lbl_status.setText("Enviando mensajes...")

    def stop_sending(self):
        if self.sender_thread and self.sender_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirmar detención",
                "¿Está seguro de que desea detener el envío de mensajes?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.lbl_status.setText("Deteniendo envío...")
                self.sender_thread.stop()

    def update_progress(self, current, total):
        self.progress_bar.setValue(current)
        self.lbl_progress.setText(f"Progreso: {current}/{total}")

    def register_sent_message(self, razon_social, telefono, ciudad, success):
        # Actualizar etiqueta de estado
        if success:
            self.lbl_status.setText(f"Último envío: {razon_social} - Éxito")
        else:
            self.lbl_status.setText(f"Último envío: {razon_social} - Error")

    def sending_finished(self):
        # Mostrar resumen
        try:
            # Obtener estadísticas del último envío
            history_df = self.db_manager.get_message_history(limit=100)
            total_sent = len(history_df)
            successful = len(history_df[history_df['resultado'] == 'Éxito'])
            
            if total_sent > 0:
                QMessageBox.information(
                    self,
                    "Envío completado",
                    f"Envío completado.\n\n"
                    f"Total intentos: {total_sent}\n"
                    f"Enviados con éxito: {successful}\n"
                    f"Fallidos: {total_sent - successful}\n\n"
                    f"El historial completo se guarda automáticamente en la base de datos"
                )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error al consultar historial",
                f"No se pudo obtener el resumen de envío: {str(e)}"
            )

        # Resetear interfaz
        self.btn_send.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_load_excel.setEnabled(True)
        self.cmb_cities.setEnabled(True)
        self.cmb_communes.setEnabled(True)
        self.cmb_giros.setEnabled(True)
        self.lbl_status.setText("Listo")

    def city_filter_selected(self):
        if self.cmb_cities.currentIndex() > 0:  # Si se selecciona una ciudad
            self.cmb_communes.setEnabled(False)
            self.cmb_giros.setEnabled(False)
        else:  # Si no hay selección
            self.cmb_communes.setEnabled(True)
            self.cmb_giros.setEnabled(True)
        self.filter_data()

    def commune_filter_selected(self):
        if self.cmb_communes.currentIndex() > 0:  # Si se selecciona una comuna
            self.cmb_cities.setEnabled(False)
            self.cmb_giros.setEnabled(False)
        else:  # Si no hay selección
            self.cmb_cities.setEnabled(True)
            self.cmb_giros.setEnabled(True)
        self.filter_data()

    def giro_filter_selected(self):
        if self.cmb_giros.currentIndex() > 0:  # Si se selecciona un giro
            self.cmb_cities.setEnabled(False)
            self.cmb_communes.setEnabled(False)
        else:  # Si no hay selección
            self.cmb_cities.setEnabled(True)
            self.cmb_communes.setEnabled(True)
        self.filter_data()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NostraWhatsApp()
    window.show()
    sys.exit(app.exec_())