"""Knowledge Base, Document Upload, Agent Assignment, and Retrieval API endpoints."""

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.v1.agents import get_agent_service
from app.api.v1.health import get_storage
from app.core.config import Settings, get_settings
from app.providers.embeddings import EmbeddingProvider, EmbeddingProviderFactory
from app.providers.storage import StorageProvider
from app.providers.vector_store import LocalVectorStoreProvider, VectorStoreProvider
from app.repositories.knowledge_repository import DocumentRepository, KnowledgeBaseRepository
from app.schemas.knowledge import (
    DocumentStatus,
    KnowledgeBase,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeDocument,
    RAGSettings,
    RetrievalTestRequest,
    RetrievalTestResult,
)
from app.schemas.response import ApiResponse, ok
from app.services.agent_service import AgentService
from app.services.knowledge_service import DocumentService, KnowledgeBaseService
from app.services.rag_service import RAGService, RAGSettingsService, RetrievalService

router = APIRouter(tags=["knowledge"])


def get_rag_settings_service(
    storage: StorageProvider = Depends(get_storage),
) -> RAGSettingsService:
    return RAGSettingsService(storage)


def get_embedding_provider(
    settings: Settings = Depends(get_settings),
    rag_cfg_svc: RAGSettingsService = Depends(get_rag_settings_service),
) -> EmbeddingProvider:
    rag_cfg = rag_cfg_svc.get_settings()
    cache_dir = settings.resolved_data_dir / "models" / "embeddings"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return EmbeddingProviderFactory.create(
        rag_cfg.embedding_provider,
        model_name=rag_cfg.embedding_model,
        cache_dir=cache_dir,
    )


def get_vector_store(storage: StorageProvider = Depends(get_storage)) -> VectorStoreProvider:
    return LocalVectorStoreProvider(storage)


def get_kb_service(
    storage: StorageProvider = Depends(get_storage),
    embedder: EmbeddingProvider = Depends(get_embedding_provider),
    vectors: VectorStoreProvider = Depends(get_vector_store),
) -> KnowledgeBaseService:
    return KnowledgeBaseService(
        kb_repo=KnowledgeBaseRepository(storage),
        doc_repo=DocumentRepository(storage),
        vector_store=vectors,
        embedding_provider=embedder,
    )


def get_document_service(
    kb_service: KnowledgeBaseService = Depends(get_kb_service),
    storage: StorageProvider = Depends(get_storage),
    embedder: EmbeddingProvider = Depends(get_embedding_provider),
    vectors: VectorStoreProvider = Depends(get_vector_store),
) -> DocumentService:
    return DocumentService(
        kb_service=kb_service,
        doc_repo=DocumentRepository(storage),
        embedder=embedder,
        vectors=vectors,
    )


def get_rag_service(
    storage: StorageProvider = Depends(get_storage),
    embedder: EmbeddingProvider = Depends(get_embedding_provider),
    vectors: VectorStoreProvider = Depends(get_vector_store),
) -> RAGService:
    return RAGService(
        kb_repo=KnowledgeBaseRepository(storage),
        retrieval=RetrievalService(embedding_provider=embedder, vector_store=vectors),
    )


@router.get("/knowledge-bases", response_model=ApiResponse[list[KnowledgeBase]])
async def list_knowledge_bases(
    settings: Settings = Depends(get_settings),
    svc: KnowledgeBaseService = Depends(get_kb_service),
) -> ApiResponse[list[KnowledgeBase]]:
    return ok(await svc.list_knowledge_bases(), version=settings.app_version)


@router.post(
    "/knowledge-bases",
    response_model=ApiResponse[KnowledgeBase],
    status_code=status.HTTP_201_CREATED,
)
async def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    settings: Settings = Depends(get_settings),
    svc: KnowledgeBaseService = Depends(get_kb_service),
) -> ApiResponse[KnowledgeBase]:
    return ok(await svc.create_knowledge_base(payload), version=settings.app_version)


@router.get("/knowledge-bases/{knowledge_base_id}", response_model=ApiResponse[KnowledgeBase])
async def get_knowledge_base(
    knowledge_base_id: str,
    settings: Settings = Depends(get_settings),
    svc: KnowledgeBaseService = Depends(get_kb_service),
) -> ApiResponse[KnowledgeBase]:
    return ok(await svc.get_knowledge_base(knowledge_base_id), version=settings.app_version)


@router.put("/knowledge-bases/{knowledge_base_id}", response_model=ApiResponse[KnowledgeBase])
async def update_knowledge_base(
    knowledge_base_id: str,
    payload: KnowledgeBaseUpdate,
    settings: Settings = Depends(get_settings),
    svc: KnowledgeBaseService = Depends(get_kb_service),
) -> ApiResponse[KnowledgeBase]:
    return ok(
        await svc.update_knowledge_base(knowledge_base_id, payload),
        version=settings.app_version,
    )


