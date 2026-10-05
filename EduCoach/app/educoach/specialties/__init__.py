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
from .routing_terminology import (
    ContextRoutingTerminology,
    get_context_routing_terminology,
)

__all__ = [
    "AmbiguousSpecialtyProfileError",
    "create_builtin_specialty_registry",
    "ContextRoutingTerminology",
    "DuplicateSpecialtyProfileError",
    "load_builtin_profile",
    "load_builtin_profiles",
    "load_specialty_profile",
    "get_context_routing_terminology",
    "parse_specialty_profile_json",
    "SpecialtyProfile",
    "SpecialtyProfileFamilyMismatchError",
    "SpecialtyProfileNotFoundError",
    "SpecialtyProfileRegistry",
    "SpecialtyProfileRegistryError",
]
