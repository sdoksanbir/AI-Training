"""Public specialty profile domain contracts."""

from .models import SpecialtyProfile
from .registry import (
    AmbiguousSpecialtyProfileError,
    DuplicateSpecialtyProfileError,
    SpecialtyProfileFamilyMismatchError,
    SpecialtyProfileNotFoundError,
    SpecialtyProfileRegistry,
    SpecialtyProfileRegistryError,
)

__all__ = [
    "AmbiguousSpecialtyProfileError",
    "DuplicateSpecialtyProfileError",
    "SpecialtyProfile",
    "SpecialtyProfileFamilyMismatchError",
    "SpecialtyProfileNotFoundError",
    "SpecialtyProfileRegistry",
    "SpecialtyProfileRegistryError",
]
