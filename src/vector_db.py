from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from src.retriever import Retriever

class VectorDb:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.vector_db = FAISS(embedding_function=self.embeddings)

    async def add_pdf(self, pdf_path):
        loader = PyPDFLoader(pdf_path)
        pages = []
        async for page in loader.alazy_load():
            pages.append(page)
        self.vector_db.add_document(pages)
        print(f"Documento PDF adicionado: {pdf_path}")
