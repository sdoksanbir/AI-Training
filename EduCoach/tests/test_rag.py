from pathlib import Path

import pytest

from educoach.llm import FakeLLMProvider
from educoach.models import ContextType, Learner, LearningContext
from educoach.orchestrator import CoachOrchestrator
from educoach.persistence import create_schema, create_session_factory, create_sqlite_engine
from educoach.rag import InMemoryRetriever, KnowledgeChunk
from educoach.services import LearnerMemoryService


KNOWLEDGE_PATH = Path("data/knowledge/learning_methods_v1.jsonl")


def chunk(
    chunk_id: str,
    text: str,
    title: str = "Başlık",
    metadata: dict[str, str] | None = None,
) -> KnowledgeChunk:
    return KnowledgeChunk(chunk_id, text, title, "test", metadata or {})


def test_jsonl_loading(tmp_path: Path) -> None:
    path = tmp_path / "knowledge.jsonl"
    path.write_text(
        '{"chunk_id":"c1","text":"Aktif hatırlama","title":"Öğrenme",'
        '"source":"guide","metadata":{"version":"1"}}\n',
        encoding="utf-8",
    )

    retriever = InMemoryRetriever.from_jsonl(path)

    assert [item.chunk_id for item in retriever.chunks] == ["c1"]
    assert retriever.chunks[0].metadata == {"version": "1"}


def test_directory_loading_is_sorted(tmp_path: Path) -> None:
    (tmp_path / "b.jsonl").write_text(
        '{"chunk_id":"b","text":"Bilgi B","title":"B","source":"test"}\n',
        encoding="utf-8",
    )
    (tmp_path / "a.jsonl").write_text(
        '{"chunk_id":"a","text":"Bilgi A","title":"A","source":"test"}\n',
        encoding="utf-8",
    )

    retriever = InMemoryRetriever.from_directory(tmp_path)

    assert [item.chunk_id for item in retriever.chunks] == ["a", "b"]


def test_duplicate_chunk_id_in_direct_list_is_rejected() -> None:
    with pytest.raises(ValueError, match="Duplicate knowledge chunk_id: duplicate"):
        InMemoryRetriever([chunk("duplicate", "Bir"), chunk("duplicate", "İki")])


def test_duplicate_chunk_id_across_jsonl_files_is_rejected(tmp_path: Path) -> None:
    for name in ("a.jsonl", "b.jsonl"):
        (tmp_path / name).write_text(
            '{"chunk_id":"duplicate","text":"Bilgi","title":"Başlık",'
            '"source":"test"}\n',
            encoding="utf-8",
        )

    with pytest.raises(ValueError, match="Duplicate knowledge chunk_id: duplicate"):
        InMemoryRetriever.from_directory(tmp_path)


def test_metadata_string_filter() -> None:
    retriever = InMemoryRetriever([
        chunk("yks", "Matematik", metadata={"program": "yks"}),
        chunk("lgs", "Matematik", metadata={"program": "lgs"}),
    ])

    assert [item.chunk_id for item in retriever.search(
        "matematik", filters={"program": "yks"}
    )] == ["yks"]


def test_metadata_set_filter() -> None:
    retriever = InMemoryRetriever([
        chunk("global", "Matematik", metadata={"program": "global"}),
        chunk("yks", "Matematik", metadata={"program": "yks"}),
        chunk("lgs", "Matematik", metadata={"program": "lgs"}),
    ])

    results = retriever.search(
        "matematik", filters={"program": {"global", "yks"}}
    )

    assert [item.chunk_id for item in results] == ["global", "yks"]


def test_multiple_metadata_filters_use_and_semantics() -> None:
    retriever = InMemoryRetriever([
        chunk(
            "tr-yks",
            "Matematik",
            metadata={"program": "yks", "language": "tr"},
        ),
        chunk(
            "en-yks",
            "Matematik",
            metadata={"program": "yks", "language": "en"},
        ),
    ])

    results = retriever.search(
        "matematik", filters={"program": "yks", "language": "tr"}
    )

    assert [item.chunk_id for item in results] == ["tr-yks"]


def test_missing_metadata_does_not_pass_filter() -> None:
    retriever = InMemoryRetriever([
        chunk("missing", "Matematik"),
        chunk("yks", "Matematik", metadata={"program": "yks"}),
    ])

    assert [item.chunk_id for item in retriever.search(
        "matematik", filters={"program": "yks"}
    )] == ["yks"]


