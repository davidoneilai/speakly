import whisper
from openai import OpenAI
import config

client = OpenAI(api_key=config.api_key)

def transcribe_audio(audio_filename):
    model = whisper.load_model("base")
    result = model.transcribe(audio_filename)
    return result["text"]

def send_to_llm(text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Transcrição: {text}\nTraduza esse texto para alemão:"}]
    )
    return response.choices[0].message.content

def process_audio_with_llm(audio_filename):
    transcript = transcribe_audio(audio_filename)
    return send_to_llm(transcript)
