from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import pytest
from pwdlib import PasswordHash
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session, sessionmaker

from educoach.api import AuthenticationRequired, InvalidCredentials, create_app
from educoach.authentication import (
    AuthenticationPolicy,
    DuplicateLearnerAccountError,
    DuplicateLoginIdentifierError,
    PasswordPolicyError,
    UnknownLearnerError,
)
from educoach.authentication.service import (
    PersistentAuthenticationService,
    generate_opaque_token,
)
from educoach.models import Learner
from educoach.orchestrator import CoachResult
from educoach.persistence import (
    create_schema,
    create_session_factory,
    create_sqlite_engine,
)
from educoach.persistence.datetime_utils import restore_utc
from educoach.persistence.tables import (
    AuthAccountRow,
    AuthSessionRow,
    LearnerRow,
)
from educoach.services import LearnerMemoryService


PASSWORD = "correct horse battery staple"
WRONG_PASSWORD = "incorrect horse battery"


@dataclass
class MutableClock:
    value: datetime

    def __call__(self) -> datetime:
        return self.value


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_sqlite_engine("sqlite+pysqlite:///:memory:")
    create_schema(engine)
    result = create_session_factory(engine)
    yield result
    engine.dispose()


@pytest.fixture
def clock() -> MutableClock:
    return MutableClock(datetime(2026, 10, 6, 12, tzinfo=timezone.utc))


@pytest.fixture
def learner(factory: sessionmaker[Session]) -> Learner:
    result = Learner(display_name="Auth Learner")
    LearnerMemoryService(factory).register_learner(result)
    return result


@pytest.fixture
def auth_service(
    factory: sessionmaker[Session],
    clock: MutableClock,
) -> PersistentAuthenticationService:
    return PersistentAuthenticationService(factory, clock=clock)


def provision(
    service: PersistentAuthenticationService,
    learner: Learner,
    *,
    identifier: str = "learner@example.test",
    password: str = PASSWORD,
):
    return service.provision_account(
        learner.learner_id,
        identifier,
        password,
    )


def account_row(
    factory: sessionmaker[Session],
    learner_id: UUID,
) -> AuthAccountRow:
    with factory() as session:
        row = session.scalar(
            select(AuthAccountRow).where(
                AuthAccountRow.learner_id == str(learner_id)
            )
        )
        assert row is not None
        return row


def session_row(factory: sessionmaker[Session]) -> AuthSessionRow:
    with factory() as session:
        row = session.scalar(select(AuthSessionRow))
        assert row is not None
        return row


def test_existing_learner_account_is_provisioned_with_canonical_login(
    auth_service: PersistentAuthenticationService,
    learner: Learner,
) -> None:
    account = provision(
        auth_service,
        learner,
        identifier="  LEARNER@Example.Test  ",
    )

    assert account.learner_id == learner.learner_id
    assert account.login_identifier == "learner@example.test"
    assert account.is_active is True


def test_create_schema_adds_auth_tables_to_an_existing_database(tmp_path) -> None:
    database_path = tmp_path / "existing.db"
    engine = create_sqlite_engine(
        f"sqlite+pysqlite:///{database_path.as_posix()}"
    )
    LearnerRow.__table__.create(engine)

    assert inspect(engine).get_table_names() == ["learners"]

    create_schema(engine)

    assert {"auth_accounts", "auth_sessions"}.issubset(
        inspect(engine).get_table_names()
    )
    engine.dispose()


def test_unknown_learner_is_rejected(
    auth_service: PersistentAuthenticationService,
) -> None:
    with pytest.raises(UnknownLearnerError):
        auth_service.provision_account(uuid4(), "unknown@example.test", PASSWORD)


def test_duplicate_learner_account_is_rejected(
    auth_service: PersistentAuthenticationService,
    learner: Learner,
) -> None:
    provision(auth_service, learner)

    with pytest.raises(DuplicateLearnerAccountError):
        provision(auth_service, learner, identifier="second@example.test")


