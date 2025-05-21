from gtts import gTTS
import os
from pydub import AudioSegment
import time
from pathlib import Path


BASE_DIR = Path(__file__).parent.parent.resolve()
TTS_DIR = BASE_DIR / 'public' / 'tts'
TTS_DIR.mkdir(parents=True, exist_ok=True)

def text_to_speech(text, lang='de'):
    """Converte o texto em áudio e salva em public/tts"""
    tts = gTTS(text=text, lang=lang, slow=False)
    timestamp = int(time.time() * 1000)
    filename = f"tts_{timestamp}.mp3"
    out_path = TTS_DIR / filename
    tts.save(str(out_path))
    return filename

