from gtts import gTTS
import os

def text_to_speech(text, lang='de'):
    """Converte o texto em áudio e salva como um arquivo de som."""
    tts = gTTS(text=text, lang=lang, slow=False)
    output_file = "temp/output_audio.wav"
    
    if not os.path.exists("temp"):
        os.makedirs("temp")
    
    tts.save(output_file)
    print(f"Áudio salvo em: {output_file}")
    return output_file

def play_audio(file_path):
    """Reproduz o áudio gerado."""
    os.system(f"start {file_path}")  # No Linux ou MacOS, troque 'start' por 'afplay' ou 'open'
