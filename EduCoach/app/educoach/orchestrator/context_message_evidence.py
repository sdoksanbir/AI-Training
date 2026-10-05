"""Deterministic message evidence for later context selection."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from educoach.models import ContextStatus
from educoach.services import LearnerMemorySnapshot
from educoach.specialties import SpecialtyProfileRegistry
from educoach.specialties.routing_terminology import (
    get_context_routing_terminology,
    normalize_context_routing_text,
)


class MessageContextEvidenceStatus(StrEnum):
    NONE = "none"
    CONSISTENT = "consistent"
    CONFLICTING = "conflicting"


@dataclass(frozen=True)
class ContextMessageMatch:
    context_id: UUID
    matched_explicit_terms: tuple[str, ...] = ()
    matched_support_terms: tuple[str, ...] = ()
    matched_explicit_phrases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.context_id, UUID):
            raise ValueError("context_id must be a UUID")

        collections = (
            self.matched_explicit_terms,
            self.matched_support_terms,
            self.matched_explicit_phrases,
        )
        for values in collections:
            if not isinstance(values, tuple):
                raise ValueError("matched signal collections must be tuples")
            if any(not isinstance(value, str) or not value for value in values):
                raise ValueError("matched signals must be non-empty strings")
            if any(normalize_context_routing_text(value) != value for value in values):
                raise ValueError("matched signals must be normalized")
            if len(set(values)) != len(values):
                raise ValueError("matched signals cannot contain duplicates")
            if values != tuple(sorted(values)):
                raise ValueError("matched signals must use canonical order")

        if any(" " in value for value in self.matched_explicit_terms):
            raise ValueError("matched explicit terms must be single terms")
        if any(" " in value for value in self.matched_support_terms):
            raise ValueError("matched support terms must be single terms")
        if set(self.matched_explicit_terms) & set(self.matched_support_terms):
            raise ValueError(
                "matched explicit terms and support terms must be disjoint"
            )
        if any(" " not in value for value in self.matched_explicit_phrases):
            raise ValueError("matched explicit phrases must be multi-word phrases")

        has_phrase = bool(self.matched_explicit_phrases)
        has_term_pair = bool(
            self.matched_explicit_terms and self.matched_support_terms
        )
        if not (has_phrase or has_term_pair):
            raise ValueError("a context match must satisfy the candidate policy")


@dataclass(frozen=True)
class MessageContextEvidence:
    status: MessageContextEvidenceStatus
    candidate_context_ids: tuple[UUID, ...]
    matches: tuple[ContextMessageMatch, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.status, MessageContextEvidenceStatus):
            raise ValueError("status must be a MessageContextEvidenceStatus")
        if not isinstance(self.candidate_context_ids, tuple):
            raise ValueError("candidate_context_ids must be a tuple")
        if any(not isinstance(value, UUID) for value in self.candidate_context_ids):
            raise ValueError("candidate_context_ids must contain UUID values")
        if len(set(self.candidate_context_ids)) != len(self.candidate_context_ids):
            raise ValueError("candidate_context_ids cannot contain duplicates")
        if self.candidate_context_ids != tuple(
            sorted(self.candidate_context_ids, key=str)
        ):
            raise ValueError("candidate_context_ids must use canonical order")

        if not isinstance(self.matches, tuple):
            raise ValueError("matches must be a tuple")
        if any(not isinstance(match, ContextMessageMatch) for match in self.matches):
            raise ValueError("matches must contain ContextMessageMatch values")
        match_ids = tuple(match.context_id for match in self.matches)
        if match_ids != tuple(sorted(match_ids, key=str)):
            raise ValueError("matches must use canonical context order")
        if len(set(match_ids)) != len(match_ids):
            raise ValueError("matches cannot repeat a context")
        if match_ids != self.candidate_context_ids:
            raise ValueError("candidate_context_ids must match context matches")

        expected_status = (
            MessageContextEvidenceStatus.NONE
            if not match_ids
            else MessageContextEvidenceStatus.CONSISTENT
            if len(match_ids) == 1
            else MessageContextEvidenceStatus.CONFLICTING
        )
        if self.status != expected_status:
            raise ValueError("status does not match candidate contexts")


def _phrase_is_present(message: str, phrase: str) -> bool:
    return f" {phrase} " in f" {message} "


def project_message_context_evidence(
    message: str,
    snapshot: LearnerMemorySnapshot,
    registry: SpecialtyProfileRegistry,
) -> MessageContextEvidence:
    """Project explicit message signals for every authoritative active context."""

    if not isinstance(message, str):
        raise ValueError("message must be a string")

    learner_id = snapshot.learner.learner_id
    contexts_by_id = {}
    for context in snapshot.contexts:
        if context.context_id in contexts_by_id:
            raise ValueError("snapshot cannot contain duplicate context_id values")
        if context.learner_id != learner_id:
            raise ValueError("context must belong to the snapshot learner")
        contexts_by_id[context.context_id] = context

    normalized_message = normalize_context_routing_text(message)
    message_terms = set(normalized_message.split())
    matches: list[ContextMessageMatch] = []

    for context in sorted(contexts_by_id.values(), key=lambda item: str(item.context_id)):
        if context.status != ContextStatus.ACTIVE:
            continue

        profile = registry.resolve_context(context)
        terminology = get_context_routing_terminology(profile)
        explicit_terms = tuple(
            term for term in terminology.explicit_terms if term in message_terms
        )
        support_terms = tuple(
            term for term in terminology.support_terms if term in message_terms
        )
        explicit_phrases = tuple(
            phrase
            for phrase in terminology.explicit_phrases
            if _phrase_is_present(normalized_message, phrase)
        )

        if explicit_phrases or (explicit_terms and support_terms):
            matches.append(
                ContextMessageMatch(
                    context_id=context.context_id,
                    matched_explicit_terms=explicit_terms,
                    matched_support_terms=support_terms,
                    matched_explicit_phrases=explicit_phrases,
                )
            )

    matches_tuple = tuple(matches)
    candidate_context_ids = tuple(match.context_id for match in matches_tuple)
    status = (
        MessageContextEvidenceStatus.NONE
        if not matches_tuple
        else MessageContextEvidenceStatus.CONSISTENT
        if len(matches_tuple) == 1
        else MessageContextEvidenceStatus.CONFLICTING
    )
    return MessageContextEvidence(status, candidate_context_ids, matches_tuple)
