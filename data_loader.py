from openai import OpenAI
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from dotenv import load_dotenv
load_dotenv()
from sentence_transformers import SentenceTransformer
EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
EMBED_DIM = 384



splitter=SentenceSplitter(chunk_size=1000,chunk_overlap=200)


def load_and_chunk_pdf(file_path: str):
    pdf_reader=PDFReader()
    docs=pdf_reader.load_data(file=file_path)
    texts = [d.text for d in docs if  getattr(d, "text",None)]
    chunks=[]
    for t in texts:
        chunks.extend(splitter.split_text(t))

    return chunks

def embed_texts(texts: list[str]) -> list[list[float]]:
    embeddings = EMBED_MODEL.encode(texts)
    return embeddings.tolist()



