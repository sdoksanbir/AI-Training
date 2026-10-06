from datetime import date
import json
from unittest.mock import Mock

import pytest

from educoach.llm import FakeLLMProvider
from educoach.models import (
    Availability,
    AvailabilityType,
    ContextType,
    DayOfWeek,
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
    evaluate_response_schedule_grounding,
    extract_daily_workload_claim,
    extract_planning_request_context,
)
from educoach.orchestrator.planning_request import (
    PlanningClaimKind,
    PlanningClaimModality,
    extract_response_planning_claims,
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
    *,
    availability: tuple[Availability, ...] = (),
) -> LearnerMemorySnapshot:
    return LearnerMemorySnapshot(
        learner=learner,
        contexts=(context,),
        goals=(),
        availability=availability,
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


def make_mock_runtime(
    response_text: str,
    *,
    availability: tuple[Availability, ...] = (),
):
    learner = Learner()
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )
    memory = Mock(spec=LearnerMemoryService)
    memory.get_learner_memory_snapshot.return_value = make_snapshot(
        learner,
        context,
        availability=availability,
    )
    provider = FakeLLMProvider(responder=lambda _: response_text)
    return CoachOrchestrator(memory, provider), memory, provider, learner


def structured_text_without_proposal(response_text: str) -> str:
    return json.dumps(
        {"response_text": response_text, "proposal": None},
        ensure_ascii=False,
    )


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
    ("message", "expected_minutes"),
    [
        ("En fazla günde 2 saat matematik çalışabilirim.", 120),
        ("En fazla günde 45 dakika matematik çalışabilirim.", 45),
    ],
)
def test_subject_limit_word_order_variant_is_extracted(
    message: str,
    expected_minutes: int,
) -> None:
    context = extract_planning_request_context(message)

    limit = context.daily_subject_limits[0]
    assert limit.area_code == "mathematics"
    assert limit.max_minutes_per_day == expected_minutes
    assert limit.strength is ConstraintStrength.HARD


def test_daily_math_statement_without_maximum_is_not_a_limit() -> None:
    context = extract_planning_request_context(
        "Günde 2 saat matematik çalışıyorum."
    )

    assert context.daily_subject_limits == ()


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


