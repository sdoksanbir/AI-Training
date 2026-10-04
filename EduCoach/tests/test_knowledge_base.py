from copy import deepcopy
import json
from pathlib import Path

import pytest

from educoach.knowledge import (
    KnowledgeStatus,
    load_active_retriever,
    load_knowledge_base,
)
from educoach.llm import FakeLLMProvider
from educoach.models import ContextType, Learner, LearningContext
from educoach.orchestrator import CoachOrchestrator
from educoach.persistence import create_schema, create_session_factory, create_sqlite_engine
from educoach.rag import InMemoryRetriever
from educoach.services import LearnerMemoryService


KNOWLEDGE_PATH = Path("data/knowledge")

SOURCE = {
    "source_id": "src-test",
    "title": "Test source",
    "publisher": "Test publisher",
    "source_type": "research",
    "canonical_url": "https://example.test/source",
    "citation": "Test Source (2026)",
    "published_date": "2026-01-01",
    "retrieved_date": "2026-10-04",
    "version": "1",
    "language": "en",
    "status": "active",
}
DOCUMENT = {
    "document_id": "doc-test",
    "source_id": "src-test",
    "version": "1",
    "language": "en",
    "program": "global",
    "category": "learning_method",
    "status": "active",
}
CHUNK = {
    "chunk_id": "chunk-test",
    "title": "Aktif hatırlama",
    "text": "Aktif hatırlama öğrenmeyi destekler.",
    "source": "Test Source (2026)",
    "metadata": {
        "source_id": "src-test",
        "document_id": "doc-test",
        "category": "learning_method",
        "version": "1",
        "language": "tr",
        "program": "global",
        "status": "active",
        "chunk_index": "1",
    },
}


def write_catalog(
    root: Path,
    *,
    sources: list[dict] | None = None,
    documents: list[dict] | None = None,
    chunks: list[dict] | None = None,
) -> Path:
    root.mkdir()
    (root / "sources_v1.json").write_text(
        json.dumps(sources or [deepcopy(SOURCE)], ensure_ascii=False),
        encoding="utf-8",
    )
    (root / "documents_v1.json").write_text(
        json.dumps(documents or [deepcopy(DOCUMENT)], ensure_ascii=False),
        encoding="utf-8",
    )
    chunk_rows = chunks or [deepcopy(CHUNK)]
    (root / "learning_methods_v1.jsonl").write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in chunk_rows) + "\n",
        encoding="utf-8",
    )
    return root


def test_source_manifest_loading(tmp_path: Path) -> None:
    catalog = load_knowledge_base(write_catalog(tmp_path / "knowledge"))

    assert catalog.sources[0].source_id == "src-test"
    assert catalog.sources[0].status is KnowledgeStatus.ACTIVE


def test_document_manifest_loading(tmp_path: Path) -> None:
    catalog = load_knowledge_base(write_catalog(tmp_path / "knowledge"))

    assert catalog.documents[0].document_id == "doc-test"
    assert catalog.documents[0].source_id == "src-test"


def test_valid_knowledge_base_loads(tmp_path: Path) -> None:
    catalog = load_knowledge_base(write_catalog(tmp_path / "knowledge"))

    assert len(catalog.sources) == 1
    assert len(catalog.documents) == 1
    assert len(catalog.chunks) == 1


def test_duplicate_source_is_rejected(tmp_path: Path) -> None:
    sources = [deepcopy(SOURCE), deepcopy(SOURCE)]

    with pytest.raises(ValueError, match="Duplicate knowledge source_id"):
        load_knowledge_base(write_catalog(tmp_path / "knowledge", sources=sources))


def test_duplicate_document_is_rejected(tmp_path: Path) -> None:
    documents = [deepcopy(DOCUMENT), deepcopy(DOCUMENT)]

    with pytest.raises(ValueError, match="Duplicate knowledge document_id"):
        load_knowledge_base(
            write_catalog(tmp_path / "knowledge", documents=documents)
        )


def test_duplicate_chunk_is_rejected(tmp_path: Path) -> None:
    chunks = [deepcopy(CHUNK), deepcopy(CHUNK)]

    with pytest.raises(ValueError, match="Duplicate knowledge chunk_id"):
        load_knowledge_base(write_catalog(tmp_path / "knowledge", chunks=chunks))


def test_orphan_document_is_rejected(tmp_path: Path) -> None:
    document = deepcopy(DOCUMENT)
    document["source_id"] = "missing-source"

    with pytest.raises(ValueError, match="unknown source_id"):
        load_knowledge_base(
            write_catalog(tmp_path / "knowledge", documents=[document])
        )


def test_orphan_chunk_source_is_rejected(tmp_path: Path) -> None:
    chunk = deepcopy(CHUNK)
    chunk["metadata"]["source_id"] = "missing-source"

    with pytest.raises(ValueError, match="unknown source_id"):
        load_knowledge_base(write_catalog(tmp_path / "knowledge", chunks=[chunk]))


def test_orphan_chunk_document_is_rejected(tmp_path: Path) -> None:
    chunk = deepcopy(CHUNK)
    chunk["metadata"]["document_id"] = "missing-document"

    with pytest.raises(ValueError, match="unknown document_id"):
        load_knowledge_base(write_catalog(tmp_path / "knowledge", chunks=[chunk]))


