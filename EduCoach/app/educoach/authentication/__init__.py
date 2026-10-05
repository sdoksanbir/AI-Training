"""Persistent learner authentication and opaque session management."""

from typing import Any

from .models import (
    AuthAccount,
    AuthenticationPolicy,
    AuthSession,
    AccountProvisioningError,
    DuplicateLearnerAccountError,
    DuplicateLoginIdentifierError,
    PasswordPolicyError,
    UnknownLearnerError,
)
from .passwords import Argon2PasswordHasher, PasswordHasher

__all__ = [
    "AccountProvisioningError",
    "Argon2PasswordHasher",
    "AuthAccount",
    "AuthenticationPolicy",
    "AuthSession",
    "DuplicateLearnerAccountError",
    "DuplicateLoginIdentifierError",
    "PasswordHasher",
    "PasswordPolicyError",
    "PersistentAuthenticationService",
    "UnknownLearnerError",
    "generate_opaque_token",
    "hash_opaque_token",
    "normalize_login_identifier",
]


def __getattr__(name: str) -> Any:
    """Load the concrete service lazily to keep core imports acyclic."""

    if name in {
        "PersistentAuthenticationService",
        "generate_opaque_token",
        "hash_opaque_token",
        "normalize_login_identifier",
    }:
        from . import service

        return getattr(service, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
