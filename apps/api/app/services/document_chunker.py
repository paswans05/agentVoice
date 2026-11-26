"""Configurable paragraph/sentence-aware document chunking service."""

from __future__ import annotations

import re
import uuid

from app.schemas.knowledge import DocumentChunk
from app.services.document_parser import ParsedSection


class DocumentChunkingService:
    """Splits extracted sections into overlapping chunks while preserving metadata."""

    @staticmethod
    def _split_paragraphs_and_sentences(text: str) -> list[str]:
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        units: list[str] = []
        for para in paragraphs:
            words = para.split()
            if len(words) <= 200:
                units.append(para)
            else:
                sentences = [s.strip() for s in re.split(r"(?<=[.!?।])\s+", para) if s.strip()]
                units.extend(sentences)
        return units

    @classmethod
    def chunk_sections(
        cls,
        sections: list[ParsedSection],
        *,
        document_id: str,
        knowledge_base_id: str,
        agent_ids: list[str],
        source_filename: str,
        chunk_size_tokens: int = 800,
        chunk_overlap_tokens: int = 120,
    ) -> list[DocumentChunk]:
        """Create DocumentChunk objects with overlap and source metadata."""
        chunks: list[DocumentChunk] = []
        chunk_idx = 0

        for section in sections:
            units = cls._split_paragraphs_and_sentences(section.text)
            current_words: list[str] = []

            for unit in units:
                unit_words = unit.split()
                if not unit_words:
                    continue

                if current_words and len(current_words) + len(unit_words) > chunk_size_tokens:
                    chunk_text = " ".join(current_words).strip()
                    chunks.append(
                        DocumentChunk(
                            chunk_id=f"chk_{uuid.uuid4().hex[:12]}",
                            document_id=document_id,
                            knowledge_base_id=knowledge_base_id,
                            agent_ids=list(agent_ids),
                            content=chunk_text,
                            chunk_index=chunk_idx,
                            page_number=section.page_number,
                            section_title=section.section_title,
                            source_filename=source_filename,
                        )
                    )
                    chunk_idx += 1
                    overlap = current_words[-chunk_overlap_tokens:] if chunk_overlap_tokens > 0 else []
                    current_words = list(overlap)

                current_words.extend(unit_words)

                # Handle unusually long single unit
                while len(current_words) > chunk_size_tokens:
                    slice_words = current_words[:chunk_size_tokens]
                    chunks.append(
                        DocumentChunk(
                            chunk_id=f"chk_{uuid.uuid4().hex[:12]}",
                            document_id=document_id,
                            knowledge_base_id=knowledge_base_id,
                            agent_ids=list(agent_ids),
                            content=" ".join(slice_words).strip(),
                            chunk_index=chunk_idx,
                            page_number=section.page_number,
                            section_title=section.section_title,
                            source_filename=source_filename,
                        )
                    )
                    chunk_idx += 1
                    overlap = slice_words[-chunk_overlap_tokens:] if chunk_overlap_tokens > 0 else []
                    current_words = list(overlap) + current_words[chunk_size_tokens:]

            if current_words:
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"chk_{uuid.uuid4().hex[:12]}",
                        document_id=document_id,
                        knowledge_base_id=knowledge_base_id,
                        agent_ids=list(agent_ids),
                        content=" ".join(current_words).strip(),
                        chunk_index=chunk_idx,
                        page_number=section.page_number,
                        section_title=section.section_title,
                        source_filename=source_filename,
                    )
                )
                chunk_idx += 1

        return chunks
