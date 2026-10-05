"""Shared response segmentation for repetition detection and deterministic repair."""

from dataclasses import dataclass
import re
import unicodedata


_SEGMENT_SEPARATOR = re.compile(r"([.!?\n]+)")
_MIN_MEANINGFUL_SEGMENT_LENGTH = 12
_MIN_REPETITION_RUN_LENGTH = 3


@dataclass(frozen=True)
class ResponseSegment:
    content: str
    separator: str
    normalized: str

    def render(self) -> str:
        return self.content + self.separator


def normalize_response_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    ).replace("ı", "i")


def segment_response(text: str) -> tuple[ResponseSegment, ...]:
    parts = _SEGMENT_SEPARATOR.split(text)
    segments: list[ResponseSegment] = []
    for index in range(0, len(parts), 2):
        content = parts[index]
        separator = parts[index + 1] if index + 1 < len(parts) else ""
        if not content and not separator:
            continue
        normalized = re.sub(
            r"\s+",
            " ",
            normalize_response_text(content),
        ).strip()
        segments.append(
            ResponseSegment(
                content=content,
                separator=separator,
                normalized=normalized,
            )
        )
    return tuple(segments)


def repetition_duplicate_segment_indexes(text: str) -> frozenset[int]:
    segments = segment_response(text)
    duplicate_indexes: set[int] = set()
    run_indexes: list[int] = []
    run_value: str | None = None
    for index, segment in enumerate(segments):
        if not segment.normalized:
            continue
        if len(segment.normalized) < _MIN_MEANINGFUL_SEGMENT_LENGTH:
            duplicate_indexes.update(_duplicate_indexes_for_run(run_indexes))
            run_indexes = []
            run_value = None
            continue
        if segment.normalized != run_value:
            duplicate_indexes.update(_duplicate_indexes_for_run(run_indexes))
            run_indexes = [index]
            run_value = segment.normalized
            continue
        run_indexes.append(index)
    duplicate_indexes.update(_duplicate_indexes_for_run(run_indexes))
    return frozenset(duplicate_indexes)


def _duplicate_indexes_for_run(run_indexes: list[int]) -> tuple[int, ...]:
    if len(run_indexes) < _MIN_REPETITION_RUN_LENGTH:
        return ()
    return tuple(run_indexes[1:])
