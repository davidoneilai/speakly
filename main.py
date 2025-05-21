import os
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, url_for
from src.recorder import start_recording, stop_recording
from src.transcriber import process_audio_with_llm
from src.text_to_speech import text_to_speech

# 1) BASE_DIR agora é a pasta onde está o main.py (a raiz do projeto)
BASE_DIR = Path(__file__).parent.resolve()

# 2) Configure o Flask para servir public/ como estático
app = Flask(
    __name__,
    static_folder=str(BASE_DIR / 'public'),
    static_url_path=''   # serve css/, js/, img/ diretamente em /css, /js, /img
)

# 3) Diretorio temp/ na raiz do projeto
TEMP_DIR = BASE_DIR / 'temp'
TEMP_DIR.mkdir(exist_ok=True)

# Rota principal
@app.route('/')
def index():
    return app.send_static_file('index.html')

# Endpoint que recebe o áudio gravado do front
@app.route('/api/stop_recording', methods=['POST'])
def api_stop_recording():
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'nenhum arquivo enviado'}), 400

    temp_path = TEMP_DIR / f.filename
    f.save(temp_path)

    try:
        llm_resp = process_audio_with_llm(str(temp_path))
        tts_filename = text_to_speech(llm_resp, lang='de')
        # agora retornamos a URL para o front
        audio_url = url_for('serve_tts', filename=tts_filename, _external=False)
        print(f"Audio URL: {audio_url}")
        return jsonify({'audio_url': audio_url, "llm_response": tts_filename}), 200

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# rota para servir o áudio TTS
@app.route('/tts/<filename>')
def serve_tts(filename):
    return send_from_directory(str(BASE_DIR / 'public' / 'tts'), filename)

if __name__ == '__main__':
    # por padrão roda em http://127.0.0.1:5000/
    app.run(debug=True)
