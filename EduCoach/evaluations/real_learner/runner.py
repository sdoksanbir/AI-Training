"""Private development evaluation runner over the production orchestrator."""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
import json
from pathlib import Path
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr

from educoach.llm import LLMProvider
from educoach.models import (
    EducationStatus,
    Learner,
    LearningContext,
    PlanType,
    TaskPriority,
    TaskType,
)
from educoach.orchestrator import CoachOrchestrator
from educoach.persistence import (
    create_schema,
    create_session_factory,
    create_sqlite_engine,
)
from educoach.services import LearnerMemoryService
from educoach.specialties import (
    SpecialtyProfileRegistry,
    create_builtin_specialty_registry,
)
from educoach.writeback import StudyPlanWriteProposal

from .contracts import (
    RealLearnerEvaluationCase,
    require_case_local_public_forum_groups,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRIVATE_ROOT = PROJECT_ROOT / "evaluations" / "real_learner" / "private"
RUN_ID_PATTERN = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
UUID_PATTERN = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
SAFE_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

AUTHORITATIVE_FACT_KINDS = frozenset(
    {"education_status", "grade_level", "study_track"}
)


class ExecutionStatus(StrEnum):
    COMPLETED = "completed"
    NOT_RUN = "not_run"
    FAILED = "failed"


class PrivatePathError(ValueError):
    """Raised when private learner material would leave its ignored boundary."""


class ProviderUnavailableError(RuntimeError):
    """Raised without provider internals when generation cannot be initialized."""


class DuplicateCaseError(ValueError):
    """Raised when a direct runner caller supplies duplicate case IDs."""


class RuntimeMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model: StrictStr | None = None
    program_code: StrictStr | None = None
    context_type: StrictStr | None = None


class DevelopmentCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: StrictStr
    source_group_id: StrictStr
    execution_status: ExecutionStatus
    response_text: StrictStr | None = None
    unsupported_fact_kinds: tuple[StrictStr, ...] = ()
    proposal_present: bool = False
    reason_code: StrictStr | None = None
    runtime_metadata: RuntimeMetadata = RuntimeMetadata()


ExpectedReview = Literal["met", "not_met", "unclear"]
ForbiddenReview = Literal["absent", "present", "unclear"]


class StudyTaskReviewProjection(BaseModel):
    """Identifier-free semantic task evidence for private human review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_date: date
    area_type: StrictStr | None = None
    area_code: StrictStr | None = None
    task_type: TaskType
    description: StrictStr
    planned_minutes: StrictInt
    priority: TaskPriority


class StudyPlanReviewProjection(BaseModel):
    """Explicit allowlist projection of a runtime StudyPlan proposal."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: StrictStr
    plan_type: PlanType
    start_date: date
    end_date: date
    tasks: tuple[StudyTaskReviewProjection, ...]


class HumanReviewRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: StrictStr
    expected_behavior_tags: tuple[StrictStr, ...]
    forbidden_behavior_tags: tuple[StrictStr, ...]
    response_text: StrictStr | None
    proposal_review: StudyPlanReviewProjection | None = None
    expected_review: ExpectedReview | None = None
    forbidden_review: ForbiddenReview | None = None
    notes: StrictStr | None = None


class DevelopmentRunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: StrictStr
    total_cases: StrictInt
    completed: StrictInt
    not_run: StrictInt
    failed: StrictInt
    proposal_count: StrictInt
    unsupported_fact_kind_count: StrictInt


@dataclass(frozen=True)
class DevelopmentEvaluationRun:
    results: tuple[DevelopmentCaseResult, ...]
    human_review: tuple[HumanReviewRecord, ...]
    summary: DevelopmentRunSummary
    output_directory: Path


@dataclass(frozen=True)
class _PreparedCase:
    case: RealLearnerEvaluationCase
    context: LearningContext | None
    unsupported_fact_kinds: tuple[str, ...]
    reason_code: str | None = None


@dataclass(frozen=True)
class _CaseExecution:
    result: DevelopmentCaseResult
    proposal_review: StudyPlanReviewProjection | None = None


def require_private_path(path: Path, *, private_root: Path = PRIVATE_ROOT) -> Path:
    """Return a resolved private path or reject it without exposing file content."""

    root = private_root.resolve(strict=False)
    candidate = path.resolve(strict=False)
    try:
        relative = candidate.relative_to(root)
    except ValueError as error:
        raise PrivatePathError(
            "real learner evaluation paths must remain under the private directory"
        ) from error
    if not relative.parts:
        raise PrivatePathError("a file or run directory below the private root is required")
    return candidate


def validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise ValueError("run_id must be a controlled lowercase identifier")
    return run_id


def run_development_evaluation(
    cases: Iterable[RealLearnerEvaluationCase],
    provider: LLMProvider,
    *,
    run_id: str,
    private_root: Path = PRIVATE_ROOT,
    output_directory: Path | None = None,
    specialty_registry: SpecialtyProfileRegistry | None = None,
) -> DevelopmentEvaluationRun:
    """Run validated cases through the real production orchestration path.

    The runtime is an isolated in-memory SQLite store. One fresh learner is used
    per source group, while every runnable case receives an explicit context.
    """

    normalized_run_id = validate_run_id(run_id)
    ordered_cases = tuple(sorted(cases, key=lambda item: item.case_id))
    _reject_duplicate_case_ids(ordered_cases)
    require_case_local_public_forum_groups(ordered_cases)

    target = output_directory or private_root / "runs" / normalized_run_id
    target = require_private_path(target, private_root=private_root)
    if target.exists():
        raise FileExistsError("run output already exists; use a new run_id")

    try:
        provider_ready = provider.health()
    except Exception as error:
        raise ProviderUnavailableError("provider health check failed") from error
    if provider_ready is not True:
        raise ProviderUnavailableError("provider is unavailable")

    registry = specialty_registry or create_builtin_specialty_registry()
    engine = create_sqlite_engine("sqlite+pysqlite:///:memory:")
    try:
        create_schema(engine)
        memory = LearnerMemoryService(create_session_factory(engine))
        orchestrator = CoachOrchestrator(
            memory,
            provider,
            specialty_registry=registry,
        )
        prepared_by_case, learners_by_group = _prepare_runtime_state(
            ordered_cases,
            registry,
            memory,
        )
        executions = tuple(
            _execute_case(
                prepared_by_case[case.case_id],
                learners_by_group.get(case.source_group_id),
                orchestrator,
            )
            for case in ordered_cases
        )
        results = tuple(execution.result for execution in executions)
    finally:
        engine.dispose()

    human_review = tuple(
        HumanReviewRecord(
            case_id=case.case_id,
            expected_behavior_tags=case.expected_behavior_tags,
            forbidden_behavior_tags=case.forbidden_behavior_tags,
            response_text=execution.result.response_text,
            proposal_review=execution.proposal_review,
        )
        for case, execution in zip(ordered_cases, executions, strict=True)
    )
    summary = _build_summary(normalized_run_id, results)
    _write_private_artifacts(target, results, human_review, summary)
    return DevelopmentEvaluationRun(
        results=results,
        human_review=human_review,
        summary=summary,
        output_directory=target,
    )


def _prepare_runtime_state(
    cases: tuple[RealLearnerEvaluationCase, ...],
    registry: SpecialtyProfileRegistry,
    memory: LearnerMemoryService,
) -> tuple[dict[str, _PreparedCase], dict[str, Learner]]:
    grouped: dict[str, list[RealLearnerEvaluationCase]] = defaultdict(list)
    for case in cases:
        grouped[case.source_group_id].append(case)

    prepared: dict[str, _PreparedCase] = {}
    learners: dict[str, Learner] = {}
    for source_group_id in sorted(grouped):
        group_cases = tuple(grouped[source_group_id])
        education_status, group_error = _group_education_status(group_cases)
        if group_error is not None:
            for case in group_cases:
                prepared[case.case_id] = _PreparedCase(
                    case=case,
                    context=None,
                    unsupported_fact_kinds=_unsupported_fact_kinds(case),
                    reason_code=group_error,
                )
            continue

        learner = Learner(education_status=education_status)
        learners[source_group_id] = learner
        contexts: list[LearningContext] = []
        for case in group_cases:
            item = _prepare_case(case, learner, registry)
            prepared[case.case_id] = item
            if item.context is not None:
                contexts.append(item.context)
        memory.register_learner(learner, contexts)
    return prepared, learners


def _group_education_status(
    cases: tuple[RealLearnerEvaluationCase, ...],
) -> tuple[EducationStatus, str | None]:
    values: set[object] = set()
    for case in cases:
        values.update(
            fact.value for fact in case.facts if fact.kind == "education_status"
        )
    if not values:
        return EducationStatus.UNKNOWN, None
    if len(values) != 1:
        return EducationStatus.UNKNOWN, "conflicting_group_fact"
    value = next(iter(values))
    if type(value) is not str:
        return EducationStatus.UNKNOWN, "invalid_authoritative_fact"
    try:
        return EducationStatus(value), None
    except ValueError:
        return EducationStatus.UNKNOWN, "invalid_authoritative_fact"


def _prepare_case(
    case: RealLearnerEvaluationCase,
    learner: Learner,
    registry: SpecialtyProfileRegistry,
) -> _PreparedCase:
    unsupported = _unsupported_fact_kinds(case)
    profile = registry.get(case.program_code)
    if profile is None:
        return _PreparedCase(
            case=case,
            context=None,
            unsupported_fact_kinds=unsupported,
            reason_code="unsupported_program_code",
        )

    grade_level, grade_error = _single_fact_value(case, "grade_level")
    if grade_error is not None:
        return _PreparedCase(case, None, unsupported, grade_error)
    if grade_level is not None and type(grade_level) is not int:
        return _PreparedCase(case, None, unsupported, "invalid_authoritative_fact")

    study_track, track_error = _single_fact_value(case, "study_track")
    if track_error is not None:
        return _PreparedCase(case, None, unsupported, track_error)
    if study_track is not None:
        if type(study_track) is not str or not study_track.strip():
            return _PreparedCase(
                case,
                None,
                unsupported,
                "invalid_authoritative_fact",
            )
        study_track = study_track.strip()

    try:
        context = LearningContext(
            learner_id=learner.learner_id,
            context_type=profile.profile_family,
            program_code=profile.profile_code,
            grade_level=grade_level,
            track=study_track,
        )
    except ValueError:
        return _PreparedCase(
            case,
            None,
            unsupported,
            "context_materialization_failed",
        )
    return _PreparedCase(case, context, unsupported)


def _single_fact_value(
    case: RealLearnerEvaluationCase,
    kind: str,
) -> tuple[object | None, str | None]:
    values = [fact.value for fact in case.facts if fact.kind == kind]
    if not values:
        return None, None
    first = values[0]
    if any(type(value) is not type(first) or value != first for value in values[1:]):
        return None, "conflicting_authoritative_fact"
    return first, None


def _unsupported_fact_kinds(
    case: RealLearnerEvaluationCase,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                fact.kind
                for fact in case.facts
                if fact.kind not in AUTHORITATIVE_FACT_KINDS
            }
        )
    )