@pytest.mark.parametrize(
    ("task_type", "area_type", "area_code", "expected_rule"),
    [
        (TaskType.STUDY, None, None, "PLAN_REQUEST_SUBJECT_LIMIT_UNVERIFIABLE"),
        (TaskType.PRACTICE, None, None, "PLAN_REQUEST_SUBJECT_LIMIT_UNVERIFIABLE"),
        (TaskType.REVISION, None, None, "PLAN_REQUEST_SUBJECT_LIMIT_UNVERIFIABLE"),
        (TaskType.READING, None, None, "PLAN_REQUEST_SUBJECT_LIMIT_UNVERIFIABLE"),
        (TaskType.VOCABULARY, None, None, "PLAN_REQUEST_SUBJECT_LIMIT_UNVERIFIABLE"),
        (TaskType.HOMEWORK, None, None, "PLAN_REQUEST_SUBJECT_LIMIT_UNVERIFIABLE"),
        (TaskType.STUDY, "subject", "physics", None),
        (TaskType.EXAM, None, None, None),
        (TaskType.ANALYSIS, None, None, None),
        (TaskType.OTHER, None, None, None),
    ],
)
def test_hard_subject_limit_requires_area_only_for_content_tasks(
    task_type: TaskType,
    area_type: str | None,
    area_code: str | None,
    expected_rule: str | None,
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
    plan = StudyPlan(
        learner_id=learner.learner_id,
        context_id=learning_context.context_id,
        title="Sentetik plan",
        plan_type=PlanType.DAILY,
        start_date=MONDAY,
        end_date=MONDAY,
    )
    proposal = StudyPlanWriteProposal(
        plan=plan,
        tasks=(
            StudyTask(
                plan_id=plan.plan_id,
                context_id=learning_context.context_id,
                task_date=MONDAY,
                task_type=task_type,
                description="Sentetik görev",
                planned_minutes=60,
                area_type=area_type,
                area_code=area_code,
            ),
        ),
    )

    violations = evaluate_request_subject_limits(request_context, proposal)

    assert [item.rule_id for item in violations] == (
        [expected_rule] if expected_rule is not None else []
    )


@pytest.mark.parametrize(
    ("area_code", "description"),
    [
        (
            "turkish",
            "Matematik: TYT soru çözümü (90 dk) + Türkçe okuma (30 dk)",
        ),
        (
            "social_studies",
            "Matematik: TYT konuları (90 dk) + Sosyal bilgiler (30 dk)",
        ),
    ],
)
def test_hard_math_limit_rejects_explicit_metadata_description_contradiction(
    area_code: str,
    description: str,
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
    proposal = make_write_proposal(
        learner,
        learning_context,
        ((MONDAY, 120, "subject", area_code),),
    )
    proposal.tasks[0].description = description

    violations = evaluate_request_subject_limits(request_context, proposal)

    assert [item.rule_id for item in violations] == [
        "PLAN_REQUEST_SUBJECT_LIMIT_UNVERIFIABLE"
    ]


def test_separate_atomic_subject_tasks_keep_hard_math_limit_verifiable() -> None:
    learner = Learner()
    learning_context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )
    request_context = extract_planning_request_context(
        "Matematiğe günde en fazla 2 saat ayırabilirim."
    )
    proposal = make_write_proposal(
        learner,
        learning_context,
        (
            (MONDAY, 90, "subject", "mathematics"),
            (MONDAY, 30, "subject", "turkish"),
        ),
    )
    proposal.tasks[0].description = "Matematik soru çözümü"
    proposal.tasks[1].description = "Türkçe okuma"

    assert evaluate_request_subject_limits(request_context, proposal) == ()


@pytest.mark.parametrize(
    "task_type",
    [TaskType.EXAM, TaskType.ANALYSIS, TaskType.OTHER],
)
def test_non_content_task_keeps_atomicity_exemption(task_type: TaskType) -> None:
    learner = Learner()
    learning_context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )
    request_context = extract_planning_request_context(
        "Matematiğe günde en fazla 2 saat ayırabilirim."
    )
    proposal = make_write_proposal(
        learner,
        learning_context,
        ((MONDAY, 120, "operational", "general"),),
    )
    proposal.tasks[0].task_type = task_type
    proposal.tasks[0].description = "Matematik deneme analizi"

    assert evaluate_request_subject_limits(request_context, proposal) == ()


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


