from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTableView, QLabel, QPushButton, QHeaderView
from ..models.pandas_model import PandasModel

class HistoryWindow(QMainWindow):
    def __init__(self, parent=None, history_df=None):
        super().__init__(parent)
        self.history_df = history_df
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Historial de Envíos")
        self.setGeometry(150, 150, 800, 500)
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Últimos {len(self.history_df)} envíos registrados:"))
        self.table_history = QTableView()
        model = PandasModel(self.history_df)
        self.table_history.setModel(model)
        header = self.table_history.horizontalHeader()
        for i in range(len(self.history_df.columns)):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        layout.addWidget(self.table_history)
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)