def _execute_case(
    prepared: _PreparedCase,
    learner: Learner | None,
    orchestrator: CoachOrchestrator,
) -> _CaseExecution:
    case = prepared.case
    if prepared.reason_code is not None or prepared.context is None or learner is None:
        return _CaseExecution(
            DevelopmentCaseResult(
                case_id=case.case_id,
                source_group_id=case.source_group_id,
                execution_status=ExecutionStatus.NOT_RUN,
                unsupported_fact_kinds=prepared.unsupported_fact_kinds,
                reason_code=prepared.reason_code or "context_unavailable",
            )
        )

    context = prepared.context
    metadata = RuntimeMetadata(
        program_code=context.program_code,
        context_type=context.context_type.value,
    )
    try:
        result = orchestrator.respond(
            learner.learner_id,
            case.user_message,
            context_id=context.context_id,
        )
    except Exception:
        return _CaseExecution(
            DevelopmentCaseResult(
                case_id=case.case_id,
                source_group_id=case.source_group_id,
                execution_status=ExecutionStatus.FAILED,
                unsupported_fact_kinds=prepared.unsupported_fact_kinds,
                reason_code="orchestrator_error",
                runtime_metadata=metadata,
            )
        )

    proposal_review = (
        _project_proposal_for_review(result.study_plan_proposal)
        if result.study_plan_proposal is not None
        else None
    )
    review_json = (
        proposal_review.model_dump_json() if proposal_review is not None else ""
    )
    if UUID_PATTERN.search(result.text) or UUID_PATTERN.search(review_json):
        return _CaseExecution(
            DevelopmentCaseResult(
                case_id=case.case_id,
                source_group_id=case.source_group_id,
                execution_status=ExecutionStatus.FAILED,
                unsupported_fact_kinds=prepared.unsupported_fact_kinds,
                reason_code="runtime_identifier_leak",
                runtime_metadata=metadata,
            )
        )

    safe_model = (
        result.model
        if isinstance(result.model, str) and SAFE_MODEL_PATTERN.fullmatch(result.model)
        else None
    )
    return _CaseExecution(
        DevelopmentCaseResult(
            case_id=case.case_id,
            source_group_id=case.source_group_id,
            execution_status=ExecutionStatus.COMPLETED,
            response_text=result.text,
            unsupported_fact_kinds=prepared.unsupported_fact_kinds,
            proposal_present=result.study_plan_proposal is not None,
            runtime_metadata=RuntimeMetadata(
                model=safe_model,
                program_code=context.program_code,
                context_type=context.context_type.value,
            ),
        ),
        proposal_review=proposal_review,
    )


