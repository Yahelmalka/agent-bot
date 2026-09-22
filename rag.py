import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()
embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))

vectorstore = Chroma(
    collection_name="project_knowledge",
    embedding_function=embeddings,
    persist_directory="./chroma_db"
)

def ingest_documents():
    with open("knowledge/docs.txt", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        print("שגיאה: לא נמצא תוכן בקובץ knowledge/docs.txt")
        return

    vectorstore.add_texts(lines)
    print(f"הוזנו {len(lines)} מסמכים למאגר")

def search_knowledge(query, n_results=2):
    docs = vectorstore.similarity_search(query, k=n_results)
    return [doc.page_content for doc in docs]

if __name__ == "__main__":
    ingest_documents()