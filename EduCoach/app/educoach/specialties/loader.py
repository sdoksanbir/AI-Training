"""Load specialty profiles from JSON files and packaged resources."""

import json
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

from .models import SpecialtyProfile
from .registry import SpecialtyProfileRegistry


_BUILTIN_PROFILE_PACKAGE = "educoach.specialties.profiles"


def parse_specialty_profile_json(data: str | bytes | bytearray) -> SpecialtyProfile:
    """Parse JSON data and validate it with the domain model."""

    return SpecialtyProfile.model_validate(json.loads(data))


def load_specialty_profile(path: str | Path) -> SpecialtyProfile:
    """Load one specialty profile from a JSON file."""

    return parse_specialty_profile_json(Path(path).read_text(encoding="utf-8"))


def load_builtin_profile(profile_code: str) -> SpecialtyProfile:
    """Load one packaged profile selected by its resource name."""

    normalized_code = profile_code.strip()
    if not normalized_code:
        raise ValueError("profile_code boş olamaz")

    resource = next(
        (
            candidate
            for candidate in _builtin_profile_resources()
            if Path(candidate.name).stem == normalized_code
        ),
        None,
    )
    if resource is None:
        raise FileNotFoundError(f"Builtin specialty profile not found: {normalized_code}")

    return _load_resource(resource)


def load_builtin_profiles() -> tuple[SpecialtyProfile, ...]:
    """Load all packaged profiles in deterministic code/version order."""

    profiles = [_load_resource(resource) for resource in _builtin_profile_resources()]
    return tuple(
        sorted(
            profiles,
            key=lambda profile: (profile.profile_code, profile.profile_version),
        )
    )


def create_builtin_specialty_registry() -> SpecialtyProfileRegistry:
    """Create a new registry populated from the packaged profiles."""

    registry = SpecialtyProfileRegistry()
    for profile in load_builtin_profiles():
        registry.register(profile)
    return registry


def _builtin_profile_resources() -> tuple[Traversable, ...]:
    package = files(_BUILTIN_PROFILE_PACKAGE)
    return tuple(
        sorted(
            (
                resource
                for resource in package.iterdir()
                if resource.is_file() and resource.name.endswith(".json")
            ),
            key=lambda resource: resource.name,
        )
    )


def _load_resource(resource: Traversable) -> SpecialtyProfile:
    return parse_specialty_profile_json(resource.read_text(encoding="utf-8"))
