import whisper
from openai import OpenAI
from pyhocon import ConfigFactory
import os

config = ConfigFactory.parse_file("speakly.conf")
api_key = config.get('openai.key')
llm_model = config.get('openai.llm')

client = OpenAI(api_key=api_key)

def transcribe_audio(audio_filename):
    model = whisper.load_model("base")
    result = model.transcribe(audio_filename)
    return result["text"]

def send_to_llm(text):
    response = client.chat.completions.create(
        model=llm_model,
        messages=[{"role": "user", "content": f"""
                   Pegue esse texto: {text}\n
                   E responda como se fosse uma conversa, mas responda em alemão.
                   """}]
    )
    return response.choices[0].message.content

def process_audio_with_llm(audio_filename):
    transcript = transcribe_audio(audio_filename)
    return send_to_llm(transcript)