def test_repeated_atomicity_contradiction_exhausts_after_two_calls() -> None:
    raw = json.dumps(
        {
            "response_text": "Planı iki saat sınırına göre düzenledim.",
            "proposal": {
                "title": "Sentetik plan",
                "plan_type": "weekly",
                "start_date": "2026-10-05",
                "end_date": "2026-10-05",
                "tasks": [
                    {
                        "task_date": "2026-10-05",
                        "task_type": "study",
                        "description": (
                            "Matematik soru çözümü (90 dk) + "
                            "Türkçe okuma (30 dk)"
                        ),
                        "planned_minutes": 120,
                        "area_type": "subject",
                        "area_code": "turkish",
                    }
                ],
            },
        },
        ensure_ascii=False,
    )
    orchestrator, memory, provider, learner = make_mock_runtime(raw)

    with pytest.raises(
        ResponseRegenerationExhausted,
        match="PLAN_REQUEST_SUBJECT_LIMIT_UNVERIFIABLE",
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


@pytest.mark.parametrize(
    ("message", "expected_minutes"),
    [
        ("1 saat çalışınca sıkılıyorum.", 60),
        ("45 dakika çalışınca sıkılıyorum.", 45),
    ],
)
def test_session_tolerance_working_variant_is_soft(
    message: str,
    expected_minutes: int,
) -> None:
    context = extract_planning_request_context(message)

    tolerance = context.session_tolerances[0]
    assert tolerance.preferred_max_continuous_minutes == expected_minutes
    assert tolerance.strength is ConstraintStrength.SOFT


def test_partial_commitment_keeps_exact_weekdays_unknown() -> None:
    context = extract_planning_request_context(
        "Haftada 3 hafta içi günü İngilizce kursum var."
    )

    commitment = context.recurring_commitments[0]
    assert commitment.occurrence_count == 3
    assert commitment.day_scope is RecurringDayScope.WEEKDAY
    assert commitment.exact_days == ()


@pytest.mark.parametrize(
    ("message", "expected_count"),
    [
        ("Hafta içi 3 gün İngilizce kursum var.", 3),
        ("Hafta iici 2 gun Ingilizce kursum var.", 2),
        ("Hafta iiçi 2 gün İngilizce kursum var.", 2),
    ],
)
def test_recurring_commitment_word_order_and_narrow_typo_variants(
    message: str,
    expected_count: int,
) -> None:
    context = extract_planning_request_context(message)

    commitment = context.recurring_commitments[0]
    assert commitment.occurrence_count == expected_count
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


@pytest.mark.parametrize(
    "message",
    [
        "Akşam saat 5'te eve geliyorum.",
        "Akşam saat 5 te eve geliyorum.",
    ],
)
def test_evening_home_arrival_is_converted_to_pm_without_availability(
    message: str,
) -> None:
    context = extract_planning_request_context(message)

    anchor = context.schedule_anchors[0]
    assert anchor.anchor_time.isoformat(timespec="minutes") == "17:00"
    assert anchor.availability_implication is AvailabilityImplication.NONE


def test_evening_home_arrival_without_time_is_not_an_anchor() -> None:
    context = extract_planning_request_context("Akşam eve geliyorum.")

    assert context.schedule_anchors == ()


def test_unknown_availability_exact_clock_schedule_exhausts_regeneration() -> None:
    raw = structured_text_without_proposal(
        "17:00-19:00 matematik çalış. 19:00-20:00 TYT çalış."
    )
    orchestrator, memory, provider, learner = make_mock_runtime(raw)

    with pytest.raises(
        ResponseRegenerationExhausted,
        match="PLAN_RESPONSE_UNSUPPORTED_AVAILABILITY",
    ):
        orchestrator.respond(
            learner.learner_id,
            "Akşam saat 5 te eve geliyorum. Bana program yap.",
        )

    assert len(provider.requests) == 2
    memory.save_study_plan.assert_not_called()


def test_multiline_clock_schedule_exhausts_regeneration() -> None:
    raw = structured_text_without_proposal(
        "5:00 - 6:00\n"
        "- Ödevlerinizi tamamlayın.\n\n"
        "6:00 - 7:30\n"
        "- TYT çalışın."
    )
    orchestrator, memory, provider, learner = make_mock_runtime(raw)

    with pytest.raises(
        ResponseRegenerationExhausted,
        match="PLAN_RESPONSE_UNSUPPORTED_AVAILABILITY",
    ):
        orchestrator.respond(
            learner.learner_id,
            "Akşam saat 5 te eve geliyorum. Bana program yap.",
        )

    assert len(provider.requests) == 2
    memory.save_study_plan.assert_not_called()


@pytest.mark.parametrize(
    "response_text",
    [
        "### Ödevler (18:00-20:00)",
        "**TYT Hazırlık (20:00-22:00)**",
        "YKS Hazırlık (22:00-23:00)",
    ],
)
def test_schedule_heading_is_typed_asserted_exact_clock_claim(
    response_text: str,
) -> None:
    claims = extract_response_planning_claims(response_text)

    assert len(claims) == 1
    assert claims[0].kind is PlanningClaimKind.EXACT_CLOCK_ASSIGNMENT
    assert claims[0].modality is PlanningClaimModality.ASSERTED


@pytest.mark.parametrize(
    ("response_text", "expected_modality"),
    [
        (
            "Müsaitliğin netleşirse Ödevler (18:00-20:00)",
            PlanningClaimModality.CONDITIONAL,
        ),
        (
            "Örneğin Ödevler (18:00-20:00)",
            PlanningClaimModality.ILLUSTRATIVE,
        ),
        (
            "Dün 18:00-20:00 çalıştığını söyledin.",
            PlanningClaimModality.REPORTED,
        ),
    ],
)
def test_non_asserted_exact_clock_modality_is_preserved(
    response_text: str,
    expected_modality: PlanningClaimModality,
) -> None:
    claims = extract_response_planning_claims(response_text)

    assert len(claims) == 1
    assert claims[0].kind is PlanningClaimKind.EXACT_CLOCK_ASSIGNMENT
    assert claims[0].modality is expected_modality


def test_exact_clock_question_is_not_a_planning_assignment() -> None:
    assert extract_response_planning_claims(
        "18:00-20:00 uygun olur mu?"
    ) == ()


@pytest.mark.parametrize(
    "response_text",
    [
        "Müsaitliğin netleşirse Ödevler (18:00-20:00)",
        "Örneğin TYT Hazırlık (20:00-22:00)",
        "18:00-20:00 uygun olur mu?",
        "Dün 18:00-20:00 çalıştığını söyledin.",
    ],
)
def test_non_asserted_clock_heading_passes_grounding_boundary(
    response_text: str,
) -> None:
    learner = Learner()
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )

    assert evaluate_response_schedule_grounding(
        response_text,
        extract_planning_request_context(
            "Akşam saat 5 te eve geliyorum. Bana program yap."
        ),
        make_snapshot(learner, context),
        None,
    ) == ()


