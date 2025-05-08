from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTextEdit, 
                           QProgressBar, QPushButton, QLabel)
from PyQt5.QtCore import Qt, pyqtSignal

class SendProgressDialog(QDialog):
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Progreso de Envío")
        self.setModal(False)  # Permite interactuar con la ventana principal
        self.setGeometry(200, 200, 600, 400)

        layout = QVBoxLayout()

        # Progreso numérico
        self.lbl_progress = QLabel("Progreso: 0/0")
        layout.addWidget(self.lbl_progress)

        # Barra de progreso
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Log detallado
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # Botón detener
        self.btn_stop = QPushButton("Detener Envío")
        self.btn_stop.clicked.connect(self.request_stop)
        layout.addWidget(self.btn_stop)

        self.setLayout(layout)

    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.lbl_progress.setText(f"Progreso: {current}/{total}")

    def add_log_entry(self, text):
        self.log_text.append(text)
        # Auto-scroll al final
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def request_stop(self):
        self.stop_requested.emit()