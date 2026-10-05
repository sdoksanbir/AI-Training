"""Authentication account and opaque session repository."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from educoach.authentication.models import AuthAccount, AuthSession
from educoach.persistence.datetime_utils import restore_utc
from educoach.persistence.tables import AuthAccountRow, AuthSessionRow


class AuthRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_account(self, account: AuthAccount) -> AuthAccount:
        self.session.add(
            AuthAccountRow(
                account_id=str(account.account_id),
                learner_id=str(account.learner_id),
                login_identifier=account.login_identifier,
                password_hash=account.password_hash,
                is_active=account.is_active,
                failed_login_attempts=account.failed_login_attempts,
                locked_until=account.locked_until,
                created_at=account.created_at,
                updated_at=account.updated_at,
            )
        )
        self.session.flush()
        return account

    def get_account_by_id(self, account_id: UUID) -> AuthAccount | None:
        row = self.session.get(AuthAccountRow, str(account_id))
        return self._account_from_row(row) if row is not None else None

    def get_account_by_learner(self, learner_id: UUID) -> AuthAccount | None:
        statement = select(AuthAccountRow).where(
            AuthAccountRow.learner_id == str(learner_id)
        )
        row = self.session.scalar(statement)
        return self._account_from_row(row) if row is not None else None

    def get_account_by_login(self, login_identifier: str) -> AuthAccount | None:
        statement = select(AuthAccountRow).where(
            AuthAccountRow.login_identifier == login_identifier
        )
        row = self.session.scalar(statement)
        return self._account_from_row(row) if row is not None else None

    def set_login_failure_state(
        self,
        account_id: UUID,
        *,
        failed_attempts: int,
        locked_until: datetime | None,
        updated_at: datetime,
    ) -> None:
        row = self._required_account_row(account_id)
        row.failed_login_attempts = failed_attempts
        row.locked_until = locked_until
        row.updated_at = updated_at
        self.session.flush()

    def reset_login_failure_state(
        self,
        account_id: UUID,
        *,
        updated_at: datetime,
    ) -> None:
        self.set_login_failure_state(
            account_id,
            failed_attempts=0,
            locked_until=None,
            updated_at=updated_at,
        )

    def add_session(self, auth_session: AuthSession) -> AuthSession:
        self.session.add(
            AuthSessionRow(
                session_id=str(auth_session.session_id),
                account_id=str(auth_session.account_id),
                token_hash=auth_session.token_hash,
                created_at=auth_session.created_at,
                expires_at=auth_session.expires_at,
                revoked_at=auth_session.revoked_at,
            )
        )
        self.session.flush()
        return auth_session

    def get_session_by_token_hash(self, token_hash: str) -> AuthSession | None:
        statement = select(AuthSessionRow).where(
            AuthSessionRow.token_hash == token_hash
        )
        row = self.session.scalar(statement)
        return self._session_from_row(row) if row is not None else None

    def revoke_session(
        self,
        session_id: UUID,
        *,
        revoked_at: datetime,
    ) -> None:
        row = self.session.get(AuthSessionRow, str(session_id))
        if row is None:
            raise ValueError("authentication session does not exist")
        row.revoked_at = revoked_at
        self.session.flush()

    def _required_account_row(self, account_id: UUID) -> AuthAccountRow:
        row = self.session.get(AuthAccountRow, str(account_id))
        if row is None:
            raise ValueError("authentication account does not exist")
        return row

    @staticmethod
    def _account_from_row(row: AuthAccountRow) -> AuthAccount:
        return AuthAccount(
            account_id=UUID(row.account_id),
            learner_id=UUID(row.learner_id),
            login_identifier=row.login_identifier,
            password_hash=row.password_hash,
            is_active=row.is_active,
            failed_login_attempts=row.failed_login_attempts,
            locked_until=restore_utc(row.locked_until),
            created_at=restore_utc(row.created_at),
            updated_at=restore_utc(row.updated_at),
        )

    @staticmethod
    def _session_from_row(row: AuthSessionRow) -> AuthSession:
        return AuthSession(
            session_id=UUID(row.session_id),
            account_id=UUID(row.account_id),
            token_hash=row.token_hash,
            created_at=restore_utc(row.created_at),
            expires_at=restore_utc(row.expires_at),
            revoked_at=restore_utc(row.revoked_at),
        )
