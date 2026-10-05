from dataclasses import FrozenInstanceError
from uuid import UUID, uuid4

import pytest

from educoach.models import ContextStatus, ContextType, Learner, LearningContext
from educoach.orchestrator import (
    ContextMessageMatch,
    MessageContextEvidence,
    MessageContextEvidenceStatus,
    project_message_context_evidence,
)
from educoach.services import LearnerMemorySnapshot
from educoach.specialties import (
    AmbiguousSpecialtyProfileError,
    ContextRoutingTerminology,
    SpecialtyProfile,
    SpecialtyProfileFamilyMismatchError,
    SpecialtyProfileNotFoundError,
    SpecialtyProfileRegistry,
    get_context_routing_terminology,
    load_builtin_profile,
)


def make_profile(
    code: str = "yks",
    family: ContextType = ContextType.ENTRANCE_EXAM,
    *,
    terminology: object | None = None,
    version: int = 1,
) -> SpecialtyProfile:
    values = {
        "profile_code": code,
        "profile_family": family,
        "display_name": code,
        "profile_version": version,
    }
    if terminology is not None:
        values["terminology"] = terminology
    return SpecialtyProfile(**values)


def configured_profile(
    code: str = "yks",
    family: ContextType = ContextType.ENTRANCE_EXAM,
    *,
    explicit_terms: list[str] | None = None,
    support_terms: list[str] | None = None,
    explicit_phrases: list[str] | None = None,
    version: int = 1,
) -> SpecialtyProfile:
    return make_profile(
        code,
        family,
        version=version,
        terminology={
            "context_routing": {
                "explicit_terms": explicit_terms or [],
                "support_terms": support_terms or [],
                "explicit_phrases": explicit_phrases or [],
            }
        },
    )


def make_context(
    learner: Learner,
    code: str = "yks",
    family: ContextType = ContextType.ENTRANCE_EXAM,
    *,
    context_id: UUID | None = None,
    status: ContextStatus = ContextStatus.ACTIVE,
) -> LearningContext:
    values = {
        "learner_id": learner.learner_id,
        "context_type": family,
        "program_code": code,
        "status": status,
    }
    if context_id is not None:
        values["context_id"] = context_id
    return LearningContext(**values)


