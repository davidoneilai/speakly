from gtts import gTTS
import pygame
import os
from pydub import AudioSegment

def text_to_speech(text, lang='de'):
    """Converte o texto em áudio e salva como um arquivo de som."""
    tts = gTTS(text=text, lang=lang, slow=False)
    mp3_file = "temp/output_audio.mp3"
    
    if not os.path.exists("temp"):
        os.makedirs("temp")
    
    tts.save(mp3_file)

    wav_file = "temp/output_audio.wav"
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
