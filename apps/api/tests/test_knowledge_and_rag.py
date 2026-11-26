"""Tests for Phase 5 Knowledge Base, Document Parsing, Vector Store, and RAG."""

import io
from pathlib import Path
import zipfile

from fastapi.testclient import TestClient

from app.api.v1.knowledge import get_embedding_provider
from app.api.v1.llm import get_llm_provider
from app.core.config import Settings, get_settings
from app.main import create_app
from app.providers.embeddings import EmbeddingDimensionError, EmbeddingProvider
from app.providers.storage import JSONStorageProvider
from app.providers.vector_store import LocalVectorStoreProvider
from app.schemas.knowledge import DocumentChunk
from app.services.document_chunker import DocumentChunkingService
from app.services.document_parser import DocumentParseError, DocumentParserService
from tests.test_conversations import FakeChatProvider


class DeterministicMockEmbedder(EmbeddingProvider):
    """Keyword-bag deterministic 4-dim embedder for offline unit & API tests."""

    provider_id = "mock-embedder"

    def model_id(self) -> str:
        return "mock-multilingual-e5-small"

    def dimension(self) -> int:
        return 4

    async def health_check(self) -> dict[str, object]:
        return {"provider": self.provider_id, "available": True, "model_id": self.model_id()}

    @staticmethod
    def _vec(text: str) -> list[float]:
        low = text.lower()
        return [
            1.0 if any(k in low for k in ("price", "pricing", "cost", "कीमत", "2499", "₹")) else 0.05,
            1.0 if any(k in low for k in ("refund", "policy", "return", "वापसी")) else 0.05,
            1.0 if any(k in low for k in ("support", "hours", "timing", "मदद")) else 0.05,
            0.1,
        ]

    async def embed_texts(self, texts: list[str], *, batch_size: int = 16) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    async def embed_query(self, query: str) -> list[float]:
        return self._vec(query)


def _make_docx_bytes(text: str) -> bytes:
    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", doc_xml)
    return buf.getvalue()


def _make_client(tmp_path: Path, llm: FakeChatProvider | None = None) -> TestClient:
    app = create_app()
    test_settings = Settings(app_env="test", data_dir=str(tmp_path))
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_llm_provider] = lambda: (llm or FakeChatProvider())
    app.dependency_overrides[get_embedding_provider] = lambda: DeterministicMockEmbedder()
    return TestClient(app)


def test_document_parsers_and_validation() -> None:
    # TXT
    txt_sections = DocumentParserService.parse("notes.txt", b"Hello pricing is 2499.")
    assert "2499" in txt_sections[0].text

    # Markdown with headings
    md_sections = DocumentParserService.parse("faq.md", b"# Pricing\nPrice is Rs 2499.")
    assert md_sections[0].section_title == "Pricing"

    # CSV
    csv_sections = DocumentParserService.parse("plans.csv", b"Plan,Price\nPro,2499\n")
    assert "Plan: Pro | Price: 2499" in csv_sections[0].text

    # HTML
    html_sections = DocumentParserService.parse(
        "page.html",
        b"<html><script>alert(1)</script><body><p>Support hours 9am-6pm</p></body></html>",
    )
    assert "Support hours" in html_sections[0].text
    assert "alert" not in html_sections[0].text

    # JSON
    json_sections = DocumentParserService.parse("data.json", b'{"price": 2499}')
    assert "2499" in json_sections[0].text

    # DOCX
    docx_sections = DocumentParserService.parse("brochure.docx", _make_docx_bytes("DOCX Price 2499"))
    assert "DOCX Price 2499" in docx_sections[0].text

    # Empty / unsupported / corrupted
    for bad_name, bad_bytes in [
        ("empty.txt", b""),
        ("script.exe", b"MZ"),
        ("broken.docx", b"not-a-zip"),
        ("broken.json", b"{invalid"),
    ]:
        try:
            DocumentParserService.parse(bad_name, bad_bytes)
            assert False, f"Expected DocumentParseError for {bad_name}"
        except DocumentParseError:
            pass


def test_chunking_preserves_metadata_and_overlap() -> None:
    sections = DocumentParserService.parse("guide.md", ("# Pricing\n" + "word " * 120).encode())
    chunks = DocumentChunkingService.chunk_sections(
        sections,
        document_id="doc_1",
        knowledge_base_id="kb_1",
        agent_ids=["agent_1"],
        source_filename="guide.md",
        chunk_size_tokens=50,
        chunk_overlap_tokens=10,
    )
    assert len(chunks) >= 2
    assert chunks[0].section_title == "Pricing"
    assert chunks[0].source_filename == "guide.md"
    assert chunks[1].chunk_index == 1