def make_snapshot(
    learner: Learner,
    contexts: tuple[LearningContext, ...] = (),
) -> LearnerMemorySnapshot:
    return LearnerMemorySnapshot(
        learner=learner,
        contexts=contexts,
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


def make_registry(*profiles: SpecialtyProfile) -> SpecialtyProfileRegistry:
    registry = SpecialtyProfileRegistry()
    for profile in profiles:
        registry.register(profile)
    return registry


def project_for_yks(message: str) -> tuple[MessageContextEvidence, LearningContext]:
    learner = Learner()
    context = make_context(learner)
    result = project_message_context_evidence(
        message,
        make_snapshot(learner, (context,)),
        make_registry(load_builtin_profile("yks")),
    )
    return result, context


def test_missing_context_routing_is_valid_empty_terminology() -> None:
    assert get_context_routing_terminology(make_profile()) == (
        ContextRoutingTerminology()
    )


def test_terminology_is_normalized_deduplicated_and_canonically_ordered() -> None:
    profile = configured_profile(
        explicit_terms=[" YKS ", "AYT"],
        support_terms=["SÜRE", "Net"],
        explicit_phrases=[" TYT   Denemesi ", "AYT denemesi"],
    )

    assert get_context_routing_terminology(profile) == ContextRoutingTerminology(
        explicit_terms=("ayt", "yks"),
        support_terms=("net", "süre"),
        explicit_phrases=("ayt denemesi", "tyt denemesi"),
    )


def test_normalized_cross_field_terminology_overlap_is_rejected() -> None:
    profile = configured_profile(
        explicit_terms=["TYT"],
        support_terms=["tyt"],
    )

    with pytest.raises(ValueError, match="must be disjoint"):
        get_context_routing_terminology(profile)


def test_direct_terminology_cross_field_overlap_is_rejected() -> None:
    with pytest.raises(ValueError, match="must be disjoint"):
        ContextRoutingTerminology(
            explicit_terms=("tyt",),
            support_terms=("tyt",),
        )


@pytest.mark.parametrize(
    "terminology",
    [
        [],
        {"context_routing": None},
        {"context_routing": []},
        {"context_routing": {"explicit_terms": "yks"}},
        {"context_routing": {"explicit_terms": [1]}},
        {"context_routing": {"explicit_terms": [" "]}},
        {"context_routing": {"explicit_terms": ["YKS", "yks"]}},
        {"context_routing": {"unknown": []}},
        {"context_routing": {"explicit_terms": ["iki kelime"]}},
        {"context_routing": {"explicit_phrases": ["tek"]}},
    ],
)
def test_invalid_configured_terminology_is_rejected(terminology: object) -> None:
    with pytest.raises(ValueError):
        get_context_routing_terminology(make_profile(terminology=terminology))


def test_empty_message_has_no_evidence() -> None:
    result, _ = project_for_yks("")
    assert result == MessageContextEvidence(MessageContextEvidenceStatus.NONE, (), ())


def test_empty_terminology_produces_no_evidence() -> None:
    learner = Learner()
    context = make_context(learner)

    result = project_message_context_evidence(
        "TYT net",
        make_snapshot(learner, (context,)),
        make_registry(make_profile()),
    )

    assert result.status == MessageContextEvidenceStatus.NONE


@pytest.mark.parametrize("message", ["TYT", "YKS", "Matematik", "net"])
def test_standalone_signal_is_not_a_candidate(message: str) -> None:
    result, _ = project_for_yks(message)
    assert result.status == MessageContextEvidenceStatus.NONE


def test_explicit_term_and_support_term_produce_consistent_evidence() -> None:
    result, context = project_for_yks("TYT'de 74 net yaptım.")

    assert result.status == MessageContextEvidenceStatus.CONSISTENT
    assert result.candidate_context_ids == (context.context_id,)
    assert result.matches[0].matched_explicit_terms == ("tyt",)
    assert result.matches[0].matched_support_terms == ("net",)


def test_explicit_phrase_alone_produces_consistent_evidence() -> None:
    result, context = project_for_yks("Bugün bir TYT denemesi çözdüm.")

    assert result.candidate_context_ids == (context.context_id,)
    assert result.matches[0].matched_explicit_phrases == ("tyt denemesi",)


def test_inflected_exam_phrase_can_qualify_via_explicit_and_support_terms() -> None:
    result, context = project_for_yks("TYT denemesinde süre yetişmedi.")

    assert result.candidate_context_ids == (context.context_id,)
    assert result.matches[0].matched_explicit_terms == ("tyt",)
    assert result.matches[0].matched_support_terms == ("süre",)


def test_all_matching_signals_are_reported_once_in_canonical_order() -> None:
    result, _ = project_for_yks("YKS TYT AYT net süre; TYT denemesi, AYT denemesi")
    match = result.matches[0]

    assert match.matched_explicit_terms == ("ayt", "tyt", "yks")
    assert match.matched_support_terms == ("net", "süre")
    assert match.matched_explicit_phrases == ("ayt denemesi", "tyt denemesi")


def test_two_qualified_contexts_are_conflicting() -> None:
    learner = Learner()
    first = make_context(learner, "first", context_id=UUID(int=2))
    second = make_context(learner, "second", context_id=UUID(int=1))
    registry = make_registry(
        configured_profile(
            "first", explicit_terms=["tyt"], support_terms=["net"]
        ),
        configured_profile(
            "second", explicit_terms=["tyt"], support_terms=["net"]
        ),
    )

    result = project_message_context_evidence(
        "TYT net", make_snapshot(learner, (first, second)), registry
    )

    assert result.status == MessageContextEvidenceStatus.CONFLICTING
    assert result.candidate_context_ids == (second.context_id, first.context_id)


@pytest.mark.parametrize("status", [ContextStatus.INACTIVE, ContextStatus.COMPLETED])
def test_non_active_context_cannot_produce_message_evidence(
    status: ContextStatus,
) -> None:
    learner = Learner()
    context = make_context(learner, status=status)

    result = project_message_context_evidence(
        "TYT net",
        make_snapshot(learner, (context,)),
        SpecialtyProfileRegistry(),
    )

    assert result.status == MessageContextEvidenceStatus.NONE


def test_duplicate_context_id_is_rejected_even_when_inactive() -> None:
    learner = Learner()
    context_id = uuid4()
    contexts = (
        make_context(learner, context_id=context_id),
        make_context(
            learner,
            context_id=context_id,
            status=ContextStatus.INACTIVE,
        ),
    )

    with pytest.raises(ValueError, match="duplicate context_id"):
        project_message_context_evidence(
            "", make_snapshot(learner, contexts), SpecialtyProfileRegistry()
        )


def test_foreign_context_is_rejected_even_when_inactive() -> None:
    learner = Learner()
    foreign_context = make_context(Learner(), status=ContextStatus.INACTIVE)

    with pytest.raises(ValueError, match="snapshot learner"):
        project_message_context_evidence(
            "", make_snapshot(learner, (foreign_context,)), SpecialtyProfileRegistry()
        )


def test_unknown_active_profile_error_propagates() -> None:
    learner = Learner()

    with pytest.raises(SpecialtyProfileNotFoundError):
        project_message_context_evidence(
            "",
            make_snapshot(learner, (make_context(learner),)),
            SpecialtyProfileRegistry(),
        )


def test_profile_family_mismatch_error_propagates() -> None:
    learner = Learner()
    context = make_context(learner)
    registry = make_registry(make_profile(family=ContextType.SCHOOL))

    with pytest.raises(SpecialtyProfileFamilyMismatchError):
        project_message_context_evidence("", make_snapshot(learner, (context,)), registry)


def test_ambiguous_profile_error_propagates() -> None:
    learner = Learner()
    context = make_context(learner)
    registry = make_registry(make_profile(version=1), make_profile(version=2))

    with pytest.raises(AmbiguousSpecialtyProfileError):
        project_message_context_evidence("", make_snapshot(learner, (context,)), registry)


@pytest.mark.parametrize(
    "message",
    [
        "  tYt... NET  ",
        "TYT\n\tNET",
        "TYT—net",
        "YKS, SÜRE",
    ],
)
def test_matching_is_case_whitespace_punctuation_and_turkish_safe(
    message: str,
) -> None:
    result, _ = project_for_yks(message)
    assert result.status == MessageContextEvidenceStatus.CONSISTENT


def test_terms_do_not_match_substrings() -> None:
    result, _ = project_for_yks("Hayti nette çalışıyorum")
    assert result.status == MessageContextEvidenceStatus.NONE


def test_context_input_order_does_not_change_projection() -> None:
    learner = Learner()
    first = make_context(learner, "first", context_id=UUID(int=1))
    second = make_context(learner, "second", context_id=UUID(int=2))
    profiles = (
        configured_profile("first", explicit_phrases=["birinci sınav"]),
        configured_profile("second", explicit_phrases=["ikinci sınav"]),
    )
    registry = make_registry(*profiles)

    forward = project_message_context_evidence(
        "İkinci sınav ve birinci sınav",
        make_snapshot(learner, (first, second)),
        registry,
    )
    reverse = project_message_context_evidence(
        "İkinci sınav ve birinci sınav",
        make_snapshot(learner, (second, first)),
        registry,
    )

    assert forward == reverse


def test_registry_registration_order_does_not_change_projection() -> None:
    learner = Learner()
    first = make_context(learner, "first", context_id=UUID(int=1))
    second = make_context(learner, "second", context_id=UUID(int=2))
    profiles = (
        configured_profile("first", explicit_phrases=["birinci sınav"]),
        configured_profile("second", explicit_phrases=["ikinci sınav"]),
    )
    snapshot = make_snapshot(learner, (first, second))

    forward = project_message_context_evidence(
        "İkinci sınav ve birinci sınav", snapshot, make_registry(*profiles)
    )
    reverse = project_message_context_evidence(
        "İkinci sınav ve birinci sınav",
        snapshot,
        make_registry(*reversed(profiles)),
    )

    assert forward == reverse


def test_contracts_are_immutable() -> None:
    match = ContextMessageMatch(UUID(int=1), (), (), ("tyt denemesi",))
    evidence = MessageContextEvidence(
        MessageContextEvidenceStatus.CONSISTENT, (UUID(int=1),), (match,)
    )

    with pytest.raises(FrozenInstanceError):
        match.context_id = UUID(int=2)
    with pytest.raises(FrozenInstanceError):
        evidence.status = MessageContextEvidenceStatus.NONE


def test_direct_context_match_cross_field_overlap_is_rejected() -> None:
    with pytest.raises(ValueError, match="must be disjoint"):
        ContextMessageMatch(
            context_id=UUID(int=1),
            matched_explicit_terms=("tyt",),
            matched_support_terms=("tyt",),
        )


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ContextMessageMatch(UUID(int=1)),
        lambda: ContextMessageMatch(
            UUID(int=1), ("tyt",), (), ()
        ),
        lambda: ContextMessageMatch(
            UUID(int=1), ("TYT",), ("net",), ()
        ),
        lambda: MessageContextEvidence(
            MessageContextEvidenceStatus.CONSISTENT, (), ()
        ),
        lambda: MessageContextEvidence(
            MessageContextEvidenceStatus.NONE,
            (UUID(int=1),),
            (ContextMessageMatch(UUID(int=1), (), (), ("tyt denemesi",)),),
        ),
        lambda: MessageContextEvidence(
            MessageContextEvidenceStatus.CONFLICTING,
            (UUID(int=1),),
            (ContextMessageMatch(UUID(int=1), (), (), ("tyt denemesi",)),),
        ),
        lambda: MessageContextEvidence(
            MessageContextEvidenceStatus.CONSISTENT,
            (UUID(int=1),),
            (ContextMessageMatch(UUID(int=2), (), (), ("tyt denemesi",)),),
        ),
    ],
)
def test_invalid_direct_contract_state_is_rejected(factory) -> None:
    with pytest.raises(ValueError):
        factory()


def test_builtin_yks_has_the_evidenced_routing_terminology() -> None:
    terminology = get_context_routing_terminology(load_builtin_profile("yks"))

    assert terminology == ContextRoutingTerminology(
        explicit_terms=("ayt", "tyt", "yks"),
        support_terms=("deneme", "net", "süre"),
        explicit_phrases=("ayt denemesi", "tyt denemesi"),
    )


@pytest.mark.parametrize("profile_code", ["ales", "general_english", "school_7"])
def test_other_builtin_profiles_keep_empty_routing_terminology(
    profile_code: str,
) -> None:
    assert get_context_routing_terminology(load_builtin_profile(profile_code)) == (
        ContextRoutingTerminology()
    )
