"""Versioned Knowledge Base manifests and deterministic provenance validation."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
import json
from pathlib import Path
import re
from typing import Any
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, field_validator

from educoach.rag import InMemoryRetriever, KnowledgeChunk


class KnowledgeStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class KnowledgeCategory(StrEnum):
    LEARNING_METHOD = "learning_method"
    STUDY_PLANNING = "study_planning"
    METACOGNITION = "metacognition"
    EXAM_RULE = "exam_rule"


class KnowledgeSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    canonical_url: str = Field(min_length=1)
    citation: str = Field(min_length=1)
    doi: str | None = None
    published_date: date
    retrieved_date: date
    version: str = Field(min_length=1)
    language: str = Field(min_length=1)
    status: KnowledgeStatus

    @field_validator(
        "source_id",
        "title",
        "publisher",
        "source_type",
        "canonical_url",
        "citation",
        "version",
        "language",
    )
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        return _required_text(value)

    @field_validator("doi")
    @classmethod
    def normalize_optional_doi(cls, value: str | None) -> str | None:
        return _required_text(value) if value is not None else None


class KnowledgeDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    language: str = Field(min_length=1)
    program: str = Field(min_length=1)
    category: KnowledgeCategory
    status: KnowledgeStatus

    @field_validator("document_id", "source_id", "version", "language", "program")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        return _required_text(value)


@dataclass(frozen=True)
class KnowledgeBase:
    sources: tuple[KnowledgeSource, ...]
    documents: tuple[KnowledgeDocument, ...]
    chunks: tuple[KnowledgeChunk, ...]

    @property
    def active_chunks(self) -> tuple[KnowledgeChunk, ...]:
        return tuple(
            chunk
            for chunk in self.chunks
            if chunk.metadata["status"] == KnowledgeStatus.ACTIVE
        )


def load_knowledge_base(directory: str | Path) -> KnowledgeBase:
    root = Path(directory)
    sources = tuple(
        KnowledgeSource.model_validate(item)
        for item in _load_manifest(root / "sources_v1.json")
    )
    documents = tuple(
        KnowledgeDocument.model_validate(item)
        for item in _load_manifest(root / "documents_v1.json")
    )
    chunks = tuple(InMemoryRetriever.from_directory(root).chunks)
    validate_knowledge_base(sources, documents, chunks)
    return KnowledgeBase(sources=sources, documents=documents, chunks=chunks)


def load_active_retriever(directory: str | Path) -> InMemoryRetriever:
    catalog = load_knowledge_base(directory)
    return InMemoryRetriever(list(catalog.active_chunks))


def validate_knowledge_base(
    sources: tuple[KnowledgeSource, ...],
    documents: tuple[KnowledgeDocument, ...],
    chunks: tuple[KnowledgeChunk, ...],
) -> None:
    source_by_id = _unique_by_id(sources, "source_id")
    document_by_id = _unique_by_id(documents, "document_id")

    for document in documents:
        if document.source_id not in source_by_id:
            raise ValueError(
                f"Knowledge document references unknown source_id: {document.source_id}"
            )

    normalized_texts: set[str] = set()
    required_metadata = {
        "source_id",
        "document_id",
        "category",
        "version",
        "language",
        "program",
        "status",
        "chunk_index",
    }
    for chunk in chunks:
        if any(
            not isinstance(key, str)
            or not isinstance(value, str)
            or not key.strip()
            or not value.strip()
            for key, value in chunk.metadata.items()
        ):
            raise ValueError(
                f"Knowledge chunk metadata must contain non-empty strings: {chunk.chunk_id}"
            )
        missing = required_metadata - chunk.metadata.keys()
        if missing:
            raise ValueError(
                f"Knowledge chunk required metadata missing for {chunk.chunk_id}: "
                f"{', '.join(sorted(missing))}"
            )

        source_id = chunk.metadata["source_id"]
        document_id = chunk.metadata["document_id"]
        source = source_by_id.get(source_id)
        if source is None:
            raise ValueError(
                f"Knowledge chunk references unknown source_id: {source_id}"
            )
        document = document_by_id.get(document_id)
        if document is None:
            raise ValueError(
                f"Knowledge chunk references unknown document_id: {document_id}"
            )
        if document.source_id != source_id:
            raise ValueError(
                f"Knowledge chunk source/document mismatch: {chunk.chunk_id}"
            )
        if chunk.source != source.citation:
            raise ValueError(
                f"Knowledge chunk citation does not match source: {chunk.chunk_id}"
            )

        category = KnowledgeCategory(chunk.metadata["category"])
        status = KnowledgeStatus(chunk.metadata["status"])
        if category != document.category:
            raise ValueError(
                f"Knowledge chunk category does not match document: {chunk.chunk_id}"
            )
        if chunk.metadata["program"] != document.program:
            raise ValueError(
                f"Knowledge chunk program does not match document: {chunk.chunk_id}"
            )
        if chunk.metadata["version"] != document.version:
            raise ValueError(
                f"Knowledge chunk version does not match document: {chunk.chunk_id}"
            )
        if status != document.status:
            raise ValueError(
                f"Knowledge chunk status does not match document: {chunk.chunk_id}"
            )

        normalized_text = _normalize_exact_text(chunk.text)
        if normalized_text in normalized_texts:
            raise ValueError(f"Duplicate knowledge text: {chunk.chunk_id}")
        normalized_texts.add(normalized_text)


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
        raise ValueError(f"Knowledge manifest must be a JSON array of objects: {path}")
    return data


def _unique_by_id(items: tuple[Any, ...], field_name: str) -> dict[str, Any]:
    indexed: dict[str, Any] = {}
    for item in items:
        identifier = getattr(item, field_name)
        if identifier in indexed:
            raise ValueError(f"Duplicate knowledge {field_name}: {identifier}")
        indexed[identifier] = item
    return indexed


def _required_text(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Knowledge manifest text fields cannot be empty")
    return cleaned


def _normalize_exact_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.translate(str.maketrans({"I": "ı", "İ": "i"}))
    normalized = normalized.casefold()
    return re.sub(r"\s+", " ", normalized).strip()