async def test_vector_store_isolation_persistence_and_dim_check(tmp_path: Path) -> None:
    storage = JSONStorageProvider(tmp_path)
    storage.ensure_initialized()
    store = LocalVectorStoreProvider(storage)

    c1 = DocumentChunk(
        chunk_id="chk_1",
        document_id="doc_1",
        knowledge_base_id="kb_1",
        agent_ids=["agent_a"],
        content="Product price is 2499",
        chunk_index=0,
        source_filename="pricing.txt",
    )
    await store.add_vectors(
        knowledge_base_id="kb_1",
        embedding_model="model-v1",
        chunks=[c1],
        vectors=[[1.0, 0.0, 0.0, 0.0]],
    )

    # Agent A sees it; Agent B is isolated
    hits_a = await store.search(
        knowledge_base_id="kb_1",
        query_vector=[1.0, 0.0, 0.0, 0.0],
        embedding_model="model-v1",
        agent_id="agent_a",
        similarity_threshold=0.5,
    )
    assert len(hits_a) == 1
    hits_b = await store.search(
        knowledge_base_id="kb_1",
        query_vector=[1.0, 0.0, 0.0, 0.0],
        embedding_model="model-v1",
        agent_id="agent_b",
        similarity_threshold=0.5,
    )
    assert len(hits_b) == 0

    # Dimension/model mismatch raises EmbeddingDimensionError
    try:
        await store.search(
            knowledge_base_id="kb_1",
            query_vector=[1.0, 0.0, 0.0, 0.0],
            embedding_model="different-model",
        )
        assert False, "Expected EmbeddingDimensionError"
    except EmbeddingDimensionError:
        pass

    # Delete removes vectors
    assert await store.delete_by_document(knowledge_base_id="kb_1", document_id="doc_1") == 1
    assert await store.count(knowledge_base_id="kb_1") == 0


def test_full_rag_pipeline_with_conversation_and_citations(tmp_path: Path) -> None:
    fake_llm = FakeChatProvider()
    client = _make_client(tmp_path, llm=fake_llm)

    # 1. Create Knowledge Base & upload pricing doc
    kb = client.post(
        "/api/v1/knowledge-bases",
        json={"name": "Company Pricing", "description": "Verified prices"},
    ).json()["data"]
    kb_id = kb["id"]

    upload = client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        files=[("files", ("pricing.txt", b"Our Pro plan price is Rs 2,499 per month.", "text/plain"))],
    )
    assert upload.status_code == 201
    doc = upload.json()["data"][0]
    assert doc["status"] == "READY"
    assert doc["chunk_count"] >= 1

    # 2. Create Agent & assign KB
    agent = client.post(
        "/api/v1/agents",
        json={
            "name": "Asha RAG",
            "type": "SALES",
            "instructions": {"system_prompt": "Answer using verified KB."},
            "model": {"provider": "ollama", "model_id": "qwen2.5:3b"},
            "knowledge_base": {"enabled": True, "knowledge_base_id": kb_id},
        },
    ).json()["data"]
    assign = client.post(f"/api/v1/agents/{agent['id']}/knowledge-bases/{kb_id}")
    assert assign.status_code == 200

    # 3. Test Retrieval Endpoint (Hindi query retrieving English pricing doc via mock embedder)
    search_resp = client.post(
        f"/api/v1/agents/{agent['id']}/test-retrieval",
        json={"query": "आपके product की कीमत कितनी है?", "top_k": 3, "similarity_threshold": 0.2},
    )
    assert search_resp.status_code == 200
    assert search_resp.json()["data"]["grounded"] is True
    assert search_resp.json()["data"]["hits"][0]["filename"] == "pricing.txt"

    # 4. Conversation turn injects retrieved context & attaches verified citations
    conv = client.post(
        f"/api/v1/agents/{agent['id']}/conversations",
        json={"title": "RAG Chat"},
    ).json()["data"]
    msg_resp = client.post(
        f"/api/v1/conversations/{conv['id']}/messages",
        json={"content": "What is the price of the Pro plan?"},
    )
    assert msg_resp.status_code == 200
    reply = msg_resp.json()["data"]["reply"]
    assert reply["grounded"] is True
    assert reply["sources"][0]["filename"] == "pricing.txt"
    assert "2,499" in fake_llm.last_messages[0]["content"]

    # 5. Delete document removes vectors
    del_doc = client.delete(f"/api/v1/documents/{doc['id']}")
    assert del_doc.status_code == 200
    kb_after = client.get(f"/api/v1/knowledge-bases/{kb_id}").json()["data"]
    assert kb_after["chunk_count"] == 0
