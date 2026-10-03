import json
from json import JSONDecodeError
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from educoach.models import ContextType, LearningContext
from educoach.specialties import (
    SpecialtyProfile,
    SpecialtyProfileRegistry,
    create_builtin_specialty_registry,
    load_builtin_profile,
    load_builtin_profiles,
    load_specialty_profile,
    parse_specialty_profile_json,
)


EXPECTED_FAMILIES = {
    "ales": ContextType.ACADEMIC_EXAM,
    "general_english": ContextType.LANGUAGE_LEARNING,
    "school_7": ContextType.SCHOOL,
    "yks": ContextType.ENTRANCE_EXAM,
}


@pytest.mark.parametrize("profile_code", EXPECTED_FAMILIES)
def test_builtin_profile_can_be_loaded(profile_code: str) -> None:
    profile = load_builtin_profile(profile_code)

    assert profile.profile_code == profile_code
    assert profile.profile_family is EXPECTED_FAMILIES[profile_code]


def test_builtin_profile_set_is_exact_and_deterministic() -> None:
    profiles = load_builtin_profiles()

    assert [profile.profile_code for profile in profiles] == [
        "ales",
        "general_english",
        "school_7",
        "yks",
    ]


def test_builtin_profiles_are_domain_models() -> None:
    assert all(
        isinstance(profile, SpecialtyProfile)
        for profile in load_builtin_profiles()
    )


def test_builtin_profiles_can_populate_one_registry() -> None:
    registry = SpecialtyProfileRegistry()
    for profile in load_builtin_profiles():
        registry.register(profile)

    assert len(registry.list_profiles()) == 4


def test_builtin_registry_resolves_matching_context() -> None:
    registry = create_builtin_specialty_registry()
    context = LearningContext(
        learner_id=uuid4(),
        context_type=ContextType.ENTRANCE_EXAM,
        program_code="yks",
    )

    assert registry.resolve_context(context).profile_code == "yks"


def test_builtin_loading_is_independent_of_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    assert {profile.profile_code for profile in load_builtin_profiles()} == set(
        EXPECTED_FAMILIES
    )


def test_malformed_json_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "malformed.json"
    path.write_text('{"profile_code":', encoding="utf-8")

    with pytest.raises(JSONDecodeError):
        load_specialty_profile(path)


def test_profile_can_be_loaded_from_json_file(tmp_path: Path) -> None:
    path = tmp_path / "example.json"
    path.write_text(json.dumps({
        "profile_code": "example",
        "profile_family": "other",
        "display_name": "Example",
        "profile_version": 1,
        "status": "active",
    }), encoding="utf-8")

    assert load_specialty_profile(path).profile_code == "example"


def test_schema_invalid_json_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "invalid-profile.json"
    path.write_text(json.dumps({"profile_code": "incomplete"}), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_specialty_profile(path)


def test_json_data_is_validated_as_specialty_profile() -> None:
    profile = parse_specialty_profile_json(json.dumps({
        "profile_code": "example",
        "profile_family": "other",
        "display_name": "Example",
        "profile_version": 1,
        "status": "active",
    }))

    assert isinstance(profile, SpecialtyProfile)


def test_builtin_loader_does_not_share_mutable_profile_state() -> None:
    first = load_builtin_profile("yks")
    first.capabilities["changed"] = True

    second = load_builtin_profile("yks")
    assert second.capabilities == {}


def test_loader_functions_are_available_from_public_package() -> None:
    assert callable(load_specialty_profile)
    assert callable(load_builtin_profile)
    assert callable(load_builtin_profiles)
    assert callable(create_builtin_specialty_registry)
