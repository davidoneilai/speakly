import whisper
from openai import OpenAI
from pyhocon import ConfigFactory
import os, getpass, hashlib
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
# --- Nova Lógica Baseada em Grafo ---
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from src.retriever import Retriever
from src.vector_db import VectorDb

# Carregar variáveis de ambiente
load_dotenv()

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

# Sistema de memória global para manter histórico de conversas
_global_memory = MemorySaver()
_global_graph = None
_current_thread_id = "default_session"

user_level = "begginer"  # ou "iniciante", "avançado"

def generate_thread_id(user_id="default_user", session_info=""):
    """
    Gera um thread_id único baseado no usuário e informações da sessão
    """
    unique_string = f"{user_id}_{session_info}"
    return hashlib.md5(unique_string.encode()).hexdigest()[:16]

def get_or_create_global_graph(user_level="begginer"):
    """
    Retorna o grafo global compartilhado, criando apenas se necessário
    """
    global _global_graph
    if _global_graph is None:
        _global_graph = create_graph(user_level)
    return _global_graph

def reset_conversation_memory():
    """
    Reseta a memória da conversa para começar uma nova sessão
    """
    global _global_memory, _current_thread_id
    _global_memory = MemorySaver()
    _current_thread_id = generate_thread_id()

def make_generate(user_level):
    def generate_with_level(state: MessagesState):
        return generate(state, user_level)
    return generate_with_level

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
        
        # Preparar parâmetros para a transcrição
        transcript_params = {
            "model": STT_OPENAI_MODEL,
            "file": None,  # será definido abaixo
            "temperature": STT_TEMPERATURE,
            "prompt": STT_PROMPT
        }
        
        # Adicionar language apenas se não for null
        if STT_LANGUAGE and STT_LANGUAGE.lower() != 'null':
            transcript_params["language"] = STT_LANGUAGE
        
        with open(audio_filename, "rb") as audio_file:
            transcript_params["file"] = audio_file
            transcript = client.audio.transcriptions.create(**transcript_params)
        
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
def generate(state: MessagesState, user_level="begginer"):
    """Gera a resposta final considerando o nível do usuário."""
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

    # Instrução de nível com ênfase em chinês simplificado (instruções em inglês)
    level_instruction = {
        "begginer": "You MUST respond ONLY in Simplified Chinese (简体中文). Use only HSK1 level vocabulary and grammar. Ensure all characters are in Simplified Chinese, never use Traditional Chinese characters.",
        "intermediate": "You MUST respond ONLY in Simplified Chinese (简体中文). Use HSK1 and HSK2 level vocabulary and grammar. Ensure all characters are in Simplified Chinese, never use Traditional Chinese characters.",
        "advanced": "You MUST respond ONLY in Simplified Chinese (简体中文). You can use A1 to C2 level vocabulary and grammar. Ensure all characters are in Simplified Chinese, never use Traditional Chinese characters."
    }.get(user_level, "You MUST respond ONLY in Simplified Chinese (简体中文). Ensure all characters are in Simplified Chinese, never use Traditional Chinese characters.")

    # Prompt do sistema otimizado para conversa contínua (instruções em inglês)
    system_message_content = (
        "You are a Chinese language learning assistant specialized in helping learners practice conversation. "
        "CRITICAL: You MUST always respond ONLY in Simplified Chinese (简体中文). Never use English or any other language in your responses. "
        "You are knowledgeable about all topics and can discuss anything the user wants to talk about freely. "
        "Use the following retrieved context to help answer, but feel free to expand beyond it with your general knowledge. "
        "Keep responses engaging, educational, and conversational. Use 1-3 sentences maximum. "
        "IMPORTANT: Always respond in a way that continues the conversation naturally. "
        "Ask follow-up questions or make statements that invite more conversation. "
        "Never end with polite closings like '如果你需要帮助，请告诉我' or '有什么问题吗？' "
        "Instead, respond naturally and keep the conversation flowing. "
        "Strictly follow the user's language level requirements:\n"
        f"{level_instruction}\n\n"
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
    
    return {"messages": [response]}

# Construção do grafo de estados
def create_graph(user_level="begginer"):
    """Cria um grafo de estados com nível específico"""
    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node(query_or_respond)
    graph_builder.add_node(tools_node)
    graph_builder.add_node("generate", make_generate(user_level))
    graph_builder.set_entry_point("query_or_respond")
    graph_builder.add_conditional_edges(
        "query_or_respond",
        tools_condition,
        {END: END, "tools": "tools"},
    )
    graph_builder.add_edge("tools", "generate")
    graph_builder.add_edge("generate", END)

    # Usar memória global compartilhada
    return graph_builder.compile(checkpointer=_global_memory)

# Nova função send_to_llm utilizando o grafo
def send_to_llm(text, user_level="begginer"):
    """
    Prepara o estado inicial com o áudio transcrito (text),
    executa o grafo e retorna a resposta gerada.
    Mantém o histórico da conversa usando thread_id persistente.
    """
    global _current_thread_id
    
    # Usa o grafo global compartilhado
    graph = get_or_create_global_graph(user_level)
    
    # Adiciona apenas a nova mensagem humana
    initial_messages = [HumanMessage(text)]
    print(f"[LOG] Nível do usuário recebido em send_to_llm: {user_level}")
    print(f"[LOG] Thread ID em uso: {_current_thread_id}")

    state = MessagesState({"messages": initial_messages})
    
    # Usa o thread_id persistente para manter histórico
    final_state = graph.invoke(state, config={"thread_id": _current_thread_id})
    response_message = final_state["messages"][-1]
    return response_message.content

# A função process_audio_with_llm continua utilizando a transcrição como query para o grafo
def process_audio_with_llm(audio_filename, user_level):
    transcript = transcribe_audio(audio_filename)
    llm_response = send_to_llm(transcript, user_level)
    print(f"[LOG] Nível do usuário recebido em process_audio_with_llm: {user_level}")  # LOG

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

# Funções utilitárias para gerenciar sessões e memória
def start_new_conversation_session():
    """
    Inicia uma nova sessão de conversa, resetando a memória
    """
    global _current_thread_id, _global_memory
    _current_thread_id = generate_thread_id()
    print(f"[LOG] Nova sessão iniciada com Thread ID: {_current_thread_id}")
    return _current_thread_id

def get_conversation_history():
    """
    Retorna o histórico da conversa atual (para debug/monitoramento)
    """
    try:
        global _current_thread_id, _global_memory
        # Retorna informações básicas sobre a sessão
        return {
            "thread_id": _current_thread_id,
            "status": "active",
            "memory_available": _global_memory is not None
        }
    except Exception as e:
        print(f"Erro ao recuperar histórico: {e}")
        return {
            "thread_id": "unknown",
            "status": "error", 
            "memory_available": False
        }

def clear_conversation_memory():
    """
    Limpa completamente a memória da conversa
    """
    reset_conversation_memory()
    print("[LOG] Memória da conversa foi limpa completamente")

# Inicializar thread_id na primeira execução
if _current_thread_id == "default_session":
    _current_thread_id = generate_thread_id()