@pytest.mark.parametrize(
    "response_text",
    [
        "Ödevler (18:00-20:00)",
        "TYT Hazırlık (20:00-22:00)",
    ],
)
def test_schedule_heading_without_availability_is_rejected(
    response_text: str,
) -> None:
    learner = Learner()
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )
    planning_request = extract_planning_request_context(
        "Akşam saat 5 te eve geliyorum. Bana program yap."
    )

    violations = evaluate_response_schedule_grounding(
        response_text,
        planning_request,
        make_snapshot(learner, context),
        None,
    )

    assert [item.rule_id for item in violations] == [
        "PLAN_RESPONSE_UNSUPPORTED_AVAILABILITY"
    ]


def test_proposal_does_not_support_exact_clock_without_availability() -> None:
    learner = Learner()
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )
    proposal = make_write_proposal(
        learner,
        context,
        ((MONDAY, 120, "subject", "mathematics"),),
    )

    violations = evaluate_response_schedule_grounding(
        "Ödevler (18:00-20:00)",
        extract_planning_request_context(
            "Akşam saat 5 te eve geliyorum. Bana program yap."
        ),
        make_snapshot(learner, context),
        proposal,
    )

    assert [item.rule_id for item in violations] == [
        "PLAN_RESPONSE_UNSUPPORTED_AVAILABILITY"
    ]


@pytest.mark.parametrize(
    "response_text",
    [
        (
            "17:00'de eve geldiğini biliyorum ancak sonrasında ne kadar "
            "müsait olduğunu bilmiyorum."
        ),
        "Müsaitsen 18:00-19:00 matematik çalışabilirsin.",
        "Örneğin müsait olduğun bir gün 18:00-19:00 çalışabilirsin.",
        (
            "17:00'den sonra ne kadar vaktin olduğunu netleştirirsek "
            "programı saatlendirebiliriz."
        ),
        "17:00 - 18:00\n- Müsaitsen matematik çalışabilirsin.",
        "17:00 - 18:00\n- Örneğin bu saati kullanabilirsin.",
        (
            "17:00 - 18:00\n"
            "- Sonrasında ne kadar müsait olduğunu bilmiyorum."
        ),
        (
            "17:00 - 18:00\n"
            "- Kısa bir ara ver.\n"
            "- Sonra matematik çalış."
        ),
    ],
)
def test_home_arrival_safe_or_conditional_clock_language_passes(
    response_text: str,
) -> None:
    raw = structured_text_without_proposal(response_text)
    orchestrator, memory, provider, learner = make_mock_runtime(raw)

    result = orchestrator.respond(
        learner.learner_id,
        "Akşam saat 5 te eve geliyorum. Bana program yap.",
    )

    assert result.text == response_text
    assert len(provider.requests) == 1
    memory.save_study_plan.assert_not_called()


