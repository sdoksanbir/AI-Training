import json
from pathlib import Path
import re

import pytest

from educoach.llm import FakeLLMProvider, LLMProvider
from educoach.repositories.auth import AuthRepository
from evaluations.real_learner import (
    CaseFileValidationError,
    DuplicateCaseError,
    ExecutionStatus,
    PrivatePathError,
    ProviderUnavailableError,
    RealLearnerEvaluationCase,
    load_validated_cases,
    run_development_evaluation,
    validate_run_id,
)
import scripts.run_real_learner_development_evaluation as runner_cli


def case_payload(
    index: int = 1,
    *,
    group_index: int | None = None,
    program_code: str = "yks",
    message: str = "Bugünkü durumumu birlikte değerlendirelim.",
    facts: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "case_id": f"RL{index:04d}",
        "source_group_id": f"RG{group_index or index:04d}",
        "source_kind": "real_anonymized",
        "category": "study_advice",
        "program_code": program_code,
        "user_message": message,
        "facts": facts or [],
        "expected_behavior_tags": ["gives_safe_guidance"],
        "forbidden_behavior_tags": ["guarantees_outcome"],
        "privacy_reviewed": True,
        "usage_authorized": True,
    }


def make_case(
    index: int = 1,
    *,
    group_index: int | None = None,
    program_code: str = "yks",
    message: str = "Bugünkü durumumu birlikte değerlendirelim.",
    facts: list[dict[str, object]] | None = None,
) -> RealLearnerEvaluationCase:
    return RealLearnerEvaluationCase.model_validate(
        case_payload(
            index,
            group_index=group_index,
            program_code=program_code,
            message=message,
            facts=facts,
        )
    )


def run_cases(
    tmp_path: Path,
    cases: tuple[RealLearnerEvaluationCase, ...],
    *,
    provider: LLMProvider | None = None,
    run_id: str = "dev-test",
):
    return run_development_evaluation(
        cases,
        provider or FakeLLMProvider(responder=lambda _: "Hazırım."),
        run_id=run_id,
        private_root=tmp_path / "private",
    )


def learner_id_from_memory(memory_context: str) -> str:
    match = re.search(r"learner_id=UUID\('([^']+)'\)", memory_context)
    assert match is not None
    return match.group(1)


def test_valid_synthetic_case_runs_through_production_orchestrator(
    tmp_path: Path,
) -> None:
    provider = FakeLLMProvider(responder=lambda _: "Hazırım.")

    run = run_cases(tmp_path, (make_case(),), provider=provider)

    assert run.results[0].execution_status is ExecutionStatus.COMPLETED
    assert run.results[0].response_text == "Hazırım."
    assert len(provider.requests) == 1
    assert "Sen EduCoach'sun" in provider.requests[0].system_prompt


def test_invalid_intake_is_rejected_by_existing_validator(tmp_path: Path) -> None:
    raw_message = "RAW-LEARNER-CONTENT"
    payload = case_payload(message=raw_message)
    payload["privacy_reviewed"] = False
    path = tmp_path / "invalid.jsonl"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(CaseFileValidationError) as error:
        load_validated_cases(path)

    assert raw_message not in str(error.value)


def test_same_source_group_reuses_same_evaluation_learner(tmp_path: Path) -> None:
    provider = FakeLLMProvider(responder=lambda _: "Hazırım.")
    cases = (make_case(1, group_index=7), make_case(2, group_index=7))

    run_cases(tmp_path, cases, provider=provider)

    learner_ids = [
        learner_id_from_memory(request.memory_context) for request in provider.requests
    ]
    assert len(learner_ids) == 2
    assert learner_ids[0] == learner_ids[1]


def test_different_source_groups_use_distinct_evaluation_learners(
    tmp_path: Path,
) -> None:
    provider = FakeLLMProvider(responder=lambda _: "Hazırım.")

    run_cases(
        tmp_path,
        (make_case(1, group_index=1), make_case(2, group_index=2)),
        provider=provider,
    )

    learner_ids = {
        learner_id_from_memory(request.memory_context) for request in provider.requests
    }
    assert len(learner_ids) == 2


def test_output_outside_private_boundary_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(PrivatePathError):
        run_development_evaluation(
            (make_case(),),
            FakeLLMProvider(),
            run_id="dev-test",
            private_root=tmp_path / "private",
            output_directory=tmp_path / "outside",
        )


