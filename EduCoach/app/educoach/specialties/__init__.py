"""Public specialty profile domain contracts."""

from .loader import (
    create_builtin_specialty_registry,
    load_builtin_profile,
    load_builtin_profiles,
    load_specialty_profile,
    parse_specialty_profile_json,
)
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
    "create_builtin_specialty_registry",
    "DuplicateSpecialtyProfileError",
    "load_builtin_profile",
    "load_builtin_profiles",
    "load_specialty_profile",
    "parse_specialty_profile_json",
    "SpecialtyProfile",
    "SpecialtyProfileFamilyMismatchError",
    "SpecialtyProfileNotFoundError",
    "SpecialtyProfileRegistry",
    "SpecialtyProfileRegistryError",
]