@router.delete(
    "/knowledge-bases/{knowledge_base_id}",
    response_model=ApiResponse[dict[str, str | bool]],
)
async def delete_knowledge_base(
    knowledge_base_id: str,
    settings: Settings = Depends(get_settings),
    svc: KnowledgeBaseService = Depends(get_kb_service),
) -> ApiResponse[dict[str, str | bool]]:
    await svc.delete_knowledge_base(knowledge_base_id)
    return ok({"deleted": True, "id": knowledge_base_id}, version=settings.app_version)


@router.post(
    "/knowledge-bases/{knowledge_base_id}/enable",
    response_model=ApiResponse[KnowledgeBase],
)
async def enable_knowledge_base(
    knowledge_base_id: str,
    settings: Settings = Depends(get_settings),
    svc: KnowledgeBaseService = Depends(get_kb_service),
) -> ApiResponse[KnowledgeBase]:
    return ok(await svc.set_enabled(knowledge_base_id, True), version=settings.app_version)


@router.post(
    "/knowledge-bases/{knowledge_base_id}/disable",
    response_model=ApiResponse[KnowledgeBase],
)
async def disable_knowledge_base(
    knowledge_base_id: str,
    settings: Settings = Depends(get_settings),
    svc: KnowledgeBaseService = Depends(get_kb_service),
) -> ApiResponse[KnowledgeBase]:
    return ok(await svc.set_enabled(knowledge_base_id, False), version=settings.app_version)


@router.get(
    "/knowledge-bases/{knowledge_base_id}/documents",
    response_model=ApiResponse[list[KnowledgeDocument]],
)
async def list_kb_documents(
    knowledge_base_id: str,
    settings: Settings = Depends(get_settings),
    doc_svc: DocumentService = Depends(get_document_service),
) -> ApiResponse[list[KnowledgeDocument]]:
    return ok(await doc_svc.list_documents(knowledge_base_id), version=settings.app_version)


@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents",
    response_model=ApiResponse[list[KnowledgeDocument]],
    status_code=status.HTTP_201_CREATED,
)
async def upload_kb_documents(
    knowledge_base_id: str,
    files: list[UploadFile] = File(...),
    settings: Settings = Depends(get_settings),
    doc_svc: DocumentService = Depends(get_document_service),
    rag_cfg_svc: RAGSettingsService = Depends(get_rag_settings_service),
) -> ApiResponse[list[KnowledgeDocument]]:
    rag_cfg = rag_cfg_svc.get_settings()
    results: list[KnowledgeDocument] = []
    for f in files:
        content = await f.read()
        doc = await doc_svc.ingest_document(
            kb_id=knowledge_base_id,
            filename=f.filename or "upload.txt",
            content=content,
            rag_settings=rag_cfg,
        )
        results.append(doc)
    return ok(results, version=settings.app_version)


@router.get("/documents/{document_id}", response_model=ApiResponse[KnowledgeDocument])
async def get_document(
    document_id: str,
    settings: Settings = Depends(get_settings),
    doc_svc: DocumentService = Depends(get_document_service),
) -> ApiResponse[KnowledgeDocument]:
    return ok(await doc_svc.get_document(document_id), version=settings.app_version)


@router.get("/documents/{document_id}/status", response_model=ApiResponse[dict[str, object]])
async def get_document_status(
    document_id: str,
    settings: Settings = Depends(get_settings),
    doc_svc: DocumentService = Depends(get_document_service),
) -> ApiResponse[dict[str, object]]:
    doc = await doc_svc.get_document(document_id)
    return ok(
        {
            "id": doc.id,
            "status": doc.status,
            "chunk_count": doc.chunk_count,
            "error_message": doc.error_message,
        },
        version=settings.app_version,
    )


@router.post("/documents/{document_id}/reprocess", response_model=ApiResponse[KnowledgeDocument])
async def reprocess_document(
    document_id: str,
    settings: Settings = Depends(get_settings),
    doc_svc: DocumentService = Depends(get_document_service),
    rag_cfg_svc: RAGSettingsService = Depends(get_rag_settings_service),
) -> ApiResponse[KnowledgeDocument]:
    rag_cfg = rag_cfg_svc.get_settings()
    return ok(
        await doc_svc.reprocess_document(document_id, rag_cfg),
        version=settings.app_version,
    )


@router.delete("/documents/{document_id}", response_model=ApiResponse[dict[str, str | bool]])
async def delete_document(
    document_id: str,
    settings: Settings = Depends(get_settings),
    doc_svc: DocumentService = Depends(get_document_service),
) -> ApiResponse[dict[str, str | bool]]:
    await doc_svc.delete_document(document_id)
    return ok({"deleted": True, "id": document_id}, version=settings.app_version)


