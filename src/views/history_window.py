from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTableView, QLabel, QPushButton, QHeaderView, QHBoxLayout, QMessageBox
from PyQt5.QtCore import Qt # Import Qt for selection behavior
from ..models.pandas_model import PandasModel

class HistoryWindow(QMainWindow):
    def __init__(self, parent=None, history_df=None):
        super().__init__(parent)
        self.history_df = history_df
        self.db_manager = parent.db_manager # Get the db_manager from the parent (main window)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Historial de Envíos")
        self.setGeometry(150, 150, 800, 500)
        central_widget = QWidget()
        main_layout = QVBoxLayout()

        main_layout.addWidget(QLabel(f"Últimos {len(self.history_df)} envíos registrados:"))

        self.table_history = QTableView()
        model = PandasModel(self.history_df)
        self.table_history.setModel(model)
        header = self.table_history.horizontalHeader()
        for i in range(len(self.history_df.columns)):
            header.setSectionResizeMode(i, QHeaderView.Stretch)

        # Allow selecting multiple rows
        self.table_history.setSelectionBehavior(QTableView.SelectRows)
        self.table_history.setSelectionMode(QTableView.ExtendedSelection)

        main_layout.addWidget(self.table_history)

        # Layout for buttons
        button_layout = QHBoxLayout()

        self.btn_delete_selected = QPushButton("Eliminar Seleccionados")
        self.btn_delete_selected.clicked.connect(self.delete_selected_history)
        button_layout.addWidget(self.btn_delete_selected)

        button_layout.addStretch() # Push buttons to the left

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.close)
        button_layout.addWidget(btn_close)

        main_layout.addLayout(button_layout)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def delete_selected_history(self):
        selected_indexes = self.table_history.selectedIndexes()
        if not selected_indexes:
            QMessageBox.information(self, "Información", "Seleccione los registros que desea eliminar.")
            return

        # Get the row indices of the selected items
        selected_rows = sorted(list(set(index.row() for index in selected_indexes)))

        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de que desea eliminar {len(selected_rows)} registros del historial?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            model = self.table_history.model()
            if not isinstance(model, PandasModel):
                 QMessageBox.critical(self, "Error", "No se pudo obtener el modelo de datos.")
                 return

            # Get the IDs from the selected rows in the history_df
            # Ensure 'id' column exists in history_df
            if 'id' not in self.history_df.columns:
                 QMessageBox.critical(self, "Error", "La columna 'id' no está disponible en los datos del historial.")
                 return

            ids_to_delete = [self.history_df.iloc[row]['id'] for row in selected_rows]

            # Add a print statement to show IDs being deleted
            print(f"Attempting to delete history records with IDs: {ids_to_delete}")

            try:
                self.db_manager.delete_history_records(ids_to_delete)
                QMessageBox.information(self, "Éxito", f"{len(ids_to_delete)} registros eliminados.")
                self.refresh_history() # Refresh the displayed history
                print(f"HistoryWindow: After refresh, history_df has {len(self.history_df)} records.") # Added print
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al eliminar registros: {str(e)}")


    def refresh_history(self):
        # Reload history from the database and update the table view
        try:
            updated_history_df = self.db_manager.get_message_history(limit=500)
            self.history_df = updated_history_df
            model = PandasModel(updated_history_df)
            self.table_history.setModel(model)
            
            header = self.table_history.horizontalHeader()
            for i in range(len(updated_history_df.columns)):
                header.setSectionResizeMode(i, QHeaderView.Stretch)
                
            current_count_label = self.findChild(QLabel, "current_count_label")
            if current_count_label:
                current_count_label.setText(f"Últimos {len(updated_history_df)} envíos registrados:")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al actualizar historial: {str(e)}")

    # Override close event to potentially clean up
    def closeEvent(self, event):
        # Any cleanup needed when the window is closed
        event.accept() # Accept the close event