@pytest.mark.parametrize(
    ("stored", "query"),
    [
        ("İSTANBUL", "istanbul"),
        ("IŞIK", "ışık"),
        ("ÇĞÖŞÜ", "çğöşü"),
        ("I\u0307STANBUL", "istanbul"),
        ("Aktif, hatırlama!", "aktif hatırlama"),
    ],
)
def test_turkish_normalization_and_punctuation(stored: str, query: str) -> None:
    retriever = InMemoryRetriever([chunk("match", stored)])

    assert [item.chunk_id for item in retriever.search(query)] == ["match"]


@pytest.mark.parametrize("query", ["", "   ", "a ve"])
def test_empty_or_unusable_query_returns_no_results(query: str) -> None:
    retriever = InMemoryRetriever([chunk("c1", "Aktif hatırlama")])

    assert retriever.search(query) == []


def test_no_match_returns_no_results() -> None:
    retriever = InMemoryRetriever([chunk("c1", "Aktif hatırlama")])

    assert retriever.search("mitokondri") == []


def test_zero_limit_returns_no_results() -> None:
    retriever = InMemoryRetriever([chunk("c1", "Aktif hatırlama")])

    assert retriever.search("aktif", limit=0) == []


def test_negative_limit_is_rejected() -> None:
    retriever = InMemoryRetriever([chunk("c1", "Aktif hatırlama")])

    with pytest.raises(ValueError, match="limit cannot be negative"):
        retriever.search("aktif", limit=-1)


def test_explicit_limit_is_applied() -> None:
    retriever = InMemoryRetriever([
        chunk("a", "Aktif hatırlama"),
        chunk("b", "Aktif tekrar"),
    ])

    assert len(retriever.search("aktif", limit=1)) == 1


def test_title_only_match_is_retrievable() -> None:
    retriever = InMemoryRetriever([
        chunk("title", "Genel açıklama", title="Mitokondri"),
    ])

    assert [item.chunk_id for item in retriever.search("mitokondri")] == ["title"]


def test_title_match_is_weighted_above_text_match() -> None:
    retriever = InMemoryRetriever([
        chunk("text", "Mitokondri açıklaması", title="Biyoloji"),
        chunk("title", "Hücre açıklaması", title="Mitokondri"),
    ])

    assert retriever.search("mitokondri")[0].chunk_id == "title"


def test_rare_term_has_more_weight_than_common_term() -> None:
    retriever = InMemoryRetriever([
        chunk("common-a", "Çalışma çalışma çalışma", title="Genel"),
        chunk("common-b", "Çalışma düzeni", title="Genel"),
        chunk("rare", "Mitokondri", title="Genel"),
    ])

    assert retriever.search("çalışma mitokondri")[0].chunk_id == "rare"


def test_term_frequency_affects_ranking() -> None:
    retriever = InMemoryRetriever([
        chunk("frequent", "Tekrar tekrar tekrar", title="Genel"),
        chunk("single", "Tekrar", title="Genel"),
    ])

    assert retriever.search("tekrar")[0].chunk_id == "frequent"


def test_equal_scores_use_chunk_id_as_tie_break() -> None:
    retriever = InMemoryRetriever([
        chunk("z-last", "Aktif hatırlama"),
        chunk("a-first", "Aktif hatırlama"),
    ])

    assert [item.chunk_id for item in retriever.search("aktif")] == [
        "a-first",
        "z-last",
    ]


def test_global_and_matching_program_are_included() -> None:
    retriever = InMemoryRetriever([
        chunk("global", "Tekrar yöntemi", metadata={"program": "global"}),
        chunk("yks", "Tekrar yöntemi", metadata={"program": "yks"}),
        chunk("lgs", "Tekrar yöntemi", metadata={"program": "lgs"}),
    ])

    results = retriever.search(
        "tekrar", filters={"program": {"global", "yks"}}
    )

    assert [item.chunk_id for item in results] == ["global", "yks"]


def test_orchestrator_uses_global_catalog_and_excludes_wrong_program() -> None:
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
    catalog = InMemoryRetriever.from_jsonl(KNOWLEDGE_PATH)
    retriever = InMemoryRetriever([
        *catalog.chunks,
        chunk(
            "lgs-only",
            "Aktif hatırlama LGS özel içeriği.",
            title="LGS özel",
            metadata={"program": "lgs"},
        ),
    ])
    provider = FakeLLMProvider()

    CoachOrchestrator(memory, provider, retriever).respond(
        learner.learner_id, "Aktif hatırlama nasıl yapılır?"
    )

    memory_context = provider.requests[-1].memory_context
    assert "cevabı kaynağa bakmadan üretmeye çalışmaktır" in memory_context
    assert "LGS özel içeriği" not in memory_context
    engine.dispose()