def test_existing_run_is_never_overwritten(tmp_path: Path) -> None:
    private_root = tmp_path / "private"
    existing = private_root / "runs" / "dev-test"
    existing.mkdir(parents=True)
    marker = existing / "marker.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="new run_id"):
        run_development_evaluation(
            (make_case(),),
            FakeLLMProvider(),
            run_id="dev-test",
            private_root=private_root,
        )

    assert marker.read_text(encoding="utf-8") == "keep"


class FailingProvider(LLMProvider):
    def health(self) -> bool:
        return True

    def generate(self, request):
        del request
        raise RuntimeError("RAW-USER-OR-MODEL-SECRET")


def test_provider_call_failure_is_safe_and_does_not_echo_raw_content(
    tmp_path: Path,
) -> None:
    raw_message = "RAW-LEARNER-MESSAGE"

    run = run_cases(
        tmp_path,
        (make_case(message=raw_message),),
        provider=FailingProvider(),
    )

    result = run.results[0]
    assert result.execution_status is ExecutionStatus.FAILED
    assert result.reason_code == "orchestrator_error"
    artifacts = "".join(
        path.read_text(encoding="utf-8")
        for path in run.output_directory.iterdir()
    )
    assert raw_message not in artifacts
    assert "RAW-USER-OR-MODEL-SECRET" not in artifacts


