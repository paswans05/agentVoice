# agentVoice — Knowledge Base & Local RAG Guide (Phase 5)

## 1. Architecture & Pipeline

1. **Document Upload & Validation**: Sanitizes filenames, prevents path traversal, enforces configurable size limits (`max_file_size_mb`, default 10 MB), and validates extensions (`.pdf`, `.docx`, `.txt`, `.md`, `.csv`, `.html`, `.htm`, `.json`).
2. **Extraction & Chunking**: Extracts clean text sections (`DocumentParserService`) and splits them into overlapping chunks (`DocumentChunkingService`, default 800 tokens / 120 overlap) while preserving `page_number`, `section_title`, and `source_filename`.
3. **Local Embeddings**: `SentenceTransformerEmbeddingProvider` uses `intfloat/multilingual-e5-small` (384-dim, supports Hindi, English, and Hinglish; downloaded locally on first use and cached in `agentvoice-data/models/embeddings/`).
4. **Local Vector Index**: `LocalVectorStoreProvider` persists vectors and chunk metadata in `agentvoice-data/knowledge/vectors/{kb_id}.json`, enforces `knowledge_base_id` and `agent_id` isolation, and checks embedding model/dimension compatibility.
5. **Conversation & Voice Integration**: `ConversationService` calls `RAGService` before LLM generation, injects verified excerpts + prompt-injection grounding rules into `PromptBuilder`, and attaches `SourceCitation` metadata to saved assistant messages (spoken voice replies never read filenames aloud).

## 2. Installing Optional RAG Dependencies

```powershell
cd apps/api
uv sync --extra speech --extra rag
```

This installs `pypdf` (for PDF extraction) and `sentence-transformers` (for local multilingual embeddings). DOCX, TXT, Markdown, CSV, HTML, and JSON extraction work with zero extra dependencies.

## 3. API Endpoints

- `GET/POST /api/v1/knowledge-bases`
- `GET/PUT/DELETE /api/v1/knowledge-bases/{knowledge_base_id}`
- `POST /api/v1/knowledge-bases/{knowledge_base_id}/enable` & `.../disable`
- `GET/POST /api/v1/knowledge-bases/{knowledge_base_id}/documents`
- `GET/DELETE /api/v1/documents/{document_id}`, `.../status`, `.../reprocess`
- `GET/POST/DELETE /api/v1/agents/{agent_id}/knowledge-bases/{knowledge_base_id}`
- `POST /api/v1/knowledge-bases/{knowledge_base_id}/search`
- `POST /api/v1/agents/{agent_id}/test-retrieval`
- `GET/PUT /api/v1/rag/settings`
