import sys
from PySide6.QtWidgets import QApplication
from gui import TranslationApp

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TranslationApp()
    window.show()
    sys.exit(app.exec())