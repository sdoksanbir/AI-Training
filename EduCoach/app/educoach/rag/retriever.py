from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    text: str
    title: str
    source: str
    metadata: dict[str, str] = field(default_factory=dict)


class Retriever(Protocol):
    def search(self, query: str, limit: int = 3) -> list[KnowledgeChunk]: ...


class InMemoryRetriever:
    def __init__(self, chunks: list[KnowledgeChunk] = ()) -> None:
        self.chunks = list(chunks)

    def search(self, query: str, limit: int = 3) -> list[KnowledgeChunk]:
        terms = {term.lower() for term in query.split() if len(term) > 2}
        ranked = sorted(
            self.chunks,
            key=lambda chunk: len(terms & set(chunk.text.lower().split())),
            reverse=True,
        )
        return [chunk for chunk in ranked if terms & set(chunk.text.lower().split())][:limit]
