import os
import asyncio
from typing import AsyncGenerator
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from langchain_openai import ChatOpenAI # LiteLLM biasanya kompatibel dengan ChatOpenAI wrapper
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_chroma import Chroma
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_community.llms.fake import FakeListLLM
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

app = FastAPI(title="Customer Service AI")

# --- Configuration ---
LITEL_LM_URL = os.getenv("LITEL_LM_URL", "http://litellm-proxy:4000")
# Pastikan DATABASE_URL diarahkan ke localhost jika menjalankan script di luar Docker
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/cs_ai_db")


# --- LLM and RAG Setup ---
# Flag untuk menggunakan Dummy LLM agar hemat token saat debugging History
USE_DUMMY_LLM = os.getenv("USE_DUMMY_LLM", "true").lower() == "false"

if USE_DUMMY_LLM:
    print("🛠️  DEBUG MODE: Menggunakan Dummy LLM (FakeListLLM)")
    llm = FakeListLLM(responses=["Halo! Ini adalah respon dummy untuk mengetes History.", "Saya ingat percakapan kita sebelumnya."])
else:
    # Menggunakan ChatOpenAI dengan base_url LiteLLM seringkali lebih stabil untuk streaming
    llm = ChatOpenAI(
        model="cs-ai-model", 
        openai_api_base=f"{LITEL_LM_URL}/v1", # LiteLLM butuh suffix /v1 biasanya
        openai_api_key="sk-1234", # LiteLLM butuh key placeholder jika tidak pakai auth
        streaming=True
    )


# Inisialisasi Embeddings (FastEmbed - Local & Lightweight)
embeddings = FastEmbedEmbeddings()

# FIX: Inisialisasi Chroma Lokal
# Kita tidak pakai CHROMA_URL karena kita simpan di folder "./chroma_db"
vectorstore = Chroma(
    persist_directory="./chroma_db", # Lokasi folder database lokal kamu
    embedding_function=embeddings,
    collection_name="products"
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# --- Prompt & Chain ---
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful customer service assistant for AI-Orchestrator. Use the following context to answer questions: {context}"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}"),
])


# --- Memory Helper ---
def get_session_history(session_id: str):
    async_db_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    # Membuat engine async untuk menghilangkan DeprecationWarning
    engine = create_async_engine(async_db_url)
    
    return SQLChatMessageHistory(
        session_id=session_id, 
        connection=engine,
        async_mode=True
    )

# --- Chain Setup ---
# Kita buat chain dasar terlebih dahulu
chain = prompt | llm

# Bungkus dengan history
runnable_with_history = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="question",
    history_messages_key="history",
)

# --- API Logic ---
async def get_chain_response(question: str, session_id: str):
    try:
        # 1. Retrieve context secara manual
        context_docs = await retriever.ainvoke(question)
        context_text = "\n".join([doc.page_content for doc in context_docs])
        
        # 2. Stream response
        async for chunk in runnable_with_history.astream(
            {"question": question, "context": context_text},
            config={"configurable": {"session_id": session_id}}
        ):
            # Resiliensi: Handle jika chunk adalah string (Dummy LLM) atau Message (Real LLM)
            if isinstance(chunk, str):
                yield chunk
            elif hasattr(chunk, "content"):
                yield chunk.content
    except Exception as e:
        print(f"❌ Error in get_chain_response: {str(e)}")
        yield f"Error: {str(e)}"

# --- API Endpoints ---
class ChatRequest(BaseModel):
    message: str
    session_id: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    return StreamingResponse(get_chain_response(request.message, request.session_id), media_type="text/event-stream")

@app.get("/health")
def health_check():
    return {"status": "ok", "mode": "local_chroma"}