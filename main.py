import sys
from PyQt6.QtWidgets import QApplication
from src.ui import AudioRecorderApp 

def main():
    app = QApplication(sys.argv)
    window = AudioRecorderApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
