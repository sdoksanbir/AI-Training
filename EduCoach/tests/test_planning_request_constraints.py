from datetime import date
import json
from unittest.mock import Mock

import pytest

from educoach.llm import FakeLLMProvider
from educoach.models import (
    ContextType,
    Learner,
    LearningContext,
    PlanType,
    StudyPlan,
    StudyTask,
    TaskType,
)
from educoach.orchestrator import (
    AvailabilityImplication,
    CoachOrchestrator,
    ConstraintStrength,
    RecurringDayScope,
    ResponseRegenerationExhausted,
    ScheduleAnchorType,
    evaluate_request_subject_limits,
    evaluate_response_proposal_workload,
    extract_daily_workload_claim,
    extract_planning_request_context,
)
from educoach.persistence import (
    create_schema,
    create_session_factory,
    create_sqlite_engine,
)
from educoach.rules import TimeBudgetResolutionStatus, resolve_daily_time_budget
from educoach.services import LearnerMemoryService, LearnerMemorySnapshot
from educoach.writeback import StudyPlanWriteProposal


MONDAY = date(2026, 10, 5)
TUESDAY = date(2026, 10, 6)


def make_snapshot(
    learner: Learner,
    context: LearningContext,
) -> LearnerMemorySnapshot:
    return LearnerMemorySnapshot(
        learner=learner,
        contexts=(context,),
        goals=(),
        availability=(),
        assessments=(),
        assessment_results=(),
        learning_evidence=(),
        study_plans=(),
        study_tasks=(),
        study_sessions=(),
        preferences=(),
        coaching_states=(),
    )


def make_write_proposal(
    learner: Learner,
    context: LearningContext,
    tasks: tuple[tuple[date, int, str, str], ...],
) -> StudyPlanWriteProposal:
    plan = StudyPlan(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        title="Sentetik plan",
        plan_type=PlanType.WEEKLY,
        start_date=min(item[0] for item in tasks),
        end_date=max(item[0] for item in tasks),
    )
    return StudyPlanWriteProposal(
        plan=plan,
        tasks=tuple(
            StudyTask(
                plan_id=plan.plan_id,
                context_id=context.context_id,
                task_date=task_date,
                task_type=TaskType.STUDY,
                description="Sentetik çalışma görevi",
                planned_minutes=minutes,
                area_type=area_type,
                area_code=area_code,
            )
            for task_date, minutes, area_type, area_code in tasks
        ),
    )


def structured_response(
    response_text: str,
    tasks: tuple[tuple[str, int, str, str], ...],
) -> str:
    return json.dumps(
        {
            "response_text": response_text,
            "proposal": {
                "title": "Sentetik plan",
                "plan_type": "weekly",
                "start_date": min(item[0] for item in tasks),
                "end_date": max(item[0] for item in tasks),
                "tasks": [
                    {
                        "task_date": task_date,
                        "task_type": "study",
                        "description": "Sentetik çalışma görevi",
                        "planned_minutes": minutes,
                        "area_type": area_type,
                        "area_code": area_code,
                    }
                    for task_date, minutes, area_type, area_code in tasks
                ],
            },
        },
        ensure_ascii=False,
    )


def make_mock_runtime(response_text: str):
    learner = Learner()
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )
    memory = Mock(spec=LearnerMemoryService)
    memory.get_learner_memory_snapshot.return_value = make_snapshot(
        learner, context
    )
    provider = FakeLLMProvider(responder=lambda _: response_text)
    return CoachOrchestrator(memory, provider), memory, provider, learner


def test_explicit_subject_limit_is_extracted_as_hard_minutes() -> None:
    context = extract_planning_request_context(
        "Matematiğe günde en fazla 2 saat ayırabilirim."
    )

    assert len(context.daily_subject_limits) == 1
    limit = context.daily_subject_limits[0]
    assert (limit.area_type, limit.area_code) == ("subject", "mathematics")
    assert limit.max_minutes_per_day == 120
    assert limit.strength is ConstraintStrength.HARD