def test_duplicate_normalized_login_is_rejected(
    factory: sessionmaker[Session],
    auth_service: PersistentAuthenticationService,
    learner: Learner,
) -> None:
    provision(auth_service, learner, identifier="Login@Example.Test")
    second = Learner(display_name="Second")
    LearnerMemoryService(factory).register_learner(second)

    with pytest.raises(DuplicateLoginIdentifierError):
        provision(
            auth_service,
            second,
            identifier="  login@example.test  ",
        )


def test_password_is_only_persisted_as_verifiable_argon2id_hash(
    factory: sessionmaker[Session],
    auth_service: PersistentAuthenticationService,
    learner: Learner,
) -> None:
    password = "  fifteen chars password  "
    provision(auth_service, learner, password=password)
    row = account_row(factory, learner.learner_id)

    assert row.password_hash != password
    assert password not in row.password_hash
    assert row.password_hash.startswith("$argon2id$")
    assert PasswordHash.recommended().verify(password, row.password_hash)
    assert not PasswordHash.recommended().verify(password.strip(), row.password_hash)


def test_password_policy_supports_15_to_128_characters_without_composition_rules(
    factory: sessionmaker[Session],
    auth_service: PersistentAuthenticationService,
    learner: Learner,
) -> None:
    provision(auth_service, learner, password="a" * 15)
    second = Learner()
    LearnerMemoryService(factory).register_learner(second)
    provision(
        auth_service,
        second,
        identifier="long@example.test",
        password="b" * 128,
    )

    third = Learner()
    LearnerMemoryService(factory).register_learner(third)
    with pytest.raises(PasswordPolicyError):
        provision(
            auth_service,
            third,
            identifier="short@example.test",
            password="c" * 14,
        )


def test_learner_deletion_cascades_account_and_session(
    factory: sessionmaker[Session],
    auth_service: PersistentAuthenticationService,
    learner: Learner,
) -> None:
    provision(auth_service, learner)
    auth_service.authenticate("learner@example.test", PASSWORD)

    with factory() as session, session.begin():
        row = session.get(LearnerRow, str(learner.learner_id))
        assert row is not None
        session.delete(row)

    with factory() as session:
        assert session.scalar(select(AuthAccountRow)) is None
        assert session.scalar(select(AuthSessionRow)) is None


def test_correct_credentials_issue_session(
    auth_service: PersistentAuthenticationService,
    learner: Learner,
    clock: MutableClock,
) -> None:
    provision(auth_service, learner)
    issued = auth_service.authenticate("LEARNER@example.test", PASSWORD)

    assert issued.access_token
    assert issued.expires_at == clock.value + timedelta(hours=12)


def test_wrong_password_and_unknown_identifier_use_same_failure_type(
    auth_service: PersistentAuthenticationService,
    learner: Learner,
) -> None:
    provision(auth_service, learner)

    with pytest.raises(InvalidCredentials) as wrong:
        auth_service.authenticate("learner@example.test", WRONG_PASSWORD)
    with pytest.raises(InvalidCredentials) as unknown:
        auth_service.authenticate("unknown@example.test", WRONG_PASSWORD)

    assert str(wrong.value) == str(unknown.value) == "invalid credentials"


class RecordingPasswordHasher:
    def __init__(self) -> None:
        self.hashes: list[tuple[str, str]] = []
        self.verifications: list[tuple[str, str]] = []

    def hash(self, password: str) -> str:
        result = f"recorded-hash-{len(self.hashes)}"
        self.hashes.append((password, result))
        return result

    def verify(self, password: str, password_hash: str) -> bool:
        self.verifications.append((password, password_hash))
        return False


def test_unknown_identifier_executes_dummy_password_verification(
    factory: sessionmaker[Session],
    clock: MutableClock,
) -> None:
    hasher = RecordingPasswordHasher()
    service = PersistentAuthenticationService(
        factory,
        clock=clock,
        password_hasher=hasher,
    )
    dummy_hash = hasher.hashes[0][1]

    with pytest.raises(InvalidCredentials):
        service.authenticate("missing@example.test", WRONG_PASSWORD)

    assert hasher.verifications == [(WRONG_PASSWORD, dummy_hash)]