@router.get(
    "/agents/{agent_id}/knowledge-bases",
    response_model=ApiResponse[list[KnowledgeBase]],
)
async def list_agent_kbs(
    agent_id: str,
    settings: Settings = Depends(get_settings),
    agent_svc: AgentService = Depends(get_agent_service),
    kb_svc: KnowledgeBaseService = Depends(get_kb_service),
) -> ApiResponse[list[KnowledgeBase]]:
    await agent_svc.get_agent(agent_id)
    all_kbs = await kb_svc.list_knowledge_bases()
    assigned = [kb for kb in all_kbs if agent_id in kb.agent_ids]
    return ok(assigned, version=settings.app_version)


@router.post(
    "/agents/{agent_id}/knowledge-bases/{knowledge_base_id}",
    response_model=ApiResponse[KnowledgeBase],
)
async def assign_kb_to_agent(
    agent_id: str,
    knowledge_base_id: str,
    settings: Settings = Depends(get_settings),
    agent_svc: AgentService = Depends(get_agent_service),
    kb_svc: KnowledgeBaseService = Depends(get_kb_service),
) -> ApiResponse[KnowledgeBase]:
    await agent_svc.get_agent(agent_id)
    return ok(await kb_svc.assign_agent(knowledge_base_id, agent_id), version=settings.app_version)


@router.delete(
    "/agents/{agent_id}/knowledge-bases/{knowledge_base_id}",
    response_model=ApiResponse[KnowledgeBase],
)
async def unassign_kb_from_agent(
    agent_id: str,
    knowledge_base_id: str,
    settings: Settings = Depends(get_settings),
    agent_svc: AgentService = Depends(get_agent_service),
    kb_svc: KnowledgeBaseService = Depends(get_kb_service),
) -> ApiResponse[KnowledgeBase]:
    await agent_svc.get_agent(agent_id)
    return ok(
        await kb_svc.unassign_agent(knowledge_base_id, agent_id),
        version=settings.app_version,
    )


@router.post(
    "/knowledge-bases/{knowledge_base_id}/search",
    response_model=ApiResponse[RetrievalTestResult],
)
async def search_knowledge_base(
    knowledge_base_id: str,
    payload: RetrievalTestRequest,
    settings: Settings = Depends(get_settings),
    kb_svc: KnowledgeBaseService = Depends(get_kb_service),
    rag_svc: RAGService = Depends(get_rag_service),
) -> ApiResponse[RetrievalTestResult]:
    await kb_svc.get_knowledge_base(knowledge_base_id)
    result = await rag_svc.test_kb_search(
        knowledge_base_id=knowledge_base_id,
        query=payload.query,
        top_k=payload.top_k,
        similarity_threshold=payload.similarity_threshold,
    )
    return ok(result, version=settings.app_version)


@router.post(
    "/agents/{agent_id}/test-retrieval",
    response_model=ApiResponse[RetrievalTestResult],
)
async def test_agent_retrieval(
    agent_id: str,
    payload: RetrievalTestRequest,
    settings: Settings = Depends(get_settings),
    agent_svc: AgentService = Depends(get_agent_service),
    rag_svc: RAGService = Depends(get_rag_service),
) -> ApiResponse[RetrievalTestResult]:
    agent = await agent_svc.get_agent(agent_id)
    kb_id = agent.knowledge_base.knowledge_base_id
    if not kb_id or not agent.knowledge_base.enabled:
        return ok(
            RetrievalTestResult(query=payload.query, hits=[], grounded=False, retrieval_ms=0),
            version=settings.app_version,
        )
    result = await rag_svc.test_kb_search(
        knowledge_base_id=kb_id,
        query=payload.query,
        top_k=payload.top_k,
        similarity_threshold=payload.similarity_threshold,
        agent_id=agent.id,
    )
    return ok(result, version=settings.app_version)


@router.get("/rag/settings", response_model=ApiResponse[RAGSettings])
async def get_rag_settings(
    settings: Settings = Depends(get_settings),
    rag_cfg_svc: RAGSettingsService = Depends(get_rag_settings_service),
) -> ApiResponse[RAGSettings]:
    return ok(rag_cfg_svc.get_settings(), version=settings.app_version)


@router.put("/rag/settings", response_model=ApiResponse[RAGSettings])
async def update_rag_settings(
    payload: RAGSettings,
    settings: Settings = Depends(get_settings),
    rag_cfg_svc: RAGSettingsService = Depends(get_rag_settings_service),
) -> ApiResponse[RAGSettings]:
    return ok(rag_cfg_svc.update_settings(payload), version=settings.app_version)