def _project_proposal_for_review(
    proposal: StudyPlanWriteProposal,
) -> StudyPlanReviewProjection:
    """Project only reviewer-relevant semantics; never copy runtime IDs."""

    plan = proposal.plan
    return StudyPlanReviewProjection(
        title=plan.title,
        plan_type=plan.plan_type,
        start_date=plan.start_date,
        end_date=plan.end_date,
        tasks=tuple(
            StudyTaskReviewProjection(
                task_date=task.task_date,
                area_type=task.area_type,
                area_code=task.area_code,
                task_type=task.task_type,
                description=task.description,
                planned_minutes=task.planned_minutes,
                priority=task.priority,
            )
            for task in proposal.tasks
        ),
    )


def _build_summary(
    run_id: str,
    results: tuple[DevelopmentCaseResult, ...],
) -> DevelopmentRunSummary:
    return DevelopmentRunSummary(
        run_id=run_id,
        total_cases=len(results),
        completed=sum(
            result.execution_status is ExecutionStatus.COMPLETED for result in results
        ),
        not_run=sum(
            result.execution_status is ExecutionStatus.NOT_RUN for result in results
        ),
        failed=sum(
            result.execution_status is ExecutionStatus.FAILED for result in results
        ),
        proposal_count=sum(result.proposal_present for result in results),
        unsupported_fact_kind_count=len(
            {
                kind
                for result in results
                for kind in result.unsupported_fact_kinds
            }
        ),
    )


def _write_private_artifacts(
    target: Path,
    results: tuple[DevelopmentCaseResult, ...],
    human_review: tuple[HumanReviewRecord, ...],
    summary: DevelopmentRunSummary,
) -> None:
    target.mkdir(parents=True, exist_ok=False)
    _write_jsonl_new(target / "results.jsonl", results)
    _write_jsonl_new(target / "human_review.jsonl", human_review)
    with (target / "summary.json").open(
        "x", encoding="utf-8", newline="\n"
    ) as output:
        json.dump(
            summary.model_dump(mode="json"),
            output,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        output.write("\n")


def _write_jsonl_new(path: Path, rows: Iterable[BaseModel]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as output:
        for row in rows:
            output.write(
                json.dumps(
                    row.model_dump(mode="json"),
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n"
            )


def _reject_duplicate_case_ids(
    cases: tuple[RealLearnerEvaluationCase, ...],
) -> None:
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise DuplicateCaseError("duplicate case_id")
