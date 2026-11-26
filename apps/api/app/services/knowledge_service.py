"""KnowledgeBaseService and DocumentService orchestrating ingestion and indexing."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import time
import uuid

from app.providers.embeddings import EmbeddingProvider
from app.providers.vector_store import VectorStoreProvider
from app.repositories.knowledge_repository import DocumentRepository, KnowledgeBaseRepository
from app.schemas.knowledge import (
    DocumentStatus,
    KnowledgeBase,
    KnowledgeBaseCreate,
    KnowledgeBaseStatus,
    KnowledgeBaseUpdate,
    KnowledgeDocument,
    RAGSettings,
)
from app.services.document_chunker import DocumentChunkingService
from app.services.document_parser import DocumentParseError, DocumentParserService, ParsedSection

logger = logging.getLogger(__name__)


class KnowledgeBaseNotFoundError(LookupError):
    """Raised when a knowledge base ID does not exist."""


class DocumentNotFoundError(LookupError):
    """Raised when a document ID does not exist."""


class KnowledgeBaseService:
    """Manages knowledge bases and agent-to-KB assignments."""

    def __init__(
        self,
        kb_repo: KnowledgeBaseRepository,
        doc_repo: DocumentRepository,
        vector_store: VectorStoreProvider,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._kb_repo = kb_repo
        self._doc_repo = doc_repo
        self._vectors = vector_store
        self._embedder = embedding_provider

    async def list_knowledge_bases(self) -> list[KnowledgeBase]:
        return await self._kb_repo.list_all()

    async def get_knowledge_base(self, kb_id: str) -> KnowledgeBase:
        kb = await self._kb_repo.get_by_id(kb_id)
        if kb is None:
            raise KnowledgeBaseNotFoundError(f"Knowledge base '{kb_id}' was not found.")
        return kb

    async def create_knowledge_base(self, payload: KnowledgeBaseCreate) -> KnowledgeBase:
        now = datetime.now(timezone.utc)
        kb = KnowledgeBase(
            id=f"kb_{uuid.uuid4().hex[:12]}",
            name=payload.name.strip(),
            description=payload.description.strip(),
            agent_ids=list(dict.fromkeys(payload.agent_ids)),
            enabled=True,
            status=KnowledgeBaseStatus.EMPTY,
            embedding_model=self._embedder.model_id(),
            created_at=now,
            updated_at=now,
        )
        return await self._kb_repo.save(kb)

    async def update_knowledge_base(
        self, kb_id: str, payload: KnowledgeBaseUpdate
    ) -> KnowledgeBase:
        kb = await self.get_knowledge_base(kb_id)
        updated = kb.model_copy(
            update={
                "name": payload.name.strip(),
                "description": payload.description.strip(),
            }
        )
        return await self._kb_repo.save(updated)

    async def delete_knowledge_base(self, kb_id: str) -> None:
        await self.get_knowledge_base(kb_id)
        docs = await self._doc_repo.list_by_kb(kb_id)
        for doc in docs:
            await self._doc_repo.delete(doc.id)
        await self._vectors.delete_by_knowledge_base(knowledge_base_id=kb_id)
        await self._kb_repo.delete(kb_id)

    async def set_enabled(self, kb_id: str, enabled: bool) -> KnowledgeBase:
        kb = await self.get_knowledge_base(kb_id)
        if not enabled:
            next_status = KnowledgeBaseStatus.DISABLED
        else:
            next_status = (
                KnowledgeBaseStatus.READY if kb.chunk_count > 0 else KnowledgeBaseStatus.EMPTY
            )
        return await self._kb_repo.save(
            kb.model_copy(update={"enabled": enabled, "status": next_status})
        )

    async def assign_agent(self, kb_id: str, agent_id: str) -> KnowledgeBase:
        kb = await self.get_knowledge_base(kb_id)
        if agent_id not in kb.agent_ids:
            kb = await self._kb_repo.save(
                kb.model_copy(update={"agent_ids": [*kb.agent_ids, agent_id]})
            )
        return kb

    async def unassign_agent(self, kb_id: str, agent_id: str) -> KnowledgeBase:
        kb = await self.get_knowledge_base(kb_id)
        if agent_id in kb.agent_ids:
            kb = await self._kb_repo.save(
                kb.model_copy(
                    update={"agent_ids": [aid for aid in kb.agent_ids if aid != agent_id]}
                )
            )
        return kb

    async def refresh_stats(self, kb_id: str) -> KnowledgeBase:
        kb = await self.get_knowledge_base(kb_id)
        docs = await self._doc_repo.list_by_kb(kb_id)
        chunk_count = await self._vectors.count(knowledge_base_id=kb_id)

        if not kb.enabled:
            status = KnowledgeBaseStatus.DISABLED
        elif any(d.status in (DocumentStatus.PROCESSING, DocumentStatus.INDEXING) for d in docs):
            status = KnowledgeBaseStatus.INDEXING
        elif docs and all(d.status == DocumentStatus.FAILED for d in docs):
            status = KnowledgeBaseStatus.FAILED
        elif chunk_count > 0:
            status = KnowledgeBaseStatus.READY
        else:
            status = KnowledgeBaseStatus.EMPTY

        return await self._kb_repo.save(
            kb.model_copy(
                update={
                    "document_count": len(docs),
                    "chunk_count": chunk_count,
                    "status": status,
                    "last_indexed_at": datetime.now(timezone.utc)
                    if chunk_count > 0
                    else kb.last_indexed_at,
                }
            )
        )


class DocumentService:
    """Handles document upload, extraction, chunking, embedding, and deletion."""

    def __init__(
        self,
        kb_service: KnowledgeBaseService,
        doc_repo: DocumentRepository,
        embedder: EmbeddingProvider,
        vectors: VectorStoreProvider,
    ) -> None:
        self._kb_service = kb_service
        self._doc_repo = doc_repo
        self._embedder = embedder
        self._vectors = vectors

    async def list_documents(self, kb_id: str) -> list[KnowledgeDocument]:
        await self._kb_service.get_knowledge_base(kb_id)
        return await self._doc_repo.list_by_kb(kb_id)

    async def get_document(self, doc_id: str) -> KnowledgeDocument:
        doc = await self._doc_repo.get_by_id(doc_id)
        if doc is None:
            raise DocumentNotFoundError(f"Document '{doc_id}' was not found.")
        return doc

    async def ingest_document(
        self,
        *,
        kb_id: str,
        filename: str,
        content: bytes,
        rag_settings: RAGSettings,
    ) -> KnowledgeDocument:
        kb = await self._kb_service.get_knowledge_base(kb_id)
        safe_name, ext = DocumentParserService.validate_file(
            filename, content, max_size_mb=rag_settings.max_file_size_mb
        )

        doc = KnowledgeDocument(
            id=f"doc_{uuid.uuid4().hex[:12]}",
            knowledge_base_id=kb.id,
            filename=safe_name,
            file_type=ext.lstrip("."),
            size_bytes=len(content),
            status=DocumentStatus.PROCESSING,
        )
        doc = await self._doc_repo.save(doc)

        try:
            t0 = time.monotonic()
            sections = DocumentParserService.parse(
                safe_name, content, max_size_mb=rag_settings.max_file_size_mb
            )
            extraction_ms = int((time.monotonic() - t0) * 1000)

            await self._doc_repo.save_extracted_sections(
                doc.id,
                [
                    {
                        "text": s.text,
                        "page_number": s.page_number,
                        "section_title": s.section_title,
                    }
                    for s in sections
                ],
            )
            return await self._chunk_and_index(
                doc=doc,
                kb=kb,
                sections=sections,
                rag_settings=rag_settings,
                extraction_ms=extraction_ms,
            )
        except DocumentParseError as exc:
            failed = await self._doc_repo.save(
                doc.model_copy(
                    update={"status": DocumentStatus.FAILED, "error_message": str(exc)}
                )
            )
            await self._kb_service.refresh_stats(kb.id)
            return failed
        except Exception as exc:
            logger.exception("Failed to ingest document %s", safe_name)
            failed = await self._doc_repo.save(
                doc.model_copy(
                    update={"status": DocumentStatus.FAILED, "error_message": str(exc)}
                )
            )
            await self._kb_service.refresh_stats(kb.id)
            return failed

    async def _chunk_and_index(
        self,
        *,
        doc: KnowledgeDocument,
        kb: KnowledgeBase,
        sections: list[ParsedSection],
        rag_settings: RAGSettings,
        extraction_ms: int,
    ) -> KnowledgeDocument:
        t1 = time.monotonic()
        chunks = DocumentChunkingService.chunk_sections(
            sections,
            document_id=doc.id,
            knowledge_base_id=kb.id,
            agent_ids=kb.agent_ids,
            source_filename=doc.filename,
            chunk_size_tokens=rag_settings.chunk_size_tokens,
            chunk_overlap_tokens=rag_settings.chunk_overlap_tokens,
        )
        chunking_ms = int((time.monotonic() - t1) * 1000)

        doc = await self._doc_repo.save(
            doc.model_copy(update={"status": DocumentStatus.INDEXING})
        )

        t2 = time.monotonic()
        vectors = await self._embedder.embed_texts([c.content for c in chunks])
        await self._vectors.delete_by_document(knowledge_base_id=kb.id, document_id=doc.id)
        await self._vectors.add_vectors(
            knowledge_base_id=kb.id,
            embedding_model=self._embedder.model_id(),
            chunks=chunks,
            vectors=vectors,
        )
        embedding_ms = int((time.monotonic() - t2) * 1000)

        ready_doc = await self._doc_repo.save(
            doc.model_copy(
                update={
                    "status": DocumentStatus.READY,
                    "chunk_count": len(chunks),
                    "error_message": None,
                    "extraction_ms": extraction_ms,
                    "chunking_ms": chunking_ms,
                    "embedding_ms": embedding_ms,
                }
            )
        )
        await self._kb_service.refresh_stats(kb.id)
        return ready_doc

    async def reprocess_document(
        self, doc_id: str, rag_settings: RAGSettings
    ) -> KnowledgeDocument:
        doc = await self.get_document(doc_id)
        kb = await self._kb_service.get_knowledge_base(doc.knowledge_base_id)
        raw_sections = await self._doc_repo.get_extracted_sections(doc_id)
        if not raw_sections:
            raise DocumentParseError(
                "Original extracted text is unavailable; please re-upload the document."
            )
        sections = [
            ParsedSection(
                text=s["text"],
                page_number=s.get("page_number"),
                section_title=s.get("section_title"),
            )
            for s in raw_sections
        ]
        try:
            return await self._chunk_and_index(
                doc=doc,
                kb=kb,
                sections=sections,
                rag_settings=rag_settings,
                extraction_ms=doc.extraction_ms,
            )
        except Exception as exc:
            failed = await self._doc_repo.save(
                doc.model_copy(
                    update={"status": DocumentStatus.FAILED, "error_message": str(exc)}
                )
            )
            await self._kb_service.refresh_stats(kb.id)
            return failed

    async def delete_document(self, doc_id: str) -> None:
        doc = await self.get_document(doc_id)
        await self._vectors.delete_by_document(
            knowledge_base_id=doc.knowledge_base_id,
            document_id=doc.id,
        )
        await self._doc_repo.delete(doc.id)
        await self._kb_service.refresh_stats(doc.knowledge_base_id)
