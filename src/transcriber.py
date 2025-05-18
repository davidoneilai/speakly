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
    model = whisper.load_model("base")
    result = model.transcribe(audio_filename)
    return result["text"]

# Passo 1: Gerar uma mensagem (possivelmente com chamada de ferramenta)
def query_or_respond(state: MessagesState):
    """Gera uma chamada de ferramenta para recuperação ou uma resposta."""
    llm_with_tools = llm.bind_tools([retrieve])
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# Passo 2: Executar a recuperação (nó de ferramenta)
tools_node = ToolNode([retrieve])

# Passo 3: Gerar a resposta utilizando o conteúdo recuperado
def generate(state: MessagesState):
    """Gera a resposta final."""
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
    system_message_content = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer "
        "the question. If you don't know the answer, say that you don't know. "
        "Use three sentences maximum and keep the answer concise."
        "\n\n" +
        docs_content
    )
    conversation_messages = [
        message
        for message in state["messages"]
        if message.type in ("human", "system") or (message.type == "ai" and not message.tool_calls)
    ]
    prompt = [SystemMessage(system_message_content)] + conversation_messages
    response = llm.invoke(prompt)
    return {"messages": [response]}

# Construção do grafo de estados
graph_builder = StateGraph(MessagesState)
graph_builder.add_node(query_or_respond)
graph_builder.add_node(tools_node)
graph_builder.add_node(generate)
graph_builder.set_entry_point("query_or_respond")
graph_builder.add_conditional_edges(
    "query_or_respond",
    tools_condition,
    {END: END, "tools": "tools"},
)
graph_builder.add_edge("tools", "generate")
graph_builder.add_edge("generate", END)

memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory)

# Nova função send_to_llm utilizando o grafo
def send_to_llm(text):
    """
    Prepara o estado inicial com o áudio transcrito (text),
    executa o grafo e retorna a resposta gerada.
    """
    initial_messages = []
    # Adiciona a query como mensagem humana
    initial_messages.append(HumanMessage(text))
    
    state = MessagesState({"messages": initial_messages})
    # Adicione um thread_id único (pode ser um valor fixo ou dinâmico)
    final_state = graph.invoke(state, config={"thread_id": "default"})
    response_message = final_state["messages"][-1]
    return response_message.content

# A função process_audio_with_llm continua utilizando a transcrição como query para o grafo
def process_audio_with_llm(audio_filename):
    transcript = transcribe_audio(audio_filename)
    return send_to_llm(transcript)
