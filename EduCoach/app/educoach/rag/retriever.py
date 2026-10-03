from dataclasses import dataclass, field
import json
import re
from pathlib import Path
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
    @classmethod
    def from_jsonl(cls, path: str | Path) -> "InMemoryRetriever":
        chunks: list[KnowledgeChunk] = []
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            required = ("chunk_id", "text", "title", "source")
            if any(not isinstance(item.get(key), str) or not item[key].strip() for key in required):
                raise ValueError("Knowledge chunk required fields are invalid")
            if not isinstance(item.get("metadata", {}), dict):
                raise ValueError("Knowledge chunk metadata must be an object")
            chunks.append(KnowledgeChunk(**item))
        return cls(chunks)

    def __init__(self, chunks: list[KnowledgeChunk] = ()) -> None:
        self.chunks = list(chunks)

    def search(
        self,
        query: str,
        limit: int = 3,
        filters: dict[str, str | set[str]] | None = None,
    ) -> list[KnowledgeChunk]:
        terms = self._terms(query)
        candidates = self.chunks
        if filters:
            candidates = [
                chunk for chunk in candidates
                if all(
                    chunk.metadata.get(key) in value
                    if isinstance(value, set)
                    else chunk.metadata.get(key) == value
                    for key, value in filters.items()
                )
            ]
        ranked = sorted(
            candidates,
            key=lambda chunk: len(terms & self._terms(chunk.text)),
            reverse=True,
        )
        return [chunk for chunk in ranked if terms & self._terms(chunk.text)][:limit]

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {
            term for term in re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+", text.casefold())
            if len(term) > 2
        }
