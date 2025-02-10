import sounddevice as sd
import numpy as np
import wave
import queue
import threading
import os

fs = 44100  # Taxa de amostragem (Hz)
channels = 1  # Mono
audio_queue = queue.Queue()
recording = False

def audio_callback(indata, frames, time_info, status):
    if status:
        print(status)
    audio_queue.put(indata.copy())

def record_audio():
    global recording
    recording = True
    while not audio_queue.empty():
        audio_queue.get()
    with sd.InputStream(samplerate=fs, channels=channels, callback=audio_callback):
        while recording:
            sd.sleep(100)

def save_audio(filename):
    frames = []
    while not audio_queue.empty():
        frames.append(audio_queue.get())
    if frames:
        audio_data = np.concatenate(frames, axis=0)
        audio_int16 = np.int16(audio_data * 32767)
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(fs)
            wf.writeframes(audio_int16.tobytes())
        return filename
    return None

def start_recording():
    global record_thread
    record_thread = threading.Thread(target=record_audio)
    record_thread.start()

def stop_recording():
    global recording
    recording = False
    record_thread.join()
    output_dir = "temp"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_path = os.path.join(output_dir, "output.wav")
    return save_audio(output_path)