@pytest.mark.parametrize(
    ("tasks", "has_violation"),
    [
        (((MONDAY, 120, "subject", "mathematics"),), False),
        (((MONDAY, 121, "subject", "mathematics"),), True),
        (
            (
                (MONDAY, 70, "subject", "mathematics"),
                (MONDAY, 50, "subject", "mathematics"),
            ),
            False,
        ),
        (
            (
                (MONDAY, 70, "subject", "mathematics"),
                (MONDAY, 51, "subject", "mathematics"),
            ),
            True,
        ),
        (
            (
                (MONDAY, 120, "subject", "mathematics"),
                (TUESDAY, 120, "subject", "mathematics"),
                (MONDAY, 180, "subject", "physics"),
            ),
            False,
        ),
    ],
)
def test_subject_limit_sums_only_matching_tasks_per_day(
    tasks: tuple[tuple[date, int, str, str], ...],
    has_violation: bool,
) -> None:
    learner = Learner()
    learning_context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )
    request_context = extract_planning_request_context(
        "Matematiğe günde en fazla 2 saat ayırabilirim."
    )
    proposal = make_write_proposal(learner, learning_context, tasks)

    violations = evaluate_request_subject_limits(request_context, proposal)

    assert bool(violations) is has_violation
    if has_violation:
        assert violations[0].rule_id == "PLAN_REQUEST_SUBJECT_DAILY_LIMIT"


def test_repeated_subject_limit_violation_exhausts_after_two_calls() -> None:
    raw = structured_response(
        "Planı iki saat sınırına göre düzenledim.",
        (("2026-10-05", 121, "subject", "mathematics"),),
    )
    orchestrator, memory, provider, learner = make_mock_runtime(raw)

    with pytest.raises(
        ResponseRegenerationExhausted,
        match="PLAN_REQUEST_SUBJECT_DAILY_LIMIT",
    ):
        orchestrator.respond(
            learner.learner_id,
            "Matematiğe günde en fazla 2 saat ayırabilirim. Bana plan yap.",
        )

    assert len(provider.requests) == 2
    memory.save_study_plan.assert_not_called()


def test_session_tolerance_is_soft_and_not_a_daily_total_rejection() -> None:
    request_context = extract_planning_request_context(
        "1 saat sonra sıkılıyorum."
    )
    learner = Learner()
    learning_context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )
    proposal = make_write_proposal(
        learner,
        learning_context,
        (
            (MONDAY, 45, "subject", "mathematics"),
            (MONDAY, 45, "subject", "physics"),
            (MONDAY, 45, "subject", "chemistry"),
        ),
    )

    tolerance = request_context.session_tolerances[0]
    assert tolerance.preferred_max_continuous_minutes == 60
    assert tolerance.strength is ConstraintStrength.SOFT
    assert evaluate_request_subject_limits(request_context, proposal) == ()


def test_partial_commitment_keeps_exact_weekdays_unknown() -> None:
    context = extract_planning_request_context(
        "Haftada 3 hafta içi günü İngilizce kursum var."
    )

    commitment = context.recurring_commitments[0]
    assert commitment.occurrence_count == 3
    assert commitment.day_scope is RecurringDayScope.WEEKDAY
    assert commitment.exact_days == ()


def test_home_arrival_anchor_has_no_availability_implication() -> None:
    context = extract_planning_request_context("Eve 17:00'de geliyorum.")

    anchor = context.schedule_anchors[0]
    assert anchor.anchor_type is ScheduleAnchorType.HOME_ARRIVAL
    assert anchor.anchor_time.isoformat(timespec="minutes") == "17:00"
    assert anchor.availability_implication is AvailabilityImplication.NONE
    assert resolve_daily_time_budget((), MONDAY).status is (
        TimeBudgetResolutionStatus.UNKNOWN
    )