def test_cli_safe_error_does_not_echo_raw_learner_message(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw_message = "RAW-TERMINAL-LEARNER-MESSAGE"
    input_path = tmp_path / "private-input.jsonl"
    input_path.write_text(
        json.dumps(case_payload(message=raw_message), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(runner_cli, "require_private_path", lambda path: path)
    monkeypatch.setattr(
        runner_cli,
        "OllamaProvider",
        lambda model: UnhealthyProvider(),
    )

    exit_code = runner_cli.main(
        [str(input_path), "--run-id", "dev-cli-safe-test", "--model", "fake"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert raw_message not in captured.out
    assert raw_message not in captured.err


def test_unsupported_fact_is_not_materialized_and_is_reported(
    tmp_path: Path,
) -> None:
    provider = FakeLLMProvider(responder=lambda _: "Hazırım.")
    case = make_case(
        facts=[
            {
                "kind": "math_net_approx",
                "value": 123.456,
                "source": "learner_reported",
            }
        ]
    )

    run = run_cases(tmp_path, (case,), provider=provider)

    assert "123.456" not in provider.requests[0].memory_context
    assert run.results[0].unsupported_fact_kinds == ("math_net_approx",)


def test_authoritative_facts_are_materialized_without_generic_storage(
    tmp_path: Path,
) -> None:
    provider = FakeLLMProvider(responder=lambda _: "Hazırım.")
    case = make_case(
        facts=[
            {
                "kind": "education_status",
                "value": "graduate",
                "source": "learner_reported",
            },
            {"kind": "grade_level", "value": 12, "source": "learner_reported"},
            {
                "kind": "study_track",
                "value": "science",
                "source": "learner_reported",
            },
        ]
    )

    run = run_cases(tmp_path, (case,), provider=provider)

    memory = provider.requests[0].memory_context
    assert "graduate" in memory
    assert "grade_level=12" in memory
    assert "track='science'" in memory
    assert run.results[0].unsupported_fact_kinds == ()


@pytest.mark.parametrize("program_code", ["lgs", "school", "unknown"])
def test_program_without_exact_builtin_contract_is_not_run(
    tmp_path: Path,
    program_code: str,
) -> None:
    provider = FakeLLMProvider(responder=lambda _: "must not run")

    run = run_cases(
        tmp_path,
        (make_case(program_code=program_code),),
        provider=provider,
    )

    assert run.results[0].execution_status is ExecutionStatus.NOT_RUN
    assert run.results[0].reason_code == "unsupported_program_code"
    assert provider.requests == []


def test_runtime_learner_uuid_never_enters_result_artifacts(tmp_path: Path) -> None:
    provider = FakeLLMProvider(responder=lambda request: request.memory_context)

    run = run_cases(tmp_path, (make_case(),), provider=provider)

    assert run.results[0].execution_status is ExecutionStatus.FAILED
    assert run.results[0].reason_code == "runtime_identifier_leak"
    artifact_text = "".join(
        path.read_text(encoding="utf-8")
        for path in run.output_directory.iterdir()
    )
    assert re.search(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
        r"[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        artifact_text,
        re.IGNORECASE,
    ) is None


def test_runner_never_creates_authentication_accounts_or_sessions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args, **kwargs):
        del args, kwargs
        raise AssertionError("authentication persistence must not be called")

    monkeypatch.setattr(AuthRepository, "add_account", forbidden)
    monkeypatch.setattr(AuthRepository, "add_session", forbidden)

    run = run_cases(tmp_path, (make_case(),))

    assert run.summary.completed == 1


def test_human_review_starts_unscored_and_has_no_automatic_judge(
    tmp_path: Path,
) -> None:
    run = run_cases(tmp_path, (make_case(),))

    review = run.human_review[0]
    assert review.expected_review is None
    assert review.forbidden_review is None
    assert review.notes is None
    payload = review.model_dump(mode="json")
    assert "judge" not in payload
    assert "score" not in payload


def test_summary_contains_only_aggregate_data(tmp_path: Path) -> None:
    raw_message = "UNIQUE-RAW-LEARNER-MESSAGE"
    response = "UNIQUE-PRIVATE-MODEL-RESPONSE"
    provider = FakeLLMProvider(responder=lambda _: response)

    run = run_cases(
        tmp_path,
        (make_case(message=raw_message),),
        provider=provider,
    )

    summary_text = (run.output_directory / "summary.json").read_text(
        encoding="utf-8"
    )
    assert raw_message not in summary_text
    assert response not in summary_text
    assert set(json.loads(summary_text)) == {
        "run_id",
        "total_cases",
        "completed",
        "not_run",
        "failed",
        "proposal_count",
        "unsupported_fact_kind_count",
    }


def test_study_plan_proposal_is_detected_but_never_persisted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = {
        "response_text": "Planın hazır.",
        "proposal": {
            "title": "Haftalık çalışma planı",
            "plan_type": "weekly",
            "start_date": "2026-10-05",
            "end_date": "2026-10-05",
            "tasks": [
                {
                    "task_date": "2026-10-05",
                    "task_type": "study",
                    "description": "Matematik çalışma",
                    "planned_minutes": 60,
                    "priority": "high",
                    "area_type": "subject",
                    "area_code": "mathematics",
                }
            ],
        },
    }

    def forbidden_write(*args, **kwargs):
        del args, kwargs
        raise AssertionError("proposal must not be persisted")

    monkeypatch.setattr(
        "educoach.services.LearnerMemoryService.save_study_plan",
        forbidden_write,
    )
    provider = FakeLLMProvider(
        responder=lambda _: json.dumps(proposal, ensure_ascii=False)
    )

    run = run_cases(
        tmp_path,
        (make_case(message="Bana haftalık plan yap."),),
        provider=provider,
    )

    assert run.results[0].proposal_present is True
    assert run.summary.proposal_count == 1


class UnhealthyProvider(LLMProvider):
    def health(self) -> bool:
        return False

    def generate(self, request):
        raise AssertionError(request)


def test_provider_unavailable_fails_before_output_creation(tmp_path: Path) -> None:
    private_root = tmp_path / "private"

    with pytest.raises(ProviderUnavailableError, match="unavailable"):
        run_development_evaluation(
            (make_case(),),
            UnhealthyProvider(),
            run_id="dev-test",
            private_root=private_root,
        )

    assert not (private_root / "runs" / "dev-test").exists()


def test_duplicate_case_id_is_rejected_before_generation(tmp_path: Path) -> None:
    provider = FakeLLMProvider()
    case = make_case()

    with pytest.raises(DuplicateCaseError):
        run_cases(tmp_path, (case, case), provider=provider)

    assert provider.requests == []


@pytest.mark.parametrize(
    "run_id",
    ["", "Dev-Run", "../escape", "dev/run", "dev run", "1dev"],
)
def test_run_id_must_be_a_controlled_identifier(run_id: str) -> None:
    with pytest.raises(ValueError, match="controlled"):
        validate_run_id(run_id)


def test_conflicting_group_level_fact_fails_closed_for_whole_group(
    tmp_path: Path,
) -> None:
    first = make_case(
        1,
        group_index=1,
        facts=[
            {
                "kind": "education_status",
                "value": "graduate",
                "source": "learner_reported",
            }
        ],
    )
    second = make_case(
        2,
        group_index=1,
        facts=[
            {
                "kind": "education_status",
                "value": "university",
                "source": "learner_reported",
            }
        ],
    )
    provider = FakeLLMProvider()

    run = run_cases(tmp_path, (first, second), provider=provider)

    assert {result.reason_code for result in run.results} == {
        "conflicting_group_fact"
    }
    assert provider.requests == []
