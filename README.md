# AI-Orchestration Customer Service System

Sistem Customer Service AI berbasis RAG yang tangguh dengan AI Gateway (LiteLLM), Vector DB (ChromaDB), Memory (PostgreSQL), dan Observability (Langfuse).

## Architecture
- **FastAPI**: Backend service.
- **LiteLLM**: Gateway untuk fallback otomatis Gemini -> OpenAI.
- **ChromaDB**: Database vektor untuk RAG.
- **PostgreSQL**: Penyimpanan memori percakapan.
- **Langfuse**: Tracing dan monitoring biaya.

## Cara Menjalankan

1.  **Siapkan API Keys**:
    Salin `.env.example` menjadi `.env` dan isi API Key Anda.
    ```bash
    cp .env.example .env
    ```

2.  **Jalankan Infrastruktur**:
    ```bash
    docker-compose up -d --build
    ```

3.  **Ingest Data**:
    Masukkan data ke database vektor.
    ```bash
    docker exec -it cs-ai-app python ingest.py
    ```

4.  **Tes API**:
    Gunakan `curl` atau tools seperti Postman untuk mengetes endpoint `/chat`.
    ```bash
    curl -X POST http://localhost:8080/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "Berapa harga paket dasar?", "session_id": "user-123"}'
    ```

5.  **Monitoring**:
    Akses Langfuse di [http://localhost:3000](http://localhost:3000).