def test_inactive_account_cannot_authenticate(
    factory: sessionmaker[Session],
    auth_service: PersistentAuthenticationService,
    learner: Learner,
) -> None:
    provision(auth_service, learner)
    with factory() as session, session.begin():
        row = session.scalar(select(AuthAccountRow))
        assert row is not None
        row.is_active = False

    with pytest.raises(InvalidCredentials):
        auth_service.authenticate("learner@example.test", PASSWORD)


def test_default_tokens_are_unique_and_have_approximately_256_bits_of_entropy() -> None:
    first = generate_opaque_token()
    second = generate_opaque_token()

    assert first != second
    assert len(first) >= 43
    assert len(second) >= 43


def test_raw_token_is_not_persisted_and_sha256_verifier_is(
    factory: sessionmaker[Session],
    auth_service: PersistentAuthenticationService,
    learner: Learner,
) -> None:
    provision(auth_service, learner)
    issued = auth_service.authenticate("learner@example.test", PASSWORD)
    row = session_row(factory)

    assert row.token_hash != issued.access_token
    assert row.token_hash == sha256(issued.access_token.encode()).hexdigest()


def test_valid_bearer_token_resolves_account_owned_principal(
    auth_service: PersistentAuthenticationService,
    learner: Learner,
) -> None:
    account = provision(auth_service, learner)
    issued = auth_service.authenticate("learner@example.test", PASSWORD)

    principal = auth_service.resolve(f"Bearer {issued.access_token}")

    assert principal.subject_id == str(account.account_id)
    assert principal.learner_id == learner.learner_id


@pytest.mark.parametrize(
    "credential",
    [None, "", "Basic token", "Bearer", "Bearer ", " Bearer token", "Bearer  token"],
)
def test_malformed_bearer_credential_is_rejected(
    auth_service: PersistentAuthenticationService,
    credential: str | None,
) -> None:
    with pytest.raises(AuthenticationRequired):
        auth_service.resolve(credential)


def test_unknown_token_is_rejected(
    auth_service: PersistentAuthenticationService,
) -> None:
    with pytest.raises(AuthenticationRequired):
        auth_service.resolve("Bearer unknown-opaque-token")


def test_expired_token_is_rejected(
    auth_service: PersistentAuthenticationService,
    learner: Learner,
    clock: MutableClock,
) -> None:
    provision(auth_service, learner)
    issued = auth_service.authenticate("learner@example.test", PASSWORD)
    clock.value = issued.expires_at

    with pytest.raises(AuthenticationRequired):
        auth_service.resolve(f"Bearer {issued.access_token}")


def test_revoked_token_is_rejected(
    auth_service: PersistentAuthenticationService,
    learner: Learner,
) -> None:
    provision(auth_service, learner)
    issued = auth_service.authenticate("learner@example.test", PASSWORD)
    credential = f"Bearer {issued.access_token}"

    auth_service.revoke(credential)

    with pytest.raises(AuthenticationRequired):
        auth_service.resolve(credential)


def test_failures_are_counted_and_threshold_temporarily_locks_account(
    factory: sessionmaker[Session],
    auth_service: PersistentAuthenticationService,
    learner: Learner,
    clock: MutableClock,
) -> None:
    provision(auth_service, learner)

    for expected in range(1, 6):
        with pytest.raises(InvalidCredentials):
            auth_service.authenticate("learner@example.test", WRONG_PASSWORD)
        row = account_row(factory, learner.learner_id)
        assert row.failed_login_attempts == expected

    assert restore_utc(row.locked_until) == clock.value + timedelta(minutes=15)
    with pytest.raises(InvalidCredentials):
        auth_service.authenticate("learner@example.test", PASSWORD)


def test_login_succeeds_after_lock_expiry(
    auth_service: PersistentAuthenticationService,
    learner: Learner,
    clock: MutableClock,
) -> None:
    provision(auth_service, learner)
    for _ in range(5):
        with pytest.raises(InvalidCredentials):
            auth_service.authenticate("learner@example.test", WRONG_PASSWORD)

    clock.value += timedelta(minutes=15)

    assert auth_service.authenticate("learner@example.test", PASSWORD).access_token


