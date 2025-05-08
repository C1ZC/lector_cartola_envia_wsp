import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QGroupBox, QHBoxLayout, QPushButton, QLabel,
    QTableView, QComboBox, QTextEdit, QCheckBox, QProgressBar, QMessageBox
)
from PyQt5.QtWidgets import QHeaderView
from ..models.pandas_model import PandasModel
from ..models.database import DatabaseManager
from ..controllers.whatsapp_sender import WhatsAppSenderThread
from .history_window import HistoryWindow
from .progress_window import SendProgressDialog
import os


class NostraWhatsApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.df = None
        self.df_filtered = None
        self.sender_thread = None
        self.db_manager = DatabaseManager()
        self.init_ui()
        self.load_data_from_db()

    def init_ui(self):
        self.setWindowTitle("NostraWhatsApp - Envío Masivo")
        self.setGeometry(100, 100, 1000, 700)
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Gestión de datos
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
        self.table_data = QTableView()
        self.table_data.setMinimumHeight(200)
        data_layout.addWidget(self.table_data)
        data_group.setLayout(data_layout)
        main_layout.addWidget(data_group)

        # Filtros
        filter_group = QGroupBox("Filtrar destinatarios")
        filter_layout = QVBoxLayout()
        city_layout = QHBoxLayout()
        city_layout.addWidget(QLabel("Filtrar por Ciudad:"))
        self.cmb_cities = QComboBox()
        self.cmb_cities.setMinimumWidth(200)
        self.cmb_cities.currentIndexChanged.connect(self.filter_data)
        city_layout.addWidget(self.cmb_cities)
        filter_layout.addLayout(city_layout)
        commune_layout = QHBoxLayout()
        commune_layout.addWidget(QLabel("Filtrar por Comuna:"))
        self.cmb_communes = QComboBox()
        self.cmb_communes.setMinimumWidth(200)
        self.cmb_communes.currentIndexChanged.connect(self.filter_data)
        commune_layout.addWidget(self.cmb_communes)
        filter_layout.addLayout(commune_layout)
        giro_layout = QHBoxLayout()
        giro_layout.addWidget(QLabel("Filtrar por Giro:"))
        self.cmb_giros = QComboBox()
        self.cmb_giros.setMinimumWidth(200)
        self.cmb_giros.currentIndexChanged.connect(self.filter_data)
        giro_layout.addWidget(self.cmb_giros)
        filter_layout.addLayout(giro_layout)
        self.cmb_cities.currentIndexChanged.connect(self.city_filter_selected)
        self.cmb_communes.currentIndexChanged.connect(
            self.commune_filter_selected)
        self.cmb_giros.currentIndexChanged.connect(self.giro_filter_selected)
        self.lbl_filter_count = QLabel("0 contactos seleccionados")
        filter_layout.addWidget(self.lbl_filter_count)
        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)

        # Mensaje
        message_group = QGroupBox("Mensaje personalizado")
        message_layout = QVBoxLayout()

        # Layout for label and save button
        message_header_layout = QHBoxLayout()
        message_header_layout.addWidget(QLabel(
            "Variables disponibles: [Razón social], [RUT], [Giro], [Dirección], [Comuna], [Ciudad], [Nombre contacto], [Teléfono]"))
        self.btn_save_message = QPushButton("Guardar Mensaje")
        self.btn_save_message.clicked.connect(self.save_message_template)
        message_header_layout.addWidget(self.btn_save_message)
        message_header_layout.addStretch() # Push button to the right

        message_layout.addLayout(message_header_layout) # Add the new header layout

        self.txt_message = QTextEdit()
        self.txt_message.setPlaceholderText(
            "Escribe tu mensaje aquí usando variables entre corchetes..."
        )
        # Read default message template from file in the current working directory
        template_file_path = "default_template.txt" # Changed path
        try:
            with open(template_file_path, "r", encoding="utf-8") as f:
                default_message = f.read()
            self.txt_message.setText(default_message)
        except FileNotFoundError:
            print(f"Error: Default template file not found at {template_file_path}")
            self.txt_message.setPlaceholderText(
                "Error: Default template file not found. Please enter your message here."
            )
        except Exception as e:
            print(f"Error reading default template file: {e}")
            self.txt_message.setPlaceholderText(
                f"Error reading template file: {e}. Please enter your message here."
            )

        message_layout.addWidget(self.txt_message)
        message_group.setLayout(message_layout)
        main_layout.addWidget(message_group)


        # Opciones de envío y Botón Iniciar Envío en la misma fila
        send_area_layout = QHBoxLayout()

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

        self.btn_send = QPushButton("Iniciar Envío")
        self.btn_send.setMinimumHeight(40)
        self.btn_send.clicked.connect(self.start_sending)
        self.btn_send.setEnabled(False)

        send_area_layout.addWidget(send_options_group)
        send_area_layout.addWidget(self.btn_send)
        send_area_layout.addStretch() # Push options and button to the left

        main_layout.addLayout(send_area_layout)

        # Pie de página para el estado/contacto
        footer_layout = QHBoxLayout()
        self.lbl_status = QLabel("c1zc developer Contact: camilo.zavala.c@gmail.com")
        footer_layout.addStretch() # Add stretch before the label
        footer_layout.addWidget(self.lbl_status)
        footer_layout.addStretch() # Add stretch after the label

        main_layout.addLayout(footer_layout)


    def load_data_from_db(self):
        try:
            self.df = self.db_manager.get_all_clients()
            if len(self.df) > 0:
                model = PandasModel(self.df)
                self.table_data.setModel(model)
                header = self.table_data.horizontalHeader()
                for i in range(len(self.df.columns)):
                    header.setSectionResizeMode(i, QHeaderView.Stretch)
                self.lbl_data_status.setText(
                    f"Base de datos cargada: {len(self.df)} registros")
                self.update_filter_options()
                self.filter_data()
                self.btn_send.setEnabled(True)
            else:
                self.lbl_data_status.setText(
                    "No hay datos en la base de datos")
                self.btn_send.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error al cargar datos: {str(e)}")

    def import_excel(self):
        try:
            default_file = "clientes.xlsx"
            if os.path.exists(default_file):
                file_path = default_file
            else:
                from PyQt5.QtWidgets import QFileDialog
                file_path, _ = QFileDialog.getOpenFileName(
                    self, "Seleccionar archivo Excel", "", "Archivos Excel (*.xlsx *.xls)"
                )
            if not file_path:
                return
            success, message = self.db_manager.import_excel_to_db(file_path)
            if success:
                QMessageBox.information(self, "Importación exitosa", message)
                self.load_data_from_db()
            else:
                QMessageBox.warning(self, "Error", message)
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error al importar Excel: {str(e)}")

    def update_filter_options(self):
        self.cmb_cities.clear()
        self.cmb_cities.addItem("Todas las ciudades")
        cities = self.db_manager.get_unique_values("ciudad")
        for city in cities:
            self.cmb_cities.addItem(city.capitalize())
        self.cmb_communes.clear()
        self.cmb_communes.addItem("Todas las comunas")
        communes = self.db_manager.get_unique_values("comuna")
        for commune in communes:
            self.cmb_communes.addItem(commune.capitalize())
        self.cmb_giros.clear()
        self.cmb_giros.addItem("Todos los giros")
        giros = self.db_manager.get_unique_values("giro")
        for giro in giros:
            self.cmb_giros.addItem(giro.capitalize())

    def filter_data(self):
        if self.df is None:
            return
        selected_city = self.cmb_cities.currentText()
        selected_commune = self.cmb_communes.currentText()
        selected_giro = self.cmb_giros.currentText()
        self.df_filtered = self.db_manager.get_filtered_clients(
            city=selected_city if selected_city != "Todas las ciudades" else None,
            commune=selected_commune if selected_commune != "Todas las comunas" else None,
            giro=selected_giro if selected_giro != "Todos los giros" else None
        )
        model = PandasModel(self.df_filtered)
        self.table_data.setModel(model)
        self.lbl_filter_count.setText(
            f"{len(self.df_filtered)} contactos seleccionados")

    def view_history(self):
        try:
            history_df = self.db_manager.get_message_history(limit=500)
            if len(history_df) > 0:
                self.history_window = HistoryWindow(self, history_df)
                self.history_window.show()
            else:
                QMessageBox.information(
                    self, "Historial", "No hay registros en el historial de envíos.")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error al cargar historial: {str(e)}")

    def start_sending(self):
        if self.df_filtered is None or len(self.df_filtered) == 0:
            QMessageBox.warning(
                self, "Error", "No hay contactos seleccionados para enviar")
            return

        message_template = self.txt_message.toPlainText()
        if not message_template:
            QMessageBox.warning(self, "Error", "Debe ingresar un mensaje")
            return

        # Add confirmation dialog here
        reply = QMessageBox.question(
            self,
            "Confirmar envío",
            "¿Ha iniciado sesión en WhatsApp Web en Google Chrome y está listo para enviar los mensajes?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.No:
            QMessageBox.information(
                self,
                "Información",
                "Para enviar mensajes, primero debe iniciar sesión en WhatsApp Web en Google Chrome.\n\n"
                "Pasos:\n"
                "1. Abra Google Chrome.\n"
                "2. Navegue a web.whatsapp.com.\n"
                "3. Escanee el código QR con su teléfono.\n"
                "4. Una vez logueado, regrese a esta aplicación e intente nuevamente."
            )
            return # Stop the sending process if user is not ready

        # Crear y mostrar ventana de progreso
        self.progress_dialog = SendProgressDialog(self)
        self.progress_dialog.stop_requested.connect(self.stop_sending)
        self.progress_dialog.show()

        # Configurar interfaz (deshabilitar controles principales)
        self.btn_send.setEnabled(False)
        self.btn_load_excel.setEnabled(False)
        self.cmb_cities.setEnabled(False)
        self.cmb_communes.setEnabled(False)
        self.cmb_giros.setEnabled(False)
        # The stop button is part of the progress dialog, so no need to enable it here

        # Iniciar hilo de envío
        self.sender_thread = WhatsAppSenderThread(
            self.df_filtered,
            message_template,
            self.db_manager,
            test_mode=self.chk_test_mode.isChecked(),
            check_history=self.chk_avoid_resend.isChecked()
        )

        # Conectar señales
        self.sender_thread.progress_update.connect(self.progress_dialog.update_progress)
        self.sender_thread.message_sent.connect(self.register_sent_message) # This slot is empty
        self.sender_thread.finished_sending.connect(self.sending_finished)
        self.sender_thread.log_message.connect(self.progress_dialog.add_log_entry)

        self.sender_thread.start()

        # Update status label (optional, progress dialog shows detailed status)
        self.lbl_status.setText("Iniciando envío...")


    def stop_sending(self):
        if self.sender_thread and self.sender_thread.isRunning():
            self.sender_thread.stop()

    def register_sent_message(self, razon_social, telefono, ciudad, success):
        # This slot is connected but currently does nothing.
        # The progress dialog handles logging and the DB manager records the history.
        pass

    def sending_finished(self):
        try:
            # Fetch history to show summary. Limit to a reasonable number for the summary.
            # The full history is in the DB and viewable via the history window.
            history_df = self.db_manager.get_message_history(limit=500) # Increased limit for summary
            # Filter for the current sending session if possible, or just show overall stats
            # For simplicity, showing overall stats from recent history
            total_attempts = len(history_df) # This is not accurate for the current session only
            successful_sends = len(history_df[history_df['resultado'] == 'Éxito']) # Also not accurate for current session only

            # A more accurate summary would require tracking results within the thread
            # and passing them back, or querying history specifically for the last session.
            # For now, let's provide a general message and direct to history window.

            QMessageBox.information(
                self,
                "Envío completado",
                "El proceso de envío ha finalizado.\n"
                "Por favor, revise el log en la ventana de progreso para detalles.\n"
                "El historial completo se guarda automáticamente en la base de datos y puede verlo en la ventana 'Ver Historial de Envíos'.\"\n\n"
                "c1zc developer Contact: camilo.zavala.c@gmail.com" # Added contact info here too
            )

        except Exception as e:
            QMessageBox.warning(
                self,
                "Error al finalizar envío",
                f"El proceso de envío ha finalizado, pero ocurrió un error al obtener el resumen: {str(e)}\n"
                "Por favor, revise el log en la ventana de progreso para detalles.\"\n\n"
                "c1zc developer Contact: camilo.zavala.c@gmail.com" # Added contact info here too
            )

        # Re-enable controls
        self.btn_send.setEnabled(True)
        self.btn_load_excel.setEnabled(True)
        self.cmb_cities.setEnabled(True)
        self.cmb_communes.setEnabled(True)
        self.cmb_giros.setEnabled(True)
        # Reset status label to the contact info after sending finishes
        self.lbl_status.setText("c1zc developer Contact: camilo.zavala.c@gmail.com")


    def city_filter_selected(self):
        if self.cmb_cities.currentIndex() > 0:
            self.cmb_communes.setEnabled(False)
            self.cmb_giros.setEnabled(False)
        else:
            self.cmb_communes.setEnabled(True)
            self.cmb_giros.setEnabled(True)
        self.filter_data()

    def commune_filter_selected(self):
        if self.cmb_communes.currentIndex() > 0:
            self.cmb_cities.setEnabled(False)
            self.cmb_giros.setEnabled(False)
        else:
            self.cmb_cities.setEnabled(True)
            self.cmb_giros.setEnabled(True)
        self.filter_data()

    def giro_filter_selected(self):
        if self.cmb_giros.currentIndex() > 0:
            self.cmb_cities.setEnabled(False)
            self.cmb_communes.setEnabled(False)
        else:
            self.cmb_cities.setEnabled(True)
            self.cmb_communes.setEnabled(True)
        self.filter_data()

    def save_message_template(self):
        template_file_path = "default_template.txt" # Changed path
        message_content = self.txt_message.toPlainText()
        try:
            # Ensure the directory exists (not strictly needed for current dir, but good practice)
            # os.makedirs(os.path.dirname(template_file_path), exist_ok=True) # Not needed for current dir
            with open(template_file_path, "w", encoding="utf-8") as f:
                f.write(message_content)
            QMessageBox.information(self, "Guardado Exitoso", "El mensaje ha sido guardado en default_template.txt")
        except Exception as e:
            QMessageBox.critical(self, "Error al Guardar", f"No se pudo guardar el mensaje: {str(e)}")
