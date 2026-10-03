from datetime import date

import pytest
from pydantic import ValidationError

from educoach.models import ContextType
from educoach.specialties import SpecialtyProfile


CONTENT_FIELDS = (
    "capabilities", "taxonomy", "assessment_schema", "goal_schema",
    "planning_policy", "rag_policy", "rules", "validators",
    "prompt_context", "terminology",
)


def make_profile(**overrides) -> SpecialtyProfile:
    values = {
        "profile_code": "school_7",
        "profile_family": ContextType.SCHOOL,
        "display_name": "School 7",
        "profile_version": 1,
    }
    return SpecialtyProfile(**(values | overrides))


def test_minimum_valid_profile() -> None:
    profile = make_profile()
    assert profile.profile_family is ContextType.SCHOOL
    assert profile.status == "active"
    assert profile.effective_from is None
    assert profile.effective_until is None


@pytest.mark.parametrize("field", ["profile_code", "display_name"])
@pytest.mark.parametrize("value", ["", " \t\n"])
def test_required_text_cannot_be_blank(field, value) -> None:
    with pytest.raises(ValidationError):
        make_profile(**{field: value})


def test_required_text_is_trimmed() -> None:
    profile = make_profile(profile_code=" school_7 ", display_name=" School 7 ")
    assert profile.profile_code == "school_7"
    assert profile.display_name == "School 7"


@pytest.mark.parametrize("version", [0, -1])
def test_version_must_be_positive(version) -> None:
    with pytest.raises(ValidationError):
        make_profile(profile_version=version)


def test_reversed_effective_dates_are_rejected() -> None:
    with pytest.raises(ValidationError):
        make_profile(effective_from=date(2026, 10, 3), effective_until=date(2026, 10, 2))


@pytest.mark.parametrize("end", [date(2026, 10, 3), date(2026, 10, 4), None])
def test_valid_effective_date_ranges(end) -> None:
    assert make_profile(effective_from=date(2026, 10, 3), effective_until=end)


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_profile(profile_id="unknown")


def test_unknown_family_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_profile(profile_family="unknown")


def test_undocumented_status_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_profile(status="inactive")


@pytest.mark.parametrize("field", CONTENT_FIELDS)
def test_content_defaults_are_independent(field) -> None:
    first, second = make_profile(), make_profile()
    getattr(first, field)["example"] = ["value"]
    assert getattr(second, field) == {}


@pytest.mark.parametrize("code,family", [
    ("school_7", ContextType.SCHOOL),
    ("yks", ContextType.ENTRANCE_EXAM),
    ("ales", ContextType.ACADEMIC_EXAM),
    ("general_english", ContextType.LANGUAGE_LEARNING),
])
def test_representative_profile_codes(code, family) -> None:
    profile = make_profile(profile_code=code, profile_family=family)
    assert profile.profile_code == code
    assert profile.profile_family is family


def test_content_accepts_json_shapes_and_round_trips() -> None:
    profile = make_profile(
        taxonomy="curriculum.example",
        rules=["example"],
        capabilities={"example": True, "nested": [1, None]},
        prompt_context="Example context",
    )
    assert SpecialtyProfile.model_validate_json(profile.model_dump_json()) == profile


def test_content_rejects_non_json_objects() -> None:
    with pytest.raises(ValidationError):
        make_profile(rules={"example": object()})
