from PyQt5.QtCore import QThread, pyqtSignal
import pywhatkit
import time
import random
import re

class WhatsAppSenderThread(QThread):
    progress_update = pyqtSignal(int, int)
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
            if phone.startswith('9') and len(phone) == 9:
                formatted_phone = f"+56{phone}"
                valid_phone = True
            elif phone.startswith('569') and len(phone) == 11:
                formatted_phone = f"+{phone}"
                valid_phone = True
            elif phone.startswith('+569') and len(phone) == 12:
                formatted_phone = phone
                valid_phone = True
            if self.check_history and formatted_phone in sent_numbers:
                self.message_sent.emit(
                    row['Razón social'],
                    formatted_phone,
                    row['Ciudad'],
                    False
                )
                self.progress_update.emit(sent_count, total)
                continue
            if valid_phone:
                message = self.message_template
                for col in self.df.columns:
                    placeholder = f"[{col}]"
                    if placeholder in message:
                        message = message.replace(placeholder, str(row[col]))
                # print(f"Enviando a {formatted_phone}: {message}")  # <-- Para depuración
                success = False
                try:
                    pywhatkit.sendwhatmsg_instantly(
                        formatted_phone,
                        message,
                        wait_time=20,  # Prueba con 20 o 30
                        tab_close=True
                    )
                    success = True
                    sent_count += 1
                except Exception as e:
                    print(f"Error al enviar mensaje: {e}")
                resultado = "Éxito" if success else "Error"
                self.db_manager.record_message_sent(
                    row['Razón social'],
                    formatted_phone,
                    row['Ciudad'],
                    resultado
                )
                self.message_sent.emit(
                    row['Razón social'],
                    formatted_phone,
                    row['Ciudad'],
                    success
                )
                self.progress_update.emit(sent_count, total)
                if not self.test_mode and index < len(process_df) - 1:
                    time.sleep(random.uniform(3, 7))
            else:
                self.db_manager.record_message_sent(
                    row['Razón social'],
                    phone,
                    row['Ciudad'],
                    "Error - Número inválido"
                )
                self.message_sent.emit(
                    row['Razón social'],
                    phone,
                    row['Ciudad'],
                    False
                )
                self.progress_update.emit(sent_count, total)
        self.finished_sending.emit()

    def stop(self):
        self.stop_requested = True