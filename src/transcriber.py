import whisper
from openai import OpenAI
from pyhocon import ConfigFactory
import os, getpass
from langchain.chat_models import init_chat_model
# --- Nova Lógica Baseada em Grafo ---
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from src.retriever import Retriever
from src.vector_db import VectorDb

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# if not os.environ.get("OPENAI_API_KEY"):
#     os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")

# Configurações iniciais
config = ConfigFactory.parse_file("speakly.conf")
llm_model = config.get('openai.llm')

# Configurações de STT (Speech-to-Text)
STT_PROVIDER = config.get('stt.provider', 'openai')
STT_OPENAI_MODEL = config.get('stt.openai.model', 'whisper-1')
STT_LANGUAGE = config.get('stt.openai.language', 'en')
STT_TEMPERATURE = config.get('stt.openai.temperature', 0.0)
STT_PROMPT = config.get('stt.openai.prompt', 'This is an English conversation for language learning.')

# Configurações do Whisper local (fallback)
WHISPER_MODEL = config.get('whisper.model', 'base')
WHISPER_LANGUAGE = config.get('whisper.language', 'en')  # Inglês
WHISPER_FP16 = config.get('whisper.fp16', False)
WHISPER_VERBOSE = config.get('whisper.verbose', False)

# Configurações para respostas em chinês (apenas para TTS)
CHINESE_RESPONSE_CONFIG = {
    'temperature': 0.3,
    'max_tokens': 500,
}

# Cache do modelo Whisper para evitar recarregar
_whisper_model_cache = None

user_level = "begginer"  # ou "iniciante", "avançado"

def make_generate(user_level, theme="conversacao-geral"):
    def generate_with_level_and_theme(state: MessagesState):
        return generate(state, user_level, theme)
    return generate_with_level_and_theme

def get_whisper_model():
    """Carrega o modelo Whisper uma única vez e mantém em cache"""
    global _whisper_model_cache
    if _whisper_model_cache is None:
        print(f"Carregando modelo Whisper: {WHISPER_MODEL} (primeira vez)")
        _whisper_model_cache = whisper.load_model(WHISPER_MODEL)
    return _whisper_model_cache

llm = init_chat_model(llm_model, model_provider="openai")

# Instancie sua base vetorial (vector_db) conforme sua implementação.
# Exemplo: de uma classe VectorDB ou similar.
db = VectorDb()
# Cria a instância do vector_db com os parâmetros necessários
vector_db = db.add_pdf("book.pdf")

# Instancia o Retriever e extrai o método retrieve para ser usado como ferramenta
retriever_instance = Retriever(vector_db)
retrieve = retriever_instance.retrieve

def transcribe_audio(audio_filename):
    """
    Transcreve áudio usando OpenAI STT API ou Whisper local como fallback
    """
    print(f"Transcrevendo arquivo: {audio_filename}")
    
    if STT_PROVIDER == 'openai':
        return transcribe_with_openai(audio_filename)
    else:
        return transcribe_with_whisper_local(audio_filename)

def transcribe_with_openai(audio_filename):
    """
    Transcreve áudio usando a API da OpenAI (Whisper-1)
    """
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        with open(audio_filename, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=STT_OPENAI_MODEL,
                file=audio_file,
                language=STT_LANGUAGE,
                temperature=STT_TEMPERATURE,
                prompt=STT_PROMPT
            )
        
        result_text = transcript.text.strip()
        print(f"Transcrição OpenAI concluída: {result_text}")
        return result_text
        
    except Exception as e:
        print(f"Erro na transcrição OpenAI: {e}")
        print("Fallback para Whisper local...")
        return transcribe_with_whisper_local(audio_filename)

def transcribe_with_whisper_local(audio_filename):
    """
    Transcreve áudio usando Whisper local (fallback)
    """
    print("Usando Whisper local...")
    
    # Usa modelo em cache (muito mais rápido)
    model = get_whisper_model()
    
    # Configurações otimizadas para inglês
    transcribe_options = {
        "fp16": WHISPER_FP16,
        "verbose": WHISPER_VERBOSE,
        "temperature": 0.0,
    }
    
    # Adicionar idioma se especificado
    if WHISPER_LANGUAGE != "auto":
        transcribe_options["language"] = WHISPER_LANGUAGE
    
    print(f"Iniciando transcrição local com modelo {WHISPER_MODEL}...")
    result = model.transcribe(audio_filename, **transcribe_options)
    
    transcript = result["text"].strip()
    print(f"Transcrição local concluída: {transcript}")
    
    return transcript

