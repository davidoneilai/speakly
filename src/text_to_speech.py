import os
import time
from pathlib import Path
from openai import OpenAI
from gtts import gTTS

BASE_DIR = Path(__file__).parent.parent.resolve()
TTS_DIR = BASE_DIR / 'public' / 'tts'
TTS_DIR.mkdir(parents=True, exist_ok=True)

# Inicializar cliente OpenAI (apenas se a chave estiver disponível)
openai_client = None
if os.getenv("OPENAI_API_KEY"):
    try:
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except Exception as e:
        print(f"Aviso: Não foi possível inicializar OpenAI TTS: {e}")

def text_to_speech_openai(text, voice='nova', model='tts-1', speed=1.0):
    """
    Converte texto em áudio usando OpenAI TTS (Pago - Alta Qualidade)
    
    Args:
        text (str): Texto para converter
        voice (str): Voz ('alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer')
        model (str): Modelo ('tts-1' para rapidez, 'tts-1-hd' para qualidade)
        speed (float): Velocidade (0.25 - 4.0)
    
    Returns:
        str: Nome do arquivo gerado ou None se falhar
    """
    if not openai_client:
        raise Exception("OpenAI TTS não está disponível. Verifique a OPENAI_API_KEY.")
    
    timestamp = int(time.time() * 1000)
    filename = f"tts_openai_{timestamp}.mp3"
    out_path = TTS_DIR / filename
    
    try:
        response = openai_client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            response_format="mp3",
            speed=speed
        )
        
        with open(out_path, 'wb') as f:
            f.write(response.content)
            
        return filename
    
    except Exception as e:
        print(f"Erro no OpenAI TTS: {e}")
        return None

def text_to_speech_gtts(text, lang='en', slow=False):
    """
    Converte texto em áudio usando Google TTS (Gratuito)
    
    Args:
        text (str): Texto para converter
        lang (str): Idioma ('en', 'es', 'fr', 'pt', 'zh', etc.)
        slow (bool): Velocidade lenta (False = velocidade normal)
    
    Returns:
        str: Nome do arquivo gerado ou None se falhar
    """
    timestamp = int(time.time() * 1000)
    filename = f"tts_gtts_{timestamp}.mp3"
    out_path = TTS_DIR / filename
    
    try:
        tts = gTTS(text=text, lang=lang, slow=slow)
        tts.save(str(out_path))
        return filename
    
    except Exception as e:
        print(f"Erro no Google TTS: {e}")
        return None

def text_to_speech(text, provider='auto', **kwargs):
    """
    Converte texto em áudio usando o provider especificado
    
    Args:
        text (str): Texto para converter
        provider (str): 'openai', 'gtts', ou 'auto' (detecta automaticamente)
        **kwargs: Argumentos específicos para cada provider
    
    Returns:
        str: Nome do arquivo gerado ou None se falhar
    """
    if not text or not text.strip():
        print("Aviso: Texto vazio fornecido para TTS")
        return None
    
    # Auto-detecção: usa OpenAI se disponível, senão gTTS
    if provider == 'auto':
        provider = 'openai' if openai_client else 'gtts'
    
    print(f"🔊 Usando TTS: {provider.upper()}")
    
    if provider == 'openai':
        if not openai_client:
            print("⚠️  OpenAI TTS não disponível, fallback para gTTS")
            return text_to_speech_gtts(text, **kwargs)
        
        # Argumentos específicos do OpenAI
        openai_args = {
            'voice': kwargs.get('voice', 'nova'),
            'model': kwargs.get('model', 'tts-1'),
            'speed': kwargs.get('speed', 1.0)
        }
        return text_to_speech_openai(text, **openai_args)
    
    elif provider == 'gtts':
        # Argumentos específicos do gTTS
        gtts_args = {
            'lang': kwargs.get('lang', 'en'),
            'slow': kwargs.get('slow', False)
        }
        return text_to_speech_gtts(text, **gtts_args)
    
    else:
        raise ValueError(f"Provider '{provider}' não suportado. Use 'openai', 'gtts' ou 'auto'")

def text_to_speech_with_quality(text, provider='auto', quality='normal', lang='en'):
    """
    Converte texto em áudio com configurações predefinidas de qualidade
    
    Args:
        text (str): Texto para converter
        provider (str): 'openai', 'gtts', ou 'auto'
        quality (str): 'fast', 'normal', 'high' (afeta configurações)
        lang (str): Idioma para gTTS ('en', 'es', 'fr', 'pt', 'zh', etc.)
    
    Returns:
        str: Nome do arquivo gerado
    """
    # Configurações por qualidade
    configs = {
        'fast': {
            'openai': {'voice': 'alloy', 'model': 'tts-1', 'speed': 1.25},
            'gtts': {'lang': lang, 'slow': False}
        },
        'normal': {
            'openai': {'voice': 'nova', 'model': 'tts-1', 'speed': 1.0},
            'gtts': {'lang': lang, 'slow': False}
        },
        'high': {
            'openai': {'voice': 'nova', 'model': 'tts-1-hd', 'speed': 1.0},
            'gtts': {'lang': lang, 'slow': False}
        }
    }
    
    # Detecta provider se auto
    actual_provider = provider
    if provider == 'auto':
        actual_provider = 'openai' if openai_client else 'gtts'
    
    # Usa configuração apropriada
    config = configs.get(quality, configs['normal'])
    kwargs = config.get(actual_provider, config['gtts'])
    
    return text_to_speech(text, provider=provider, **kwargs)

def get_tts_info():
    """
    Retorna informações sobre os providers de TTS disponíveis
    
    Returns:
        dict: Informações sobre providers disponíveis
    """
    return {
        'openai': {
            'available': openai_client is not None,
            'cost': 'Pago (~$15/1M caracteres)',
            'quality': 'Excelente - Voz humana',
            'speed': 'Rápido (1-2s)',
            'voices': ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
            'languages': 'Todos os idiomas'
        },
        'gtts': {
            'available': True,
            'cost': 'Gratuito',
            'quality': 'Boa - Voz sintética',
            'speed': 'Médio (2-4s)',
            'voices': ['Padrão'],
            'languages': '100+ idiomas'
        }
    }

