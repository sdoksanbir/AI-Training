"""Datetime helpers for persistence adapters."""

from datetime import datetime, timezone
from typing import overload


@overload
def restore_utc(value: None) -> None:
    ...


@overload
def restore_utc(value: datetime) -> datetime:
    ...


def restore_utc(
    value: datetime | None,
) -> datetime | None:
    """Restore UTC tzinfo lost by SQLite datetime round-trips."""
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value