# Passo 1: Gerar uma mensagem (possivelmente com chamada de ferramenta)
def query_or_respond(state: MessagesState):
    """Gera uma chamada de ferramenta para recuperação ou uma resposta."""
    llm_with_tools = llm.bind_tools([retrieve])
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# Passo 2: Executar a recuperação (nó de ferramenta)
tools_node = ToolNode([retrieve])

# Passo 3: Gerar a resposta utilizando o conteúdo recuperado
def generate(state: MessagesState, user_level="begginer", theme="conversacao-geral"):
    """Gera a resposta final considerando o nível do usuário e o tema."""
    # Obtém as mensagens geradas pela ferramenta, se houver
    recent_tool_messages = []
    for message in reversed(state["messages"]):
        if message.type == "tool":
            recent_tool_messages.append(message)
        else:
            break
    tool_messages = recent_tool_messages[::-1]
    
    # Formata o prompt com o conteúdo dos documentos recuperados
    docs_content = "\n\n".join(doc.content for doc in tool_messages)
    print(f"[LOG] Nível do usuário recebido em generate: {user_level}")  # LOG
    print(f"[LOG] Tema recebido em generate: {theme}")  # LOG

    # Instrução de nível com ênfase em chinês simplificado (instruções em inglês)
    level_instruction = {
        "begginer": "You MUST respond ONLY in Simplified Chinese (简体中文). Use only HSK1 level vocabulary and grammar. Ensure all characters are in Simplified Chinese, never use Traditional Chinese characters.",
        "intermediate": "You MUST respond ONLY in Simplified Chinese (简体中文). Use HSK1 and HSK2 level vocabulary and grammar. Ensure all characters are in Simplified Chinese, never use Traditional Chinese characters.",
        "advanced": "You MUST respond ONLY in Simplified Chinese (简体中文). You can use A1 to C2 level vocabulary and grammar. Ensure all characters are in Simplified Chinese, never use Traditional Chinese characters."
    }.get(user_level, "You MUST respond ONLY in Simplified Chinese (简体中文). Ensure all characters are in Simplified Chinese, never use Traditional Chinese characters.")

    # Instrução de tema em inglês
    theme_contexts = {
        "conversacao-geral": "Focus on general daily conversation topics like greetings, family, hobbies, and everyday activities.",
        "trabalho": "Focus on work-related topics like job responsibilities, meetings, office life, and professional communication.",
        "viagem": "Focus on travel-related topics like transportation, hotels, tourism, asking for directions, and cultural experiences.",
        "tecnologia": "Focus on technology-related topics like computers, smartphones, internet, social media, and digital tools."
    }
    
    # Se for um tema customizado, use ele diretamente
    if theme in theme_contexts:
        theme_instruction = theme_contexts[theme]
    else:
        theme_instruction = f"Focus the conversation on topics related to: {theme}"

    # Prompt do sistema otimizado para chinês simplificado (instruções em inglês)
    system_message_content = (
        "You are a Chinese language learning assistant specialized in helping learners practice conversation. "
        "CRITICAL: You MUST always respond ONLY in Simplified Chinese (简体中文). Never use English or any other language in your responses. "
        "Use the following retrieved context to answer the question. If you don't know the answer, say that you don't know in Simplified Chinese. "
        "Use maximum three sentences and keep the answer concise. "
        "Strictly follow the user's language level requirements:\n"
        f"{level_instruction}\n\n"
        f"Theme Context: {theme_instruction}\n\n"
        f"Reference Content:\n{docs_content}"
    )
    conversation_messages = [
        message
        for message in state["messages"]
        if message.type in ("human", "system") or (message.type == "ai" and not message.tool_calls)
    ]
    prompt = [SystemMessage(system_message_content)] + conversation_messages
    
    # Usar configurações específicas para chinês
    llm_params = {
        "temperature": CHINESE_RESPONSE_CONFIG.get('temperature', 0.3),
        "max_tokens": CHINESE_RESPONSE_CONFIG.get('max_tokens', 500)
    }
    
    response = llm.invoke(prompt, **llm_params)
    
    # Validar e garantir chinês simplificado na resposta
    if hasattr(response, 'content'):
        response.content = validate_chinese_response(response.content)
    
    return {"messages": [response]}

