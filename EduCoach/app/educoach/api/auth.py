"""Authentication boundary contracts for HTTP adapters."""

from dataclasses import dataclass
from datetime import datetime
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


class InvalidCredentials(AuthenticationError):
    """Signal that login credentials cannot be authenticated."""


@dataclass(frozen=True)
class IssuedCredential:
    """Opaque access credential returned by a login/session service."""

    access_token: str
    expires_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.access_token, str) or not self.access_token:
            raise ValueError("access_token must be a non-empty string")
        if self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")


class AuthResolver(Protocol):
    """Resolve an HTTP credential into an authoritative principal."""

    def resolve(self, credential: str | None) -> AuthenticatedPrincipal: ...


class LoginSessionService(Protocol):
    """Authenticate credentials and revoke opaque access sessions."""

    def authenticate(
        self,
        login_identifier: str,
        password: str,
    ) -> IssuedCredential: ...

    def revoke(self, credential: str | None) -> None: ...