def test_invalid_status_is_rejected(tmp_path: Path) -> None:
    source = deepcopy(SOURCE)
    source["status"] = "unknown"

    with pytest.raises(ValueError, match="status"):
        load_knowledge_base(write_catalog(tmp_path / "knowledge", sources=[source]))


def test_invalid_category_is_rejected(tmp_path: Path) -> None:
    document = deepcopy(DOCUMENT)
    document["category"] = "unsupported"

    with pytest.raises(ValueError, match="category"):
        load_knowledge_base(
            write_catalog(tmp_path / "knowledge", documents=[document])
        )


def test_missing_required_chunk_metadata_is_rejected(tmp_path: Path) -> None:
    chunk = deepcopy(CHUNK)
    del chunk["metadata"]["language"]

    with pytest.raises(ValueError, match="required metadata missing"):
        load_knowledge_base(write_catalog(tmp_path / "knowledge", chunks=[chunk]))


def test_source_document_chunk_provenance_must_be_consistent(
    tmp_path: Path,
) -> None:
    second_source = deepcopy(SOURCE)
    second_source["source_id"] = "src-second"
    second_source["citation"] = "Second Source (2026)"
    chunk = deepcopy(CHUNK)
    chunk["metadata"]["source_id"] = "src-second"
    chunk["source"] = "Second Source (2026)"

    with pytest.raises(ValueError, match="source/document mismatch"):
        load_knowledge_base(
            write_catalog(
                tmp_path / "knowledge",
                sources=[deepcopy(SOURCE), second_source],
                chunks=[chunk],
            )
        )


def test_exact_duplicate_knowledge_text_is_rejected(tmp_path: Path) -> None:
    duplicate = deepcopy(CHUNK)
    duplicate["chunk_id"] = "chunk-second"
    duplicate["metadata"]["chunk_index"] = "2"
    duplicate["text"] = "  AKTİF HATIRLAMA   öğrenmeyi destekler.  "

    with pytest.raises(ValueError, match="Duplicate knowledge text"):
        load_knowledge_base(
            write_catalog(
                tmp_path / "knowledge",
                chunks=[deepcopy(CHUNK), duplicate],
            )
        )


def test_real_knowledge_catalog_is_valid() -> None:
    catalog = load_knowledge_base(KNOWLEDGE_PATH)

    assert len(catalog.sources) == 5
    assert len(catalog.documents) == 6
    assert len(catalog.chunks) == 14
    assert {document.category.value for document in catalog.documents} == {
        "learning_method",
        "study_planning",
        "metacognition",
        "exam_rule",
    }
    assert {document.program for document in catalog.documents} == {"global", "yks"}
    assert all(chunk.source != "EduCoach internal guide v1" for chunk in catalog.chunks)


def test_real_catalog_retrieves_global_learning_method() -> None:
    catalog = load_knowledge_base(KNOWLEDGE_PATH)
    retriever = InMemoryRetriever(list(catalog.chunks))

    results = retriever.search(
        "aktif hatırlama",
        filters={"program": "global", "category": "learning_method"},
    )

    assert results[0].chunk_id == "learning-active-recall-v1-001"


def test_real_catalog_retrieves_archived_yks_rule() -> None:
    catalog = load_knowledge_base(KNOWLEDGE_PATH)
    retriever = InMemoryRetriever(list(catalog.chunks))

    results = retriever.search(
        "2026 YKS oturumları",
        filters={"program": "yks", "status": "archived"},
    )

    assert results[0].chunk_id == "yks-2026-sessions-v1-001"
    assert all(item.metadata["program"] == "yks" for item in results)


def test_active_retriever_keeps_history_out_of_production_catalog() -> None:
    catalog = load_knowledge_base(KNOWLEDGE_PATH)
    retriever = load_active_retriever(KNOWLEDGE_PATH)

    assert any(
        chunk.metadata["status"] == "archived" for chunk in catalog.chunks
    )
    assert all(chunk.metadata["status"] == "active" for chunk in retriever.chunks)
    assert retriever.search("2026 YKS oturumları") == []
    assert retriever.search(
        "aktif hatırlama", filters={"program": "global"}
    )[0].chunk_id == "learning-active-recall-v1-001"


def test_archived_knowledge_cannot_reach_learner_context() -> None:
    engine = create_sqlite_engine("sqlite+pysqlite:///:memory:")
    create_schema(engine)
    factory = create_session_factory(engine)
    learner = Learner()
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.ENTRANCE_EXAM,
        program_code="yks",
    )
    memory = LearnerMemoryService(factory)
    memory.register_learner(learner, [context])
    provider = FakeLLMProvider(responder=lambda _: "Güncel kaynağı kontrol edelim.")

    CoachOrchestrator(
        memory,
        provider,
        load_active_retriever(KNOWLEDGE_PATH),
    ).respond(learner.learner_id, "2026 YKS oturumları")

    memory_context = provider.requests[-1].memory_context
    assert "2026-YKS tarihsel olarak üç oturumda uygulandı" not in memory_context
    assert "Bu kayıt yalnız 2026-YKS dönemini açıklar" not in memory_context
    engine.dispose()


def test_real_catalog_excludes_wrong_program() -> None:
    catalog = load_knowledge_base(KNOWLEDGE_PATH)
    retriever = InMemoryRetriever(list(catalog.chunks))

    results = retriever.search("2026 YKS", filters={"program": "global"})

    assert all(item.metadata["program"] != "yks" for item in results)
