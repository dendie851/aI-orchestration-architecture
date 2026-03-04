import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv()

def ingest_data():
    # 1. Load data
    if not os.path.exists("knowledge.txt"):
        with open("knowledge.txt", "w") as f:
            f.write("Harga paket dasar adalah Rp 1.000.000 per bulan.\n")
            f.write("Dukungan teknis tersedia 24/7 melalui email support@example.com.\n")
    
    loader = TextLoader("knowledge.txt")
    documents = loader.load()
    
    # 2. Split text
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    docs = text_splitter.split_documents(documents)
    
    # 3. Embedding (FastEmbed - Local & Lightweight)
    print("Memuat model embedding (FastEmbed)...")
    from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
    embeddings = FastEmbedEmbeddings()
    
    # 4. Sync Index: Hapus data lama agar sinkron dengan file terbaru
    print(f"🔄 Mensinkronisasi database dengan {len(docs)} potongan teks...")
    
    vectorstore = Chroma(
        persist_directory="./chroma_db",
        embedding_function=embeddings,
        collection_name="products"
    )
    
    # Hapus semua data di collection sebelum memasukkan yang baru
    try:
        all_ids = vectorstore.get()["ids"]
        if all_ids:
            vectorstore.delete(ids=all_ids)
            print(f"🗑️ Menghapus {len(all_ids)} data lama dari index.")
    except Exception as e:
        print(f"⚠️ Warning saat membersihkan index: {str(e)}")

    vectorstore.add_documents(documents=docs)
    print("✅ Sinkronisasi Selesai secara LOKAL!")

if __name__ == "__main__":
    ingest_data()