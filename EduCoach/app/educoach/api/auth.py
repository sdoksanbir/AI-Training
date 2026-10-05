"""Authentication boundary contracts for HTTP adapters."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """Authoritative identity resolved from an external credential."""

    subject_id: str
    learner_id: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.subject_id, str) or not self.subject_id.strip():
            raise ValueError("subject_id must be a non-empty string")
        if not isinstance(self.learner_id, UUID):
            raise ValueError("learner_id must be a UUID")


class AuthenticationError(Exception):
    """Base error for rejected or missing authentication credentials."""


class AuthenticationRequired(AuthenticationError):
    """Signal that no authenticated principal could be resolved."""


class AuthResolver(Protocol):
    """Resolve an HTTP credential into an authoritative principal."""

    def resolve(self, credential: str | None) -> AuthenticatedPrincipal: ...
