import tkinter as tk
import sounddevice as sd
import numpy as np
import wave
import threading
import queue
import time
import whisper
from openai import OpenAI
client = OpenAI(api_key='')

# Parâmetros de gravação
fs = 44100         # taxa de amostragem (Hz)
channels = 1       # mono
audio_queue = queue.Queue()
recording = False  # flag de gravação

# Função callback para capturar áudio
def audio_callback(indata, frames, time_info, status):
    if status:
        print(status)
    # Coloca os dados capturados na fila
    audio_queue.put(indata.copy())

# Função que gerencia a gravação em um thread separado
def record_audio():
    global recording
    recording = True
    # Limpa a fila
    while not audio_queue.empty():
        audio_queue.get()
    # Inicia a gravação com sounddevice em um fluxo (stream)
    with sd.InputStream(samplerate=fs, channels=channels, callback=audio_callback):
        while recording:
            sd.sleep(100)  # dorme 100 ms para reduzir uso de CPU

# Função para salvar o áudio gravado em um arquivo WAV
def save_audio(filename):
    frames = []
    # Consome todos os dados da fila
    while not audio_queue.empty():
        frames.append(audio_queue.get())
    if frames:
        audio_data = np.concatenate(frames, axis=0)
        # Converte para int16
        audio_int16 = np.int16(audio_data * 32767)
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # 16 bits = 2 bytes
            wf.setframerate(fs)
            wf.writeframes(audio_int16.tobytes())
        print(f"Áudio salvo em {filename}")
        return filename
    else:
        print("Nenhum áudio capturado!")
        return None



def process_audio_with_llm(audio_filename):
    """
    Neste ponto, você pode:
      1. Enviar o arquivo de áudio para um serviço de STT (por exemplo, OpenAI Whisper)
         para obter uma transcrição.
      2. Enviar a transcrição para o seu LLM (ex.: GPT-3.5) para processamento adicional.
    """
    # Usando OpenAI Whisper para transcrição
    model = whisper.load_model("base")
    result = model.transcribe(audio_filename)
    transcript = result["text"]
    print("Transcrição:", transcript)
    
    # Enviando o texto para o LLM
    response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": f"Transcrição: {transcript}\nTraduza esse texto para alemão:"}]
    )

    print("Resposta do LLM:", response.choices[0].message.content)



# Funções dos botões da interface
def start_recording():
    global record_thread
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)
    # Inicia o thread de gravação
    record_thread = threading.Thread(target=record_audio)
    record_thread.start()
    status_label.config(text="Gravando...")

def stop_recording():
    global recording
    stop_button.config(state=tk.DISABLED)
    recording = False
    # Aguarda o término do thread de gravação
    record_thread.join()
    status_label.config(text="Gravação finalizada.")
    # Salva o áudio em um arquivo WAV
    filename = "output.wav"
    saved = save_audio(filename)
    if saved:
        # Envie para o LLM (ou inicie a transcrição e então envie)
        process_audio_with_llm(saved)
    start_button.config(state=tk.NORMAL)

# Cria a interface com Tkinter
root = tk.Tk()
root.title("Gravador de Áudio para LLM")

frame = tk.Frame(root, padx=10, pady=10)
frame.pack()

start_button = tk.Button(frame, text="Iniciar Gravação", command=start_recording, width=20)
start_button.grid(row=0, column=0, padx=5, pady=5)

stop_button = tk.Button(frame, text="Parar Gravação", command=stop_recording, state=tk.DISABLED, width=20)
stop_button.grid(row=0, column=1, padx=5, pady=5)

status_label = tk.Label(frame, text="Clique em 'Iniciar Gravação' para começar.", pady=10)
status_label.grid(row=1, column=0, columnspan=2)

root.mainloop()
