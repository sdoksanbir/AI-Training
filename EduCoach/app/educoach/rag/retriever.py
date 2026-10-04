from collections import Counter
from dataclasses import dataclass, field
import json
import math
import re
from pathlib import Path
from typing import Protocol
import unicodedata


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    text: str
    title: str
    source: str
    metadata: dict[str, str] = field(default_factory=dict)


class Retriever(Protocol):
    def search(
        self,
        query: str,
        limit: int = 3,
        filters: dict[str, str | set[str]] | None = None,
    ) -> list[KnowledgeChunk]: ...


class InMemoryRetriever:
    _TITLE_WEIGHT = 2.5
    _BM25_K1 = 1.2
    _BM25_B = 0.75

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

    @classmethod
    def from_directory(cls, directory: str | Path) -> "InMemoryRetriever":
        root = Path(directory)
        chunks: list[KnowledgeChunk] = []
        for path in sorted(root.glob("*.jsonl")):
            chunks.extend(cls.from_jsonl(path).chunks)
        return cls(chunks)

    def __init__(self, chunks: list[KnowledgeChunk] = ()) -> None:
        self.chunks = list(chunks)
        chunk_ids: set[str] = set()
        for chunk in self.chunks:
            if chunk.chunk_id in chunk_ids:
                raise ValueError(f"Duplicate knowledge chunk_id: {chunk.chunk_id}")
            chunk_ids.add(chunk.chunk_id)

        self._title_terms = {
            chunk.chunk_id: Counter(self._tokens(chunk.title)) for chunk in self.chunks
        }
        self._text_terms = {
            chunk.chunk_id: Counter(self._tokens(chunk.text)) for chunk in self.chunks
        }
        self._document_frequency: Counter[str] = Counter()
        for chunk in self.chunks:
            terms = set(self._title_terms[chunk.chunk_id]) | set(
                self._text_terms[chunk.chunk_id]
            )
            self._document_frequency.update(terms)

        self._average_title_length = self._average_length(self._title_terms)
        self._average_text_length = self._average_length(self._text_terms)

    def search(
        self,
        query: str,
        limit: int = 3,
        filters: dict[str, str | set[str]] | None = None,
    ) -> list[KnowledgeChunk]:
        if limit < 0:
            raise ValueError("limit cannot be negative")
        if limit == 0:
            return []

        query_terms = Counter(self._tokens(query))
        if not query_terms:
            return []

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
        scored = [
            (self._score(chunk, query_terms), chunk)
            for chunk in candidates
        ]
        ranked = sorted(
            (item for item in scored if item[0] > 0),
            key=lambda item: (-item[0], item[1].chunk_id),
        )
        return [chunk for _, chunk in ranked[:limit]]

    def _score(
        self,
        chunk: KnowledgeChunk,
        query_terms: Counter[str],
    ) -> float:
        score = 0.0
        title_terms = self._title_terms[chunk.chunk_id]
        text_terms = self._text_terms[chunk.chunk_id]
        for term, query_frequency in query_terms.items():
            document_frequency = self._document_frequency.get(term, 0)
            if document_frequency == 0:
                continue
            inverse_document_frequency = math.log(
                1
                + (
                    len(self.chunks) - document_frequency + 0.5
                ) / (document_frequency + 0.5)
            )
            query_weight = 1.0 + math.log(query_frequency)
            title_score = self._bm25_term_score(
                title_terms.get(term, 0),
                sum(title_terms.values()),
                self._average_title_length,
            )
            text_score = self._bm25_term_score(
                text_terms.get(term, 0),
                sum(text_terms.values()),
                self._average_text_length,
            )
            score += inverse_document_frequency * query_weight * (
                self._TITLE_WEIGHT * title_score + text_score
            )
        return score

    @classmethod
    def _bm25_term_score(
        cls,
        term_frequency: int,
        document_length: int,
        average_document_length: float,
    ) -> float:
        if term_frequency == 0:
            return 0.0
        length_ratio = (
            document_length / average_document_length
            if average_document_length
            else 0.0
        )
        denominator = term_frequency + cls._BM25_K1 * (
            1.0 - cls._BM25_B + cls._BM25_B * length_ratio
        )
        return term_frequency * (cls._BM25_K1 + 1.0) / denominator

    @staticmethod
    def _average_length(term_counts: dict[str, Counter[str]]) -> float:
        if not term_counts:
            return 0.0
        return sum(sum(counts.values()) for counts in term_counts.values()) / len(
            term_counts
        )

    @staticmethod
    def _terms(text: str) -> set[str]:
        return set(InMemoryRetriever._tokens(text))

    @staticmethod
    def _tokens(text: str) -> list[str]:
        normalized = unicodedata.normalize("NFKC", text)
        normalized = normalized.translate(str.maketrans({"I": "ı", "İ": "i"}))
        normalized = normalized.casefold()
        return [term for term in re.findall(r"\w+", normalized) if len(term) > 2]
