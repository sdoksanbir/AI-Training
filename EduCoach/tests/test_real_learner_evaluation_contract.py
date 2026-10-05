from hashlib import sha256
import json
from pathlib import Path

from pydantic import ValidationError
import pytest

from evaluations.real_learner import (
    CaseFileValidationError,
    RealLearnerEvaluationCase,
    load_validated_cases,
    split_cases,
    write_split,
)


def case_payload(
    index: int = 1,
    *,
    group_index: int | None = None,
    message: str = "Bugünkü çalışma süremi dengeli kullanmak istiyorum.",
) -> dict[str, object]:
    return {
        "case_id": f"RL{index:04d}",
        "source_group_id": f"RG{group_index or index:04d}",
        "source_kind": "real_anonymized",
        "category": "study_planning",
        "program_code": "yks",
        "user_message": message,
        "facts": [
            {
                "kind": "available_minutes",
                "value": 90,
                "source": "learner_reported",
            }
        ],
        "expected_behavior_tags": ["uses_available_time"],
        "forbidden_behavior_tags": ["guarantees_outcome"],
        "privacy_reviewed": True,
        "usage_authorized": True,
    }


def make_case(
    index: int = 1,
    *,
    group_index: int | None = None,
    message: str = "Bugünkü çalışma süremi dengeli kullanmak istiyorum.",
) -> RealLearnerEvaluationCase:
    return RealLearnerEvaluationCase.model_validate(
        case_payload(index, group_index=group_index, message=message)
    )


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_valid_case_is_accepted() -> None:
    case = make_case()

    assert case.case_id == "RL0001"
    assert case.source_group_id == "RG0001"
    assert case.facts[0].value == 90
    assert case.privacy_reviewed is True
    assert case.usage_authorized is True


def test_extra_field_is_rejected() -> None:
    payload = case_payload()
    payload["unexpected"] = "not allowed"

    with pytest.raises(ValidationError):
        RealLearnerEvaluationCase.model_validate(payload)


def test_privacy_reviewed_false_is_rejected() -> None:
    payload = case_payload()
    payload["privacy_reviewed"] = False

    with pytest.raises(ValidationError):
        RealLearnerEvaluationCase.model_validate(payload)


def test_usage_authorized_false_is_rejected() -> None:
    payload = case_payload()
    payload["usage_authorized"] = False

    with pytest.raises(ValidationError):
        RealLearnerEvaluationCase.model_validate(payload)


@pytest.mark.parametrize(
    ("message", "expected_label"),
    [
        (
            "Kayıt 123e4567-e89b-42d3-a456-426614174000 ile bağlantılı.",
            "uuid",
        ),
        ("İletişim adresi learner@example.test.", "email"),
        ("Telefon benzeri değer 0555 123 45 67.", "phone"),
        ("Authorization Bearer abc.def.ghi olarak geldi.", "token"),
        ("Sosyal hesap @sample_handle olarak yazılmış.", "social_handle"),
    ],
)
def test_likely_identifier_leakage_is_rejected(
    message: str,
    expected_label: str,
) -> None:
    with pytest.raises(ValidationError) as error:
        make_case(message=message)

    assert expected_label in str(error.value)


def test_nested_fact_value_is_rejected() -> None:
    payload = case_payload()
    payload["facts"] = [
        {
            "kind": "nested",
            "value": {"not": "allowed"},
            "source": "learner_reported",
        }
    ]

    with pytest.raises(ValidationError):
        RealLearnerEvaluationCase.model_validate(payload)


def test_expected_behavior_tags_cannot_be_empty() -> None:
    payload = case_payload()
    payload["expected_behavior_tags"] = []

    with pytest.raises(ValidationError):
        RealLearnerEvaluationCase.model_validate(payload)


def test_duplicate_case_id_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.jsonl"
    write_jsonl(path, [case_payload(), case_payload()])

    with pytest.raises(CaseFileValidationError, match="duplicate case_id"):
        load_validated_cases(path)


def test_validation_error_does_not_echo_sensitive_content(tmp_path: Path) -> None:
    sensitive = "learner@example.test"
    path = tmp_path / "leak.jsonl"
    write_jsonl(path, [case_payload(message=f"İletişim {sensitive}")])

    with pytest.raises(CaseFileValidationError) as error:
        load_validated_cases(path)

    assert sensitive not in str(error.value)
    assert "user_message" not in str(error.value)


def test_same_source_group_always_uses_same_split() -> None:
    cases = (
        make_case(1, group_index=1),
        make_case(2, group_index=1),
        make_case(3, group_index=2),
    )
    development, final = split_cases(cases, version="v1")
    development_ids = {case.case_id for case in development}
    final_ids = {case.case_id for case in final}

    assert {"RL0001", "RL0002"}.issubset(development_ids) or {
        "RL0001",
        "RL0002",
    }.issubset(final_ids)


def test_input_order_does_not_change_split_or_canonical_order() -> None:
    cases = tuple(make_case(index) for index in range(1, 13))

    first = split_cases(cases, version="v1")
    second = split_cases(tuple(reversed(cases)), version="v1")

    assert first == second
    assert tuple(case.case_id for case in first[0]) == tuple(
        sorted(case.case_id for case in first[0])
    )
    assert tuple(case.case_id for case in first[1]) == tuple(
        sorted(case.case_id for case in first[1])
    )


def test_development_and_final_source_groups_are_disjoint() -> None:
    cases = tuple(make_case(index) for index in range(1, 25))
    development, final = split_cases(cases, version="v1")

    development_groups = {case.source_group_id for case in development}
    final_groups = {case.source_group_id for case in final}

    assert development_groups
    assert final_groups
    assert development_groups.isdisjoint(final_groups)


def test_existing_final_output_rejects_overwrite_before_other_writes(
    tmp_path: Path,
) -> None:
    final_path = tmp_path / "final.jsonl"
    final_path.write_text("existing final unseen\n", encoding="utf-8")
    development_path = tmp_path / "development.jsonl"
    manifest_path = tmp_path / "manifest.json"

    with pytest.raises(FileExistsError, match="new dataset version"):
        write_split(
            (make_case(),),
            version="v1",
            development_path=development_path,
            final_path=final_path,
            manifest_path=manifest_path,
        )

    assert final_path.read_text(encoding="utf-8") == "existing final unseen\n"
    assert not development_path.exists()
    assert not manifest_path.exists()


def test_manifest_hashes_and_outputs_are_deterministic(tmp_path: Path) -> None:
    cases = tuple(make_case(index) for index in range(1, 13))
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"

    first = write_split(
        cases,
        version="v1",
        development_path=first_dir / "development.jsonl",
        final_path=first_dir / "final.jsonl",
        manifest_path=first_dir / "manifest.json",
    )
    second = write_split(
        tuple(reversed(cases)),
        version="v1",
        development_path=second_dir / "development.jsonl",
        final_path=second_dir / "final.jsonl",
        manifest_path=second_dir / "manifest.json",
    )

    first_development = (first_dir / "development.jsonl").read_bytes()
    first_final = (first_dir / "final.jsonl").read_bytes()
    assert first == second
    assert first_development == (second_dir / "development.jsonl").read_bytes()
    assert first_final == (second_dir / "final.jsonl").read_bytes()
    assert first.development_sha256 == sha256(first_development).hexdigest()
    assert first.final_sha256 == sha256(first_final).hexdigest()
    assert first.input_case_count == 12
    assert first.source_group_count == 12