def test_any_available_record_documents_exact_clock_p0_fail_open() -> None:
    learner = Learner()
    available = Availability(
        learner_id=learner.learner_id,
        day_of_week=DayOfWeek.MONDAY,
        availability_type=AvailabilityType.AVAILABLE,
        available_minutes=30,
    )
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )
    planning_request = extract_planning_request_context(
        "Akşam saat 5 te eve geliyorum. Bana program yap."
    )

    violations = evaluate_response_schedule_grounding(
        "17:00-19:00 matematik çalış.",
        planning_request,
        make_snapshot(learner, context, availability=(available,)),
        None,
    )

    assert violations == ()


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
    ("text", "minimum", "maximum"),
    [
        ("Her gün 3-4 saatlik toplam çalışma süresi planlanmıştır.", 180, 240),
        ("Günde 8-10 saatlik bir çalışma planı öneriyorum.", 480, 600),
        ("Günde 8-10 saat çalışarak ilerleyebilirsin.", 480, 600),
        ("Günde yaklaşık 90 dakika çalış.", 90, 90),
        ("Günde 8-10 saat çalışmanız gerekir.", 480, 600),
        ("Her gün 6 saat çalışmalısın.", 360, 360),
        ("Günlük Program (8-10 saat):", 480, 600),
        ("Günlük Program (8-10 saat)", 480, 600),
        ("#### **Günlük Program (8–10 saat):**", 480, 600),
        ("**Günlük Program (8-10 saat):**", 480, 600),
        ("**Günlük Program (8-10 saat)**:", 480, 600),
        ("### Günlük Program (8-10 saat):", 480, 600),
        ("Günlük çalışma: 8-10 saat", 480, 600),
        ("Günlük çalışma süresi: 6 saat", 360, 360),
        (
            "Toplam 8-10 saat çalışmanız gerekir. "
            "08:00-09:00 matematik çalış. 09:00-10:00 TYT çalış.",
            480,
            600,
        ),
    ],
)
def test_explicit_daily_workload_variants_are_parsed(
    text: str,
    minimum: int,
    maximum: int,
) -> None:
    claim = extract_daily_workload_claim(text)

    assert claim is not None
    assert claim.min_minutes_per_day == minimum
    assert claim.max_minutes_per_day == maximum


@pytest.mark.parametrize(
    "text",
    [
        "Günlük Program Önerisi (Toplam 7.5-8.5 saat)",
        "Günlük Program Önerisi (Toplam 7,5-8,5 saat)",
    ],
)
def test_decimal_daily_workload_is_typed_in_minutes(text: str) -> None:
    claims = extract_response_planning_claims(text)

    assert len(claims) == 1
    claim = claims[0]
    assert claim.kind is PlanningClaimKind.DAILY_WORKLOAD_ASSIGNMENT
    assert claim.modality is PlanningClaimModality.ASSERTED
    assert claim.min_minutes_per_day == 450
    assert claim.max_minutes_per_day == 510


def test_mandatory_daily_workload_is_typed_capacity_prescription() -> None:
    claims = extract_response_planning_claims(
        "Günlük 8 saat çalışmak zorunludur."
    )

    assert len(claims) == 1
    assert claims[0].modality is PlanningClaimModality.ASSERTED
    assert claims[0].is_capacity_prescription is True


@pytest.mark.parametrize(
    ("text", "expected_modality"),
    [
        (
            "Şu anda günde 8 saat çalıştığını söyledin.",
            PlanningClaimModality.REPORTED,
        ),
        (
            "Geçen yıl günlük 8 saat çalışıyordun.",
            PlanningClaimModality.REPORTED,
        ),
        (
            "Bazı öğrenciler günde 8 saat çalışabiliyor.",
            PlanningClaimModality.ILLUSTRATIVE,
        ),
        (
            "Müsaitsen günde 3 saat ayırabilirsin.",
            PlanningClaimModality.CONDITIONAL,
        ),
        (
            "Örneğin günlük 2 saatlik bir plan düşünülebilir.",
            PlanningClaimModality.ILLUSTRATIVE,
        ),
    ],
)
def test_non_asserted_daily_workload_modality_is_preserved(
    text: str,
    expected_modality: PlanningClaimModality,
) -> None:
    claims = extract_response_planning_claims(text)

    assert len(claims) == 1
    assert claims[0].kind is PlanningClaimKind.DAILY_WORKLOAD_ASSIGNMENT
    assert claims[0].modality is expected_modality


