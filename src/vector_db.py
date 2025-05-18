import faiss
import numpy as np
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader

class VectorDb:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.dimension = 1536  # Dimensão padrão do OpenAI embeddings
        self.index = faiss.IndexFlatL2(self.dimension)
        self.documents = []

    async def add_pdf(self, pdf_path):
        loader = PyPDFLoader(pdf_path)
        pages = []
        async for page in loader.alazy_load():
            pages.append(page)
        texts = [page.page_content for page in pages]
        vectors = self.embeddings.embed_documents(texts)
        vectors_np = np.array(vectors).astype('float32')
        self.index.add(vectors_np)
        self.documents.extend(pages)
        print(f"Documento PDF adicionado: {pdf_path}")