from uuid import uuid4

import pytest

from educoach.models import ContextType, LearningContext
from educoach.specialties import (
    AmbiguousSpecialtyProfileError,
    DuplicateSpecialtyProfileError,
    SpecialtyProfile,
    SpecialtyProfileFamilyMismatchError,
    SpecialtyProfileNotFoundError,
    SpecialtyProfileRegistry,
)


def make_profile(
    code: str = "yks",
    family: ContextType = ContextType.ENTRANCE_EXAM,
    version: int = 1,
) -> SpecialtyProfile:
    return SpecialtyProfile(
        profile_code=code,
        profile_family=family,
        display_name=code,
        profile_version=version,
    )


def make_context(code: str, family: ContextType) -> LearningContext:
    return LearningContext(
        learner_id=uuid4(),
        context_type=family,
        program_code=code,
    )


def test_empty_registry_can_be_created() -> None:
    assert SpecialtyProfileRegistry().list_profiles() == ()


def test_profile_can_be_registered_and_looked_up_exactly() -> None:
    registry = SpecialtyProfileRegistry()
    profile = make_profile()
    registry.register(profile)

    assert registry.get("yks", version=1) == profile


def test_lookup_normalizes_profile_code() -> None:
    registry = SpecialtyProfileRegistry()
    registry.register(make_profile())

    assert registry.get(" yks ", version=1) == make_profile()


@pytest.mark.parametrize("code", ["", " \t\n"])
def test_lookup_rejects_blank_profile_code(code: str) -> None:
    with pytest.raises(ValueError):
        SpecialtyProfileRegistry().get(code)


def test_require_raises_for_unknown_profile() -> None:
    with pytest.raises(SpecialtyProfileNotFoundError):
        SpecialtyProfileRegistry().require("unknown")


def test_duplicate_code_and_version_cannot_be_registered() -> None:
    registry = SpecialtyProfileRegistry()
    registry.register(make_profile())

    with pytest.raises(DuplicateSpecialtyProfileError):
        registry.register(make_profile())


def test_different_versions_of_same_code_can_be_registered() -> None:
    registry = SpecialtyProfileRegistry()
    registry.register(make_profile(version=1))
    registry.register(make_profile(version=2))

    assert registry.get("yks", version=1) == make_profile(version=1)
    assert registry.get("yks", version=2) == make_profile(version=2)


def test_single_version_can_be_resolved_without_version() -> None:
    registry = SpecialtyProfileRegistry()
    profile = make_profile()
    registry.register(profile)

    assert registry.get("yks") == profile
    assert registry.require("yks") == profile


def test_multiple_versions_are_ambiguous_without_version() -> None:
    registry = SpecialtyProfileRegistry()
    registry.register(make_profile(version=1))
    registry.register(make_profile(version=2))

    with pytest.raises(AmbiguousSpecialtyProfileError):
        registry.get("yks")


def test_list_profiles_is_deterministic() -> None:
    registry = SpecialtyProfileRegistry()
    registry.register(make_profile("yks", version=2))
    registry.register(make_profile("school_7", ContextType.SCHOOL))
    registry.register(make_profile("yks", version=1))

    assert [
        (profile.profile_code, profile.profile_version)
        for profile in registry.list_profiles()
    ] == [("school_7", 1), ("yks", 1), ("yks", 2)]


def test_context_is_resolved_by_program_code_and_matching_family() -> None:
    registry = SpecialtyProfileRegistry()
    profile = make_profile()
    registry.register(profile)

    context = make_context("yks", ContextType.ENTRANCE_EXAM)
    assert registry.resolve_context(context) == profile


def test_context_family_mismatch_is_rejected() -> None:
    registry = SpecialtyProfileRegistry()
    registry.register(make_profile())

    context = make_context("yks", ContextType.SCHOOL)
    with pytest.raises(SpecialtyProfileFamilyMismatchError):
        registry.resolve_context(context)


def test_unknown_context_program_code_raises_not_found() -> None:
    context = make_context("unknown", ContextType.OTHER)

    with pytest.raises(SpecialtyProfileNotFoundError):
        SpecialtyProfileRegistry().resolve_context(context)


def test_representative_profiles_can_coexist() -> None:
    registry = SpecialtyProfileRegistry()
    profiles = (
        make_profile("school_7", ContextType.SCHOOL),
        make_profile("yks", ContextType.ENTRANCE_EXAM),
        make_profile("ales", ContextType.ACADEMIC_EXAM),
        make_profile("general_english", ContextType.LANGUAGE_LEARNING),
    )
    for profile in profiles:
        registry.register(profile)

    assert {
        (profile.profile_code, profile.profile_version)
        for profile in registry.list_profiles()
    } == {
        (profile.profile_code, profile.profile_version)
        for profile in profiles
    }


def test_two_contexts_resolve_independently() -> None:
    registry = SpecialtyProfileRegistry()
    school = make_profile("school_11", ContextType.SCHOOL)
    exam = make_profile("yks", ContextType.ENTRANCE_EXAM)
    registry.register(school)
    registry.register(exam)

    assert registry.resolve_context(
        make_context("school_11", ContextType.SCHOOL)
    ) == school
    assert registry.resolve_context(
        make_context("yks", ContextType.ENTRANCE_EXAM)
    ) == exam


def test_callers_cannot_mutate_registry_contents() -> None:
    registry = SpecialtyProfileRegistry()
    source = make_profile()
    registry.register(source)

    source.display_name = "Changed source"
    looked_up = registry.require("yks")
    looked_up.display_name = "Changed lookup"
    listed = registry.list_profiles()
    listed[0].display_name = "Changed list"

    assert registry.require("yks").display_name == "yks"