def test_multiple_daily_workloads_are_all_extracted() -> None:
    claims = tuple(
        claim
        for claim in extract_response_planning_claims(
            "Günde 2 saat çalışmalısın. Her gün 3 saat çalışmalısın."
        )
        if claim.kind is PlanningClaimKind.DAILY_WORKLOAD_ASSIGNMENT
    )

    assert [claim.min_minutes_per_day for claim in claims] == [120, 180]
    assert all(
        claim.modality is PlanningClaimModality.ASSERTED for claim in claims
    )


@pytest.mark.parametrize(
    "text",
    [
        "Günde 2 saat çalış, 15 dakika mola ver.",
        "Günde toplam 2 saat çalış. Her 50 dakikada 10 dakika mola ver.",
    ],
)
def test_daily_scope_does_not_promote_break_durations(text: str) -> None:
    claims = tuple(
        claim
        for claim in extract_response_planning_claims(text)
        if claim.kind is PlanningClaimKind.DAILY_WORKLOAD_ASSIGNMENT
    )

    assert len(claims) == 1
    assert claims[0].modality is PlanningClaimModality.ASSERTED
    assert claims[0].min_minutes_per_day == 120
    assert claims[0].max_minutes_per_day == 120


def test_clock_schedule_does_not_promote_session_or_break_durations() -> None:
    claims = extract_response_planning_claims(
        "18:00-19:00 matematik çalış. 19:00-20:00 TYT çalış. "
        "30 dakika çalışma. 15 dakika mola."
    )

    assert not any(
        claim.kind is PlanningClaimKind.DAILY_WORKLOAD_ASSIGNMENT
        for claim in claims
    )


@pytest.mark.parametrize(
    "text",
    [
        "Günlük 8 saat çalışmak şart.",
        "Günlük 8 saat çalışmak şarttır.",
    ],
)
def test_requirement_daily_workload_is_capacity_prescription(text: str) -> None:
    claims = extract_response_planning_claims(text)

    assert len(claims) == 1
    assert claims[0].kind is PlanningClaimKind.DAILY_WORKLOAD_ASSIGNMENT
    assert claims[0].modality is PlanningClaimModality.ASSERTED
    assert claims[0].min_minutes_per_day == 480
    assert claims[0].max_minutes_per_day == 480
    assert claims[0].is_capacity_prescription is True


@pytest.mark.parametrize(
    "text",
    [
        "Günde birkaç saat ayırabilirsen iyi olur.",
        "Günde 3-4 saat vaktin varsa çalışabilirsin.",
        "Günde 3 saat ayırabilirsen çalışabilirsin.",
        "Zamanın oldukça çalış.",
        "Daha düzenli çalışmalısın.",
        "3-4 saatlik vaktin varsa çalışabilirsin.",
        "Zamanın varsa 2 saat çalışabilirsin.",
        "Şu anda günde 8 saat çalıştığını söyledin.",
        "Bazı öğrenciler günde 8 saat çalışabiliyor.",
        "Müsaitlik bilgini bilmeden günlük süre belirleyemem.",
        "Toplam 8-10 saat çalışmanız gerekir.",
        "Geçen yıl günlük programım 8 saat sürüyordu.",
        "Geçen yıl **günlük programım 8 saat** sürüyordu.",
        "Bir öğrencinin günlük programı 8 saat olabilir.",
        "8 saatlik program örneği.",
        "Program örneği: **8-10 saat**",
    ],
)
def test_conditional_or_non_numeric_workload_is_not_claim(text: str) -> None:
    assert extract_daily_workload_claim(text) is None


@pytest.mark.parametrize(
    "response_text",
    [
        "Günde 8-10 saat çalışmanız gerekir.",
        "Her gün 6 saat çalışmalısın.",
        "Günlük Program (8-10 saat):",
        "Günlük Program (8-10 saat)",
        "#### **Günlük Program (8–10 saat):**",
        "Günlük çalışma süresi: 6 saat",
        "Günlük Program Önerisi (Toplam 7.5-8.5 saat)",
        "Günlük Program Önerisi (Toplam 7,5-8,5 saat)",
        "Günlük 8 saat çalışmak zorunludur.",
    ],
)
def test_response_only_prescriptive_workload_without_availability_regenerates(
    response_text: str,
) -> None:
    learner = Learner()
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )

    violations = evaluate_response_schedule_grounding(
        response_text,
        extract_planning_request_context("Nasıl çalışmalıyım?"),
        make_snapshot(learner, context),
        None,
    )

    assert [item.rule_id for item in violations] == [
        "PLAN_RESPONSE_UNSUPPORTED_AVAILABILITY"
    ]


