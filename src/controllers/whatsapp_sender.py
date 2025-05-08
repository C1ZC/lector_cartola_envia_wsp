from PyQt5.QtCore import QThread, pyqtSignal
import pywhatkit
import time
import random
import re

class WhatsAppSenderThread(QThread):
    progress_update = pyqtSignal(int, int)
    # message_sent signal is connected but its slot in main_window is empty,
    # keeping it for now but it doesn't affect the UI progress display.
    message_sent = pyqtSignal(str, str, str, bool)
    finished_sending = pyqtSignal()
    log_message = pyqtSignal(str)

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
        processed_count = 0 # Contador para contactos procesados (intentados o saltados)
        sent_numbers = set()
        if self.check_history:
            sent_numbers = self.db_manager.get_sent_phones()
        process_df = self.df.head(1) if self.test_mode else self.df

        for index, row in process_df.iterrows():
            if self.stop_requested:
                break

            phone = str(row['Teléfono']).strip()
            phone = re.sub(r'\D', '', phone)
            valid_phone = False
            formatted_phone = phone # Default to raw phone

            # Phone number validation and formatting
            if phone.startswith('9') and len(phone) == 9:
                formatted_phone = f"+56{phone}"
                valid_phone = True
            elif phone.startswith('569') and len(phone) == 11:
                formatted_phone = f"+{phone}"
                valid_phone = True
            elif phone.startswith('+569') and len(phone) == 12:
                formatted_phone = phone
                valid_phone = True

            razon_social = row['Razón social']
            ciudad = row['Ciudad']
            rut = str(row['RUT']) # Get RUT from the row
            nombre_contacto = str(row['Nombre contacto']) # Get Nombre contacto from the row


            # Check history BEFORE processing
            if self.check_history and valid_phone and formatted_phone in sent_numbers:
                # Modified log message to include RUT and Nombre contacto
                self.log_message.emit(f"Saltando a {razon_social} (RUT: {rut}, Contacto: {nombre_contacto}, Teléfono: {formatted_phone}): Ya enviado con éxito.")
                processed_count += 1 # Incrementar contador de procesados
                self.progress_update.emit(processed_count, total)
                continue # Saltar al siguiente contacto

            if valid_phone:
                # Prepare personalized message
                message = self.message_template
                for col in self.df.columns:
                    placeholder = f"[{col}]"
                    if placeholder in message:
                        message = message.replace(placeholder, str(row[col]))

                self.log_message.emit(f"Enviando mensaje a {razon_social} ({formatted_phone})...")
                success = False

                try:
                    # Usar pywhatkit sin especificar navegador
                    pywhatkit.sendwhatmsg_instantly(
                        formatted_phone,
                        message,
                        wait_time=15,  # Tiempo reducido
                        tab_close=True,
                        close_time=3   # Tiempo para cerrar la pestaña
                    )

                    # Dar tiempo para que se complete el envío
                    time.sleep(2)
                    success = True

                except Exception as e:
                    self.log_message.emit(f"Error al enviar a {razon_social} ({formatted_phone}): {str(e)}")

                # Registrar resultado
                resultado = "Éxito" if success else "Error"
                self.db_manager.record_message_sent(
                    razon_social,
                    formatted_phone,
                    ciudad,
                    resultado
                )

                # Emitir señales de progreso y log
                # self.message_sent.emit(razon_social, formatted_phone, ciudad, success) # Signal connected but slot is empty

                processed_count += 1 # Incrementar contador de procesados
                self.progress_update.emit(processed_count, total)


                # Esperar entre mensajes
                if not self.test_mode and processed_count < total and not self.stop_requested: # Check processed_count and stop_requested
                    delay = random.uniform(3, 5)  # Reducido el tiempo de espera
                    self.log_message.emit(f"Esperando {delay:.1f} segundos...")
                    time.sleep(delay)

            else: # Invalid phone number
                self.log_message.emit(f"Saltando a {razon_social} ({phone}): Número inválido.")
                self.db_manager.record_message_sent(
                    razon_social,
                    phone,
                    ciudad,
                    "Error - Número inválido"
                )
                # self.message_sent.emit(razon_social, phone, ciudad, False) # Signal connected but slot is empty

                processed_count += 1 # Incrementar contador de procesados
                self.progress_update.emit(processed_count, total)


        self.finished_sending.emit()

    def stop(self):
        self.stop_requested = True
