import os
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, url_for
from pyhocon import ConfigFactory
from src.recorder import start_recording, stop_recording
from src.transcriber import process_audio_with_llm, transcribe_audio
from src.text_to_speech import text_to_speech_with_quality, get_tts_info
# from googletrans import Translator  # Comentado temporariamente por conflito de dependências

# 1) BASE_DIR agora é a pasta onde está o main.py (a raiz do projeto)
BASE_DIR = Path(__file__).parent.resolve()

# Carregar configurações
config = ConfigFactory.parse_file(str(BASE_DIR / 'speakly.conf'))

# 2) Configure o Flask para servir public/ como estático
app = Flask(
    __name__,
    static_folder=str(BASE_DIR / 'public'),
    static_url_path=''   # serve css/, js/, img/ diretamente em /css, /js, /img
)

# 3) Diretorio temp/ na raiz do projeto
TEMP_DIR = BASE_DIR / 'temp'
TEMP_DIR.mkdir(exist_ok=True)

# Função para obter configurações de TTS
def get_tts_config():
    return {
        'provider': config.get('tts.provider', 'auto'),
        'quality': config.get('tts.quality', 'normal'),
        'openai_voice': config.get('tts.openai.voice', 'nova'),
        'gtts_lang': config.get('tts.gtts.lang', 'en').split(','),
        'gtts_slow': config.get('tts.gtts.slow', False)
    }

# Rota principal
@app.route('/')
def index():
    return app.send_static_file('index.html')

# Rota para informações do TTS
@app.route('/api/tts_info')
def api_tts_info():
    tts_info = get_tts_info()
    tts_config = get_tts_config()
    
    return jsonify({
        'providers': tts_info,
        'current_config': tts_config,
        'active_provider': 'openai' if tts_info['openai']['available'] and tts_config['provider'] in ['auto', 'openai'] else 'gtts'
    })

# Endpoint que recebe o áudio gravado do front
@app.route('/api/stop_recording', methods=['POST'])
def api_stop_recording():
    f = request.files.get('file')
    user_level = request.form.get('user_level', 'begginer')  # Recebe o nível enviado

    if not f:
        return jsonify({'error': 'nenhum arquivo enviado'}), 400

    temp_path = TEMP_DIR / f.filename
    f.save(temp_path)

    try:
        # Chama apenas process_audio_with_llm que já faz a transcrição
        result = process_audio_with_llm(str(temp_path),  user_level=user_level)

        # Extrai os resultados
        transcription = result['transcription']
        llm_response = result['llm_response']

        # Gera o áudio da resposta usando configuração atual
        tts_config = get_tts_config()
        tts_filename = text_to_speech_with_quality(
            llm_response, 
            provider=tts_config['provider'],
            quality=tts_config['quality'],
            lang=tts_config.get('gtts_lang', 'en')
        )
        audio_url = url_for('serve_tts', filename=tts_filename, _external=False)

        return jsonify({
            'level': user_level,
            'transcription': transcription,
            'llm_response': llm_response,
            'audio_url': audio_url
        }), 200

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# rota para servir o áudio TTS
@app.route('/tts/<filename>')
def serve_tts(filename):
    return send_from_directory(str(BASE_DIR / 'public' / 'tts'), filename)

# Endpoint para traduzir texto do chinês para inglês
@app.route('/api/translate', methods=['POST'])
def api_translate():
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'Texto não fornecido'}), 400
        
        # Importar função de tradução do transcriber que já tem OpenAI configurado
        try:
            from src.transcriber import translate_text_with_llm
            translated_text = translate_text_with_llm(text)
            
            return jsonify({
                'original_text': text,
                'translated_text': translated_text,
                'detected_language': 'zh'
            }), 200
            
        except ImportError:
            # Fallback: tradução placeholder
            return jsonify({
                'original_text': text,
                'translated_text': f"[English translation of: {text}]",
                'detected_language': 'zh'
            }), 200
        
    except Exception as e:
        print(f"Erro na tradução: {e}")
        return jsonify({'error': f'Erro ao traduzir: {str(e)}'}), 500

if __name__ == '__main__':
    # por padrão roda em http://127.0.0.1:5000/
    app.run(debug=True)
