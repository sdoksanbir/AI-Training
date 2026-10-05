"""Persistent authentication domain contracts kept outside Learner Memory."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuthenticationPolicy:
    """Central session, password, and account lockout policy."""

    session_ttl: timedelta = timedelta(hours=12)
    failed_attempt_limit: int = 5
    lockout_duration: timedelta = timedelta(minutes=15)
    minimum_password_length: int = 15
    maximum_password_length: int = 128

    def __post_init__(self) -> None:
        if self.session_ttl <= timedelta(0):
            raise ValueError("session_ttl must be positive")
        if self.failed_attempt_limit < 1:
            raise ValueError("failed_attempt_limit must be at least one")
        if self.lockout_duration <= timedelta(0):
            raise ValueError("lockout_duration must be positive")
        if self.minimum_password_length < 15:
            raise ValueError("minimum_password_length cannot be below 15")
        if self.maximum_password_length < 64:
            raise ValueError("maximum_password_length cannot be below 64")
        if self.maximum_password_length < self.minimum_password_length:
            raise ValueError("maximum password length must cover the minimum")


@dataclass(frozen=True, slots=True)
class AuthAccount:
    account_id: UUID
    learner_id: UUID
    login_identifier: str
    password_hash: str
    is_active: bool
    failed_login_attempts: int
    locked_until: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class AuthSession:
    session_id: UUID
    account_id: UUID
    token_hash: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None


class AccountProvisioningError(ValueError):
    """Base error for rejected account provisioning."""


class UnknownLearnerError(AccountProvisioningError):
    """The requested learner does not exist."""


class DuplicateLearnerAccountError(AccountProvisioningError):
    """The learner already owns an authentication account."""


class DuplicateLoginIdentifierError(AccountProvisioningError):
    """The canonical login identifier is already assigned."""


class PasswordPolicyError(AccountProvisioningError):
    """The password does not satisfy the bounded length policy."""