def test_successful_login_resets_failure_state(
    factory: sessionmaker[Session],
    auth_service: PersistentAuthenticationService,
    learner: Learner,
) -> None:
    provision(auth_service, learner)
    for _ in range(2):
        with pytest.raises(InvalidCredentials):
            auth_service.authenticate("learner@example.test", WRONG_PASSWORD)

    auth_service.authenticate("learner@example.test", PASSWORD)
    row = account_row(factory, learner.learner_id)

    assert row.failed_login_attempts == 0
    assert row.locked_until is None


class RecordingOrchestrator:
    def __init__(self) -> None:
        self.calls: list[tuple[UUID, str, UUID | None]] = []

    def health(self) -> bool:
        return True

    def respond(
        self,
        learner_id: UUID,
        message: str,
        *,
        context_id: UUID | None = None,
    ) -> CoachResult:
        self.calls.append((learner_id, message, context_id))
        return CoachResult("Authenticated response", "stub")


def persistent_client(
    service: PersistentAuthenticationService,
    orchestrator: RecordingOrchestrator | None = None,
) -> tuple[TestClient, RecordingOrchestrator]:
    result_orchestrator = orchestrator or RecordingOrchestrator()
    return (
        TestClient(
            create_app(result_orchestrator, service, service),
            raise_server_exceptions=False,
        ),
        result_orchestrator,
    )


def test_http_login_returns_opaque_bearer_token(
    auth_service: PersistentAuthenticationService,
    learner: Learner,
) -> None:
    provision(auth_service, learner)
    client, _ = persistent_client(auth_service)

    response = client.post(
        "/v1/auth/login",
        json={"login_identifier": "learner@example.test", "password": PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]
    assert response.json()["expires_at"]
    assert "password" not in response.text
    assert "token_hash" not in response.text


def test_http_unknown_and_wrong_password_have_identical_public_failure(
    auth_service: PersistentAuthenticationService,
    learner: Learner,
) -> None:
    provision(auth_service, learner)
    client, _ = persistent_client(auth_service)

    wrong = client.post(
        "/v1/auth/login",
        json={
            "login_identifier": "learner@example.test",
            "password": WRONG_PASSWORD,
        },
    )
    unknown = client.post(
        "/v1/auth/login",
        json={
            "login_identifier": "unknown@example.test",
            "password": WRONG_PASSWORD,
        },
    )

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "invalid credentials"}


def test_http_logout_revokes_token_and_coach_rejects_reuse(
    auth_service: PersistentAuthenticationService,
    learner: Learner,
) -> None:
    provision(auth_service, learner)
    client, _ = persistent_client(auth_service)
    login = client.post(
        "/v1/auth/login",
        json={"login_identifier": "learner@example.test", "password": PASSWORD},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    logout = client.post("/v1/auth/logout", headers=headers)
    coach = client.post(
        "/v1/coach/respond",
        headers=headers,
        json={"message": "Merhaba"},
    )

    assert logout.status_code == 204
    assert coach.status_code == 401


def test_persistent_login_end_to_end_uses_only_account_owned_learner(
    factory: sessionmaker[Session],
    auth_service: PersistentAuthenticationService,
    learner: Learner,
) -> None:
    provision(auth_service, learner)
    other = Learner(display_name="Other")
    LearnerMemoryService(factory).register_learner(other)
    client, orchestrator = persistent_client(auth_service)
    login = client.post(
        "/v1/auth/login",
        json={"login_identifier": "learner@example.test", "password": PASSWORD},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    accepted = client.post(
        "/v1/coach/respond",
        headers=headers,
        json={"message": "Merhaba"},
    )
    rejected = client.post(
        "/v1/coach/respond",
        headers=headers,
        json={"message": "Merhaba", "learner_id": str(other.learner_id)},
    )

    assert accepted.status_code == 200
    assert orchestrator.calls == [(learner.learner_id, "Merhaba", None)]
    assert rejected.status_code == 422
