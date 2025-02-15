import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout
from PyQt6.QtGui import QFont, QMovie
from PyQt6.QtCore import Qt
from src.recorder import start_recording, stop_recording
from src.transcriber import process_audio_with_llm
from src.text_to_speech import text_to_speech, play_audio

class AudioRecorderApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Gravador de Áudio para LLM")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: #2C3E50; color: white;")

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gif_label = QLabel(self)
        self.movie = QMovie("img/ai_speaking.gif")
        self.gif_label.setMovie(self.movie)
        layout.addWidget(self.gif_label, alignment=Qt.AlignmentFlag.AlignCenter)

        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Iniciar Gravação")
        self.start_button.setStyleSheet("background-color: #27AE60; color: white; font-size: 16px; padding: 10px;")
        self.start_button.clicked.connect(self.start_recording_action)

        self.stop_button = QPushButton("Parar Gravação")
        self.stop_button.setStyleSheet("background-color: #C0392B; color: white; font-size: 16px; padding: 10px;")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_recording_action)

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)

        # Status label
        self.status_label = QLabel("Clique em 'Iniciar Gravação' para começar.")
        self.status_label.setFont(QFont("Helvetica", 14))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def start_recording_action(self):
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("Gravando...")
        start_recording()

    def stop_recording_action(self):
        self.stop_button.setEnabled(False)
        filename = stop_recording()

        if filename:
            self.movie.start()  
            self.status_label.setText("Processando áudio...")
            llm_response = process_audio_with_llm(filename)
            self.movie.stop()
            self.status_label.setText(f"Resposta: {llm_response}")

            audio_file = text_to_speech(llm_response, lang='de')
            play_audio(audio_file)

        self.start_button.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AudioRecorderApp()
    window.show()
    sys.exit(app.exec())
