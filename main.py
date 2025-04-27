import sys
from PyQt5.QtWidgets import QApplication
from src.views.main_window import NostraWhatsApp

def main():
    app = QApplication(sys.argv)
    window = NostraWhatsApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()