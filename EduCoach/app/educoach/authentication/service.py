"""Persistent opaque-session authentication service."""

from collections.abc import Callable
from datetime import datetime, timezone
import hashlib
import secrets
import unicodedata
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from educoach.api import (
    AuthenticatedPrincipal,
    AuthenticationRequired,
    InvalidCredentials,
    IssuedCredential,
)
from educoach.repositories import AuthRepository, LearnerRepository

from .models import (
    AuthAccount,
    AuthenticationPolicy,
    AuthSession,
    DuplicateLearnerAccountError,
    DuplicateLoginIdentifierError,
    PasswordPolicyError,
    UnknownLearnerError,
)
from .passwords import Argon2PasswordHasher, PasswordHasher


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_opaque_token() -> str:
    """Generate approximately 256 bits of CSPRNG session-token entropy."""

    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    """Create the persistent verifier for a high-entropy opaque token."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_login_identifier(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("login_identifier must be a string")
    normalized = unicodedata.normalize("NFKC", value.strip()).casefold()
    if not normalized:
        raise ValueError("login_identifier cannot be empty")
    if len(normalized) > 320:
        raise ValueError("login_identifier is too long")
    return normalized


class PersistentAuthenticationService:
    """Provision accounts and manage revocable persistent login sessions."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        policy: AuthenticationPolicy | None = None,
        password_hasher: PasswordHasher | None = None,
        clock: Callable[[], datetime] = utc_now,
        token_factory: Callable[[], str] = generate_opaque_token,
    ) -> None:
        self.session_factory = session_factory
        self.policy = policy or AuthenticationPolicy()
        self.password_hasher = password_hasher or Argon2PasswordHasher()
        self.clock = clock
        self.token_factory = token_factory
        self._dummy_password_hash = self.password_hasher.hash(
            secrets.token_urlsafe(32)
        )

    def provision_account(
        self,
        learner_id: UUID,
        login_identifier: str,
        password: str,
    ) -> AuthAccount:
        canonical_identifier = normalize_login_identifier(login_identifier)
        self._validate_new_password(password)
        now = self._now()

        with self.session_factory() as session:
            repository = AuthRepository(session)
            with session.begin():
                if LearnerRepository(session).get_learner(learner_id) is None:
                    raise UnknownLearnerError("learner does not exist")
                if repository.get_account_by_learner(learner_id) is not None:
                    raise DuplicateLearnerAccountError(
                        "learner already has an authentication account"
                    )
                if repository.get_account_by_login(canonical_identifier) is not None:
                    raise DuplicateLoginIdentifierError(
                        "login identifier is already assigned"
                    )

                account = AuthAccount(
                    account_id=uuid4(),
                    learner_id=learner_id,
                    login_identifier=canonical_identifier,
                    password_hash=self.password_hasher.hash(password),
                    is_active=True,
                    failed_login_attempts=0,
                    locked_until=None,
                    created_at=now,
                    updated_at=now,
                )
                repository.add_account(account)
        return account

    def authenticate(
        self,
        login_identifier: str,
        password: str,
    ) -> IssuedCredential:
        try:
            canonical_identifier = normalize_login_identifier(login_identifier)
        except ValueError:
            canonical_identifier = None

        valid_password_shape = self._password_has_valid_shape(password)
        password_for_verification = password if valid_password_shape else ""
        now = self._now()
        issued_credential: IssuedCredential | None = None
        authentication_failed = False

        with self.session_factory() as session:
            repository = AuthRepository(session)
            with session.begin():
                account = (
                    repository.get_account_by_login(canonical_identifier)
                    if canonical_identifier is not None
                    else None
                )
                verification_hash = (
                    account.password_hash
                    if account is not None and valid_password_shape
                    else self._dummy_password_hash
                )
                password_matches = self._verify_password(
                    password_for_verification,
                    verification_hash,
                )

                if account is None:
                    authentication_failed = True
                else:
                    lock_is_active = (
                        account.locked_until is not None
                        and account.locked_until > now
                    )
                    expired_lock = (
                        account.locked_until is not None
                        and account.locked_until <= now
                    )
                    if lock_is_active or not account.is_active:
                        authentication_failed = True
                    elif not password_matches or not valid_password_shape:
                        previous_failures = (
                            0 if expired_lock else account.failed_login_attempts
                        )
                        failed_attempts = previous_failures + 1
                        locked_until = (
                            now + self.policy.lockout_duration
                            if failed_attempts >= self.policy.failed_attempt_limit
                            else None
                        )
                        repository.set_login_failure_state(
                            account.account_id,
                            failed_attempts=failed_attempts,
                            locked_until=locked_until,
                            updated_at=now,
                        )
                        authentication_failed = True
                    else:
                        repository.reset_login_failure_state(
                            account.account_id,
                            updated_at=now,
                        )
                        issued_credential = self._issue_session(
                            repository,
                            account.account_id,
                            now,
                        )

        if authentication_failed or issued_credential is None:
            raise InvalidCredentials("invalid credentials")
        return issued_credential

    def resolve(self, credential: str | None) -> AuthenticatedPrincipal:
        token = self._parse_bearer_credential(credential)
        token_hash = hash_opaque_token(token)
        now = self._now()

        with self.session_factory() as session:
            repository = AuthRepository(session)
            auth_session = repository.get_session_by_token_hash(token_hash)
            account = self._validate_session(repository, auth_session, now)
            learner = LearnerRepository(session).get_learner(account.learner_id)
            if learner is None or learner.learner_id != account.learner_id:
                raise AuthenticationRequired("authentication required")
            return AuthenticatedPrincipal(
                subject_id=str(account.account_id),
                learner_id=account.learner_id,
            )

    def revoke(self, credential: str | None) -> None:
        token = self._parse_bearer_credential(credential)
        token_hash = hash_opaque_token(token)
        now = self._now()

        with self.session_factory() as session:
            repository = AuthRepository(session)
            with session.begin():
                auth_session = repository.get_session_by_token_hash(token_hash)
                account = self._validate_session(repository, auth_session, now)
                learner = LearnerRepository(session).get_learner(
                    account.learner_id
                )
                if learner is None or learner.learner_id != account.learner_id:
                    raise AuthenticationRequired("authentication required")
                repository.revoke_session(
                    auth_session.session_id,
                    revoked_at=now,
                )

    def _issue_session(
        self,
        repository: AuthRepository,
        account_id: UUID,
        now: datetime,
    ) -> IssuedCredential:
        raw_token = self.token_factory()
        if not isinstance(raw_token, str) or not raw_token:
            raise RuntimeError("token factory returned an invalid token")
        expires_at = now + self.policy.session_ttl
        repository.add_session(
            AuthSession(
                session_id=uuid4(),
                account_id=account_id,
                token_hash=hash_opaque_token(raw_token),
                created_at=now,
                expires_at=expires_at,
                revoked_at=None,
            )
        )
        return IssuedCredential(
            access_token=raw_token,
            expires_at=expires_at,
        )

    def _validate_session(
        self,
        repository: AuthRepository,
        auth_session: AuthSession | None,
        now: datetime,
    ) -> AuthAccount:
        if (
            auth_session is None
            or auth_session.revoked_at is not None
            or auth_session.expires_at <= now
        ):
            raise AuthenticationRequired("authentication required")
        account = repository.get_account_by_id(auth_session.account_id)
        if account is None or not account.is_active:
            raise AuthenticationRequired("authentication required")
        return account

    def _validate_new_password(self, password: str) -> None:
        if not self._password_has_valid_shape(password):
            raise PasswordPolicyError(
                "password length must be between "
                f"{self.policy.minimum_password_length} and "
                f"{self.policy.maximum_password_length} characters"
            )

    def _password_has_valid_shape(self, password: object) -> bool:
        return (
            isinstance(password, str)
            and self.policy.minimum_password_length
            <= len(password)
            <= self.policy.maximum_password_length
        )

    def _verify_password(self, password: str, password_hash: str) -> bool:
        try:
            return self.password_hasher.verify(password, password_hash)
        except Exception:
            return False

    def _now(self) -> datetime:
        value = self.clock()
        if value.tzinfo is None:
            raise ValueError("authentication clock must be timezone-aware")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _parse_bearer_credential(credential: str | None) -> str:
        if not isinstance(credential, str):
            raise AuthenticationRequired("authentication required")
        parts = credential.split(" ")
        if (
            len(parts) != 2
            or parts[0].casefold() != "bearer"
            or not parts[1]
            or any(character.isspace() for character in parts[1])
        ):
            raise AuthenticationRequired("authentication required")
        return parts[1]
