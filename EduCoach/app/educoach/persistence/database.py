"""SQLite engine and session configuration."""

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .base import Base


def _enable_sqlite_foreign_keys(
    dbapi_connection: object,
    connection_record: object,
) -> None:
    del connection_record

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_sqlite_engine(
    url: str = "sqlite+pysqlite:///educoach.db",
) -> Engine:
    options: dict[str, object] = {}

    if ":memory:" in url:
        options["connect_args"] = {"check_same_thread": False}
        options["poolclass"] = StaticPool

    engine = create_engine(url, **options)

    event.listen(
        engine,
        "connect",
        _enable_sqlite_foreign_keys,
    )

    return engine


def create_session_factory(
    engine: Engine,
) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
    )


def create_schema(engine: Engine) -> None:
    # Importing tables registers them in Base.metadata.
    from . import tables  # noqa: F401

    Base.metadata.create_all(engine)
