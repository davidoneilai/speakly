from gtts import gTTS
import pygame
import os
from pydub import AudioSegment
import time

def text_to_speech(text, lang='de'):
    """Converte o texto em áudio e salva como um arquivo de som único."""
    tts = gTTS(text=text, lang=lang, slow=False)
    timestamp = int(time.time() * 1000)
    temp_dir = "temp"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    mp3_file = f"{temp_dir}/output_audio_{timestamp}.mp3"
    wav_file = f"{temp_dir}/output_audio_{timestamp}.wav"

    tts.save(mp3_file)
    audio = AudioSegment.from_mp3(mp3_file)
    audio.export(wav_file, format="wav")

    print(f"Áudio salvo em: {wav_file}")
    return wav_file

def play_audio(file_path):
    """Reproduz o áudio gerado usando pygame."""
    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