def test_proposal_does_not_support_independent_capacity_prescription() -> None:
    learner = Learner()
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )
    proposal = make_write_proposal(
        learner,
        context,
        ((MONDAY, 480, "subject", "mathematics"),),
    )

    violations = evaluate_response_schedule_grounding(
        "Günlük 8 saat çalışmak zorunludur.",
        extract_planning_request_context("Nasıl çalışmalıyım?"),
        make_snapshot(learner, context),
        proposal,
    )

    assert [item.rule_id for item in violations] == [
        "PLAN_RESPONSE_UNSUPPORTED_AVAILABILITY"
    ]


def test_aligned_neutral_proposal_total_passes_without_availability() -> None:
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
    response_text = "Planın günlük toplamı 90 dakikadır."

    assert evaluate_response_schedule_grounding(
        response_text,
        extract_planning_request_context("Nasıl çalışmalıyım?"),
        make_snapshot(learner, context),
        proposal,
    ) == ()
    assert evaluate_response_proposal_workload(response_text, proposal) == ()


def test_neutral_proposal_total_mismatch_keeps_existing_rule() -> None:
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
        "Planın günlük toplamı 120 dakikadır.", proposal
    )

    assert [item.rule_id for item in violations] == [
        "PLAN_RESPONSE_PROPOSAL_WORKLOAD_MISMATCH"
    ]


def test_break_duration_does_not_create_proposal_workload_mismatch() -> None:
    learner = Learner()
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )
    proposal = make_write_proposal(
        learner,
        context,
        ((MONDAY, 120, "subject", "mathematics"),),
    )
    response_text = (
        "Günde 2 saatlik plan toplamı var, ayrıca 15 dakika mola ver."
    )

    assert evaluate_response_proposal_workload(response_text, proposal) == ()


def test_second_of_multiple_workloads_cannot_fail_open_mismatch() -> None:
    learner = Learner()
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )
    proposal = make_write_proposal(
        learner,
        context,
        ((MONDAY, 120, "subject", "mathematics"),),
    )

    violations = evaluate_response_proposal_workload(
        "Planın günlük toplamı 120 dakikadır. "
        "Günlük çalışma süresi 180 dakikadır.",
        proposal,
    )

    assert [item.rule_id for item in violations] == [
        "PLAN_RESPONSE_PROPOSAL_WORKLOAD_MISMATCH"
    ]


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


def test_pilot_word_order_variants_reach_canonical_llm_context() -> None:
    raw = structured_response(
        "Her gün yaklaşık 90 dakika çalış.",
        (("2026-10-05", 90, "subject", "mathematics"),),
    )
    orchestrator, memory, provider, learner = make_mock_runtime(raw)

    orchestrator.respond(
        learner.learner_id,
        "En fazla günde 2 saat matematik çalışabilirim. "
        "Hafta içi 3 gün İngilizce kursum var. Bana plan yap.",
    )

    request_context = provider.requests[0].memory_context
    assert "subject/mathematics max 120 min/day [HARD" in request_context
    assert "3 WEEKDAY occurrences/week; exact days UNKNOWN" in request_context
    assert memory.get_learner_memory_snapshot.return_value.availability == ()
    memory.save_study_plan.assert_not_called()


def test_evening_home_arrival_reaches_context_without_availability() -> None:
    raw = structured_response(
        "Her gün yaklaşık 90 dakika çalış.",
        (("2026-10-05", 90, "subject", "mathematics"),),
    )
    orchestrator, memory, provider, learner = make_mock_runtime(raw)

    orchestrator.respond(
        learner.learner_id,
        "Akşam saat 5 te eve geliyorum. Bana plan yap.",
    )

    request_context = provider.requests[0].memory_context
    assert "home arrival: 17:00; availability implication NONE" in request_context
    assert memory.get_learner_memory_snapshot.return_value.availability == ()
    memory.save_study_plan.assert_not_called()


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