def test_explicit_daily_workload_mismatch_is_detected() -> None:
    learner = Learner()
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )
    proposal = make_write_proposal(
        learner,
        context,
        ((MONDAY, 90, "subject", "mathematics"),),
    )

    violations = evaluate_response_proposal_workload(
        "Her gün 3-4 saat çalış.", proposal
    )

    assert violations[0].rule_id == (
        "PLAN_RESPONSE_PROPOSAL_WORKLOAD_MISMATCH"
    )


def test_aligned_daily_workload_passes() -> None:
    learner = Learner()
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )
    proposal = make_write_proposal(
        learner,
        context,
        ((MONDAY, 90, "subject", "mathematics"),),
    )

    assert evaluate_response_proposal_workload(
        "Her gün yaklaşık 90 dakika çalış.", proposal
    ) == ()


@pytest.mark.parametrize(
    "text",
    [
        "Günde birkaç saat ayırabilirsen iyi olur.",
        "Zamanın oldukça çalış.",
        "Daha düzenli çalışmalısın.",
        "3-4 saatlik vaktin varsa çalışabilirsin.",
    ],
)
def test_conditional_or_non_numeric_workload_is_not_claim(text: str) -> None:
    assert extract_daily_workload_claim(text) is None


def test_repeated_workload_drift_exhausts_after_two_calls() -> None:
    raw = structured_response(
        "Her gün 3-4 saat çalış.",
        (("2026-10-05", 90, "subject", "mathematics"),),
    )
    orchestrator, memory, provider, learner = make_mock_runtime(raw)

    with pytest.raises(
        ResponseRegenerationExhausted,
        match="PLAN_RESPONSE_PROPOSAL_WORKLOAD_MISMATCH",
    ):
        orchestrator.respond(learner.learner_id, "Bana günlük plan yap.")

    assert len(provider.requests) == 2
    memory.save_study_plan.assert_not_called()


def test_request_context_is_canonical_and_nothing_is_persisted() -> None:
    engine = create_sqlite_engine("sqlite+pysqlite:///:memory:")
    create_schema(engine)
    factory = create_session_factory(engine)
    memory = LearnerMemoryService(factory)
    learner = Learner()
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )
    memory.register_learner(learner, (context,))
    before = memory.get_learner_memory_snapshot(learner.learner_id)
    raw = structured_response(
        "Her gün yaklaşık 90 dakika çalış.",
        (("2026-10-05", 90, "subject", "mathematics"),),
    )
    provider = FakeLLMProvider(responder=lambda _: raw)
    message = (
        "Matematiğe günde en fazla 2 saat ayırabilirim. "
        "1 saat sonra sıkılıyorum. "
        "Haftada 3 hafta içi günü İngilizce kursum var. "
        "Eve 17:00'de geliyorum. Bana plan yap."
    )

    result = CoachOrchestrator(memory, provider).respond(
        learner.learner_id, message
    )
    after = memory.get_learner_memory_snapshot(learner.learner_id)

    request = provider.requests[0]
    assert message not in request.memory_context
    assert "subject/mathematics max 120 min/day [HARD" in request.memory_context
    assert "preferred continuous session max 60 min [SOFT" in request.memory_context
    assert "3 WEEKDAY occurrences/week; exact days UNKNOWN" in request.memory_context
    assert "home arrival: 17:00; availability implication NONE" in (
        request.memory_context
    )
    assert result.study_plan_proposal is not None
    assert before == after
    assert after.preferences == ()
    assert after.availability == ()
    assert after.study_plans == ()
    assert after.study_tasks == ()
    engine.dispose()


@pytest.mark.parametrize(
    "message",
    [
        "Matematiğe daha çok çalışmalıyım.",
        "Akşamları bazen müsait oluyorum.",
        "Çok yorma beni.",
    ],
)
def test_ambiguous_language_does_not_create_constraints(message: str) -> None:
    assert extract_planning_request_context(message).is_empty