# Construção do grafo de estados
def create_graph(user_level="begginer", theme="conversacao-geral"):
    """Cria um grafo de estados com nível e tema específicos"""
    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node(query_or_respond)
    graph_builder.add_node(tools_node)
    graph_builder.add_node("generate", make_generate(user_level, theme))
    graph_builder.set_entry_point("query_or_respond")
    graph_builder.add_conditional_edges(
        "query_or_respond",
        tools_condition,
        {END: END, "tools": "tools"},
    )
    graph_builder.add_edge("tools", "generate")
    graph_builder.add_edge("generate", END)

    memory = MemorySaver()
    return graph_builder.compile(checkpointer=memory)

# Nova função send_to_llm utilizando o grafo
def send_to_llm(text, user_level="begginer", theme="conversacao-geral"):
    """
    Prepara o estado inicial com o áudio transcrito (text),
    executa o grafo e retorna a resposta gerada.
    """
    # Cria um grafo específico para este request
    graph = create_graph(user_level, theme)
    
    initial_messages = []
    # Adiciona a query como mensagem humana
    initial_messages.append(HumanMessage(text))
    print(f"[LOG] Nível do usuário recebido em send_to_llm: {user_level}")  # LOG
    print(f"[LOG] Tema recebido em send_to_llm: {theme}")  # LOG

    state = MessagesState({"messages": initial_messages})
    # Adicione um thread_id único (pode ser um valor fixo ou dinâmico)
    final_state = graph.invoke(state, config={"thread_id": "default"})
    response_message = final_state["messages"][-1]
    return response_message.content

# A função process_audio_with_llm continua utilizando a transcrição como query para o grafo
def process_audio_with_llm(audio_filename, user_level, theme='conversacao-geral'):
    transcript = transcribe_audio(audio_filename)
    llm_response = send_to_llm(transcript, user_level, theme)
    print(f"[LOG] Nível do usuário recebido em process_audio_with_llm: {user_level}")  # LOG
    print(f"[LOG] Tema recebido em process_audio_with_llm: {theme}")  # LOG

    return {
        "transcription": transcript,
        "llm_response": llm_response
    }

# Função para traduzir texto usando OpenAI
def translate_text_with_llm(text):
    """Traduz texto do chinês para inglês usando OpenAI"""
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a professional translator. Translate the following Chinese text to English. Return only the English translation, no explanations or additional text."
                },
                {
                    "role": "user", 
                    "content": text
                }
            ],
            max_tokens=500,
            temperature=0.1
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Erro na tradução: {e}")
        return f"[Translation unavailable: {text}]"

# Funções auxiliares para chinês simplificado
def ensure_simplified_chinese(text):
    """
    Garante que o texto está em chinês simplificado.
    Esta função pode ser expandida com um mapeamento mais completo.
    """
    # Mapeamento básico de caracteres tradicionais para simplificados
    traditional_to_simplified = {
        '國': '国', '學': '学', '語': '语', '說': '说',
        '聽': '听', '讀': '读', '寫': '写', '時': '时',
        '間': '间', '會': '会', '個': '个', '們': '们',
        '來': '来', '過': '过', '後': '后', '進': '进',
        '這': '这', '那': '那', '裡': '里', '點': '点',
        '開': '开', '關': '关', '問': '问', '題': '题'
    }
    
    # Converter caracteres tradicionais para simplificados
    result = text
    for trad, simp in traditional_to_simplified.items():
        result = result.replace(trad, simp)
    
    return result

def validate_chinese_response(response):
    """
    Valida se a resposta está em chinês e força simplificado se necessário.
    """
    if not response:
        return response
    
    # Converter para simplificado
    simplified_response = ensure_simplified_chinese(response)
    
    # Log para debugging
    if simplified_response != response:
        print(f"[LOG] Convertido de tradicional para simplificado: {response} -> {simplified_response}")
    
    return simplified_response